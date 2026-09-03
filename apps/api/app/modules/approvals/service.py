from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import (
    ApprovalRequestStatus,
    ApprovalRequestType,
    TicketTimelineEventType,
    ToolApprovalStatus,
    ToolExecutionStatus,
)
from app.common.enums import AuditAction, AuditResourceType
from app.modules.audit.service import create_audit_log
from app.modules.approvals.models import ApprovalRequest
from app.modules.organizations.models import Organization
from app.modules.realtime.publisher import publish_timeline_event_after_commit
from app.modules.tickets.models import TicketTimelineEvent
from app.modules.tools.models import ToolExecution
from app.modules.tools.service import execute_approved_tool_execution
from app.modules.agent.service import resume_agent_after_approval


def add_approval_timeline_event(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID | None,
    actor_user_id: UUID | None,
    event_type: TicketTimelineEventType,
    title: str,
    description: str | None = None,
) -> TicketTimelineEvent | None:
    if not ticket_id:
        return None

    event = TicketTimelineEvent(
        organization_id=organization_id,
        ticket_id=ticket_id,
        actor_user_id=actor_user_id,
        event_type=event_type.value,
        title=title,
        description=description,
    )

    db.add(event)
    return event


def publish_if_exists(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID | None,
    event: TicketTimelineEvent | None,
) -> None:
    if not event or not ticket_id:
        return

    db.refresh(event)

    publish_timeline_event_after_commit(
        db=db,
        organization_id=organization_id,
        ticket_id=ticket_id,
        event=event,
    )


def get_approval_or_404(
    db: Session,
    organization_id: UUID,
    approval_id: UUID,
) -> ApprovalRequest:
    approval = db.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.id == approval_id)
        .where(ApprovalRequest.organization_id == organization_id)
    )

    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found.",
        )

    return approval


def get_tool_execution_or_404(
    db: Session,
    organization_id: UUID,
    execution_id: UUID,
) -> ToolExecution:
    execution = db.scalar(
        select(ToolExecution)
        .where(ToolExecution.id == execution_id)
        .where(ToolExecution.organization_id == organization_id)
    )

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tool execution not found.",
        )

    return execution


def create_approval_request_for_tool_execution(
    db: Session,
    organization_id: UUID,
    execution_id: UUID,
    requested_by_user_id: UUID | None,
    request_reason: str | None = None,
    metadata_json: dict | None = None,
) -> ApprovalRequest:
    execution = get_tool_execution_or_404(
        db=db,
        organization_id=organization_id,
        execution_id=execution_id,
    )

    if execution.approval_status not in {
        ToolApprovalStatus.PENDING.value,
        ToolApprovalStatus.REQUIRED.value,
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This tool execution does not need approval.",
        )

    if execution.status != ToolExecutionStatus.BLOCKED_APPROVAL_REQUIRED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only blocked approval-required tool executions can create approval requests.",
        )

    existing = db.scalar(
        select(ApprovalRequest)
        .where(ApprovalRequest.organization_id == organization_id)
        .where(ApprovalRequest.tool_execution_id == execution.id)
    )

    if existing:
        return existing

    approval = ApprovalRequest(
        organization_id=organization_id,
        ticket_id=execution.ticket_id,
        agent_run_id=execution.agent_run_id,
        tool_execution_id=execution.id,
        requested_by_user_id=requested_by_user_id,
        request_type=ApprovalRequestType.TOOL_EXECUTION.value,
        status=ApprovalRequestStatus.PENDING.value,
        title=f"Approval required for {execution.tool_name}",
        description="A risky tool execution requires human approval before it can continue.",
        risk_level=execution.risk_level,
        tool_name=execution.tool_name,
        input_args=execution.input_args,
        request_reason=request_reason,
        metadata_json=metadata_json,
    )

    db.add(approval)

    timeline_event = add_approval_timeline_event(
        db=db,
        organization_id=organization_id,
        ticket_id=execution.ticket_id,
        actor_user_id=requested_by_user_id,
        event_type=TicketTimelineEventType.APPROVAL_REQUEST_CREATED,
        title="Approval request created",
        description=f"Approval requested for tool {execution.tool_name}.",
    )
    create_audit_log(
        db=db,
        organization_id=organization_id,
        actor_user_id=requested_by_user_id,
        action=AuditAction.APPROVAL_REQUEST_CREATED,
        resource_type=AuditResourceType.APPROVAL_REQUEST,
        resource_id=approval.id,
        ticket_id=execution.ticket_id,
        agent_run_id=execution.agent_run_id,
        tool_execution_id=execution.id,
        approval_request_id=approval.id,
        description=f"Approval request created for tool {execution.tool_name}.",
        metadata_json={
            "tool_name": execution.tool_name,
            "risk_level": execution.risk_level,
            "request_reason": request_reason,
        },
    )
    db.commit()
    db.refresh(approval)
    publish_if_exists(db, organization_id, execution.ticket_id, timeline_event)

    return approval


async def approve_request(
    db: Session,
    organization: Organization,
    approval_id: UUID,
    decided_by_user_id: UUID | None,
    decision_reason: str | None = None,
) -> ApprovalRequest:
    approval = get_approval_or_404(
        db=db,
        organization_id=organization.id,
        approval_id=approval_id,
    )

    if approval.status != ApprovalRequestStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending approval requests can be approved.",
        )

    approval.status = ApprovalRequestStatus.APPROVED.value
    approval.decided_by_user_id = decided_by_user_id
    approval.decision_reason = decision_reason
    approval.decided_at = datetime.now(timezone.utc)

    timeline_event = add_approval_timeline_event(
        db=db,
        organization_id=organization.id,
        ticket_id=approval.ticket_id,
        actor_user_id=decided_by_user_id,
        event_type=TicketTimelineEventType.APPROVAL_REQUEST_APPROVED,
        title="Approval request approved",
        description=decision_reason,
    )
    create_audit_log(
        db=db,
        organization_id=organization.id,
        actor_user_id=decided_by_user_id,
        action=AuditAction.APPROVAL_REQUEST_APPROVED,
        resource_type=AuditResourceType.APPROVAL_REQUEST,
        resource_id=approval.id,
        ticket_id=approval.ticket_id,
        agent_run_id=approval.agent_run_id,
        tool_execution_id=approval.tool_execution_id,
        approval_request_id=approval.id,
        description="Approval request approved.",
        metadata_json={
            "request_type": approval.request_type,
            "decision_reason": decision_reason,
        },
    )
    db.commit()
    db.refresh(approval)
    publish_if_exists(db, organization.id, approval.ticket_id, timeline_event)

    # If this approval is linked to an agent run, resume the graph instead of
    # executing tools directly. The approval decision itself is already
    # committed above and reflects what the human actually did — if resuming
    # the graph fails, that failure belongs to the AgentRun (which
    # resume_agent_after_approval marks FAILED and commits on its own), not
    # to the approval decision. We surface it clearly instead of letting a
    # bare exception propagate to the API layer.
    if approval.agent_run_id:
        # Mark the underlying tool execution as approved BEFORE resuming the
        # graph. execute_tools_node -> execute_approved_tool_execution
        # requires approval_status == APPROVED and will reject otherwise.
        # The manual (non-agent-run) branch below already does this; the
        # agent-run branch previously did not, since the old mock
        # execute_tools_node set this flag itself instead of calling the
        # real executor.
        if approval.tool_execution_id:
            execution = get_tool_execution_or_404(
                db=db,
                organization_id=organization.id,
                execution_id=approval.tool_execution_id,
            )
            execution.approval_status = ToolApprovalStatus.APPROVED.value
            db.commit()

        try:
            resume_agent_after_approval(
                db=db,
                agent_run_id=approval.agent_run_id,
                approved=True,
                reason=decision_reason,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Approval was recorded, but resuming the agent run failed: "
                    f"{exc}"
                ),
            ) from exc
        # The graph will update the AgentRun, execute tools, and finalize.
        # No further direct execution is needed here.
        return approval

    # For manual tool executions (not part of an agent run), keep the original direct execution
    if approval.request_type == ApprovalRequestType.TOOL_EXECUTION.value:
        if not approval.tool_execution_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Approval request has no tool execution attached.",
            )

        execution = get_tool_execution_or_404(
            db=db,
            organization_id=organization.id,
            execution_id=approval.tool_execution_id,
        )

        execution.approval_status = ToolApprovalStatus.APPROVED.value

        db.commit()
        db.refresh(execution)

        execution = await execute_approved_tool_execution(
            db=db,
            organization=organization,
            execution=execution,
            approved_by_user_id=decided_by_user_id,
        )

        approval.result_json = {
            "tool_execution_id": str(execution.id),
            "tool_status": execution.status,
            "tool_output": execution.output_json,
            "tool_error": execution.error_message,
        }

        db.commit()
        db.refresh(approval)

    return approval


def reject_request(
    db: Session,
    organization_id: UUID,
    approval_id: UUID,
    decided_by_user_id: UUID | None,
    decision_reason: str | None = None,
) -> ApprovalRequest:
    approval = get_approval_or_404(
        db=db,
        organization_id=organization_id,
        approval_id=approval_id,
    )

    if approval.status != ApprovalRequestStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending approval requests can be rejected.",
        )

    approval.status = ApprovalRequestStatus.REJECTED.value
    approval.decided_by_user_id = decided_by_user_id
    approval.decision_reason = decision_reason
    approval.decided_at = datetime.now(timezone.utc)

    if approval.tool_execution_id:
        execution = get_tool_execution_or_404(
            db=db,
            organization_id=organization_id,
            execution_id=approval.tool_execution_id,
        )
        execution.approval_status = ToolApprovalStatus.REJECTED.value
        # ToolExecutionStatus has no REJECTED/CANCELLED member; SKIPPED is the
        # correct terminal state here since the tool was never executed.
        # Without this, execution.status stays BLOCKED_APPROVAL_REQUIRED
        # forever, even though approval_status already says REJECTED.
        execution.status = ToolExecutionStatus.SKIPPED.value
        execution.completed_at = datetime.now(timezone.utc)

    timeline_event = add_approval_timeline_event(
        db=db,
        organization_id=organization_id,
        ticket_id=approval.ticket_id,
        actor_user_id=decided_by_user_id,
        event_type=TicketTimelineEventType.APPROVAL_REQUEST_REJECTED,
        title="Approval request rejected",
        description=decision_reason,
    )
    create_audit_log(
        db=db,
        organization_id=organization_id,
        actor_user_id=decided_by_user_id,
        action=AuditAction.APPROVAL_REQUEST_REJECTED,
        resource_type=AuditResourceType.APPROVAL_REQUEST,
        resource_id=approval.id,
        ticket_id=approval.ticket_id,
        agent_run_id=approval.agent_run_id,
        tool_execution_id=approval.tool_execution_id,
        approval_request_id=approval.id,
        description="Approval request rejected.",
        metadata_json={
            "request_type": approval.request_type,
            "decision_reason": decision_reason,
        },
    )
    db.commit()
    db.refresh(approval)
    publish_if_exists(db, organization_id, approval.ticket_id, timeline_event)

    # If linked to an agent run, resume the graph with rejection.
    # Same reasoning as approve_request: the rejection decision is already
    # committed and correct regardless of whether the graph resume succeeds.
    if approval.agent_run_id:
        try:
            resume_agent_after_approval(
                db=db,
                agent_run_id=approval.agent_run_id,
                approved=False,
                reason=decision_reason,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    "Rejection was recorded, but resuming the agent run failed: "
                    f"{exc}"
                ),
            ) from exc

    return approval