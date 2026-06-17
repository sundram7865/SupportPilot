import time
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import (
    TicketTimelineEventType,
    ToolApprovalStatus,
    ToolExecutionStatus,
    ToolName,
)
from app.modules.agent.models import AgentRun
from app.modules.organizations.models import Organization
from app.modules.tickets.models import Ticket, TicketTimelineEvent
from app.modules.tools.models import ToolExecution
from app.modules.tools.registry import get_tool_definition
from app.modules.tools.urbankart_tools import (
    execute_urbankart_get_order_context,
    execute_urbankart_request_refund,
)


def add_tool_timeline_event(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID | None,
    actor_user_id: UUID | None,
    event_type: TicketTimelineEventType,
    title: str,
    description: str | None = None,
) -> None:
    if not ticket_id:
        return

    event = TicketTimelineEvent(
        organization_id=organization_id,
        ticket_id=ticket_id,
        actor_user_id=actor_user_id,
        event_type=event_type.value,
        title=title,
        description=description,
    )

    db.add(event)


def validate_ticket_scope(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID | None,
) -> None:
    if ticket_id is None:
        return

    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .where(Ticket.organization_id == organization_id)
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )


def get_existing_execution_by_idempotency_key(
    db: Session,
    organization_id: UUID,
    idempotency_key: str | None,
) -> ToolExecution | None:
    if not idempotency_key:
        return None

    return db.scalar(
        select(ToolExecution)
        .where(ToolExecution.organization_id == organization_id)
        .where(ToolExecution.idempotency_key == idempotency_key)
    )


async def execute_tool(
    db: Session,
    organization: Organization,
    tool_name: str,
    args: dict,
    requested_by_user_id: UUID | None,
    ticket_id: UUID | None = None,
    agent_run_id: UUID | None = None,
    idempotency_key: str | None = None,
    allow_risky_execution: bool = False,
) -> ToolExecution:
    validate_ticket_scope(db, organization.id, ticket_id)

    existing_execution = get_existing_execution_by_idempotency_key(
    db=db,
    organization_id=organization.id,
    idempotency_key=idempotency_key,
)

    if existing_execution:
        same_tool = existing_execution.tool_name == tool_name
        same_ticket = existing_execution.ticket_id == ticket_id
        same_agent_run = existing_execution.agent_run_id == agent_run_id
        same_args = existing_execution.input_args == args

        if not all([same_tool, same_ticket, same_agent_run, same_args]):
            raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency key was already used with different tool input.",
        )

        return existing_execution

    tool_definition = get_tool_definition(tool_name)

    started_at = time.perf_counter()

    execution = ToolExecution(
        organization_id=organization.id,
        ticket_id=ticket_id,
        agent_run_id=agent_run_id,
        requested_by_user_id=requested_by_user_id,
        tool_name=tool_name,
        risk_level=tool_definition.risk_level.value,
        input_args=args,
        idempotency_key=idempotency_key,
        status=ToolExecutionStatus.STARTED.value,
        approval_status=(
            ToolApprovalStatus.REQUIRED.value
            if tool_definition.requires_approval
            else ToolApprovalStatus.NOT_REQUIRED.value
        ),
    )

    db.add(execution)

    add_tool_timeline_event(
        db=db,
        organization_id=organization.id,
        ticket_id=ticket_id,
        actor_user_id=requested_by_user_id,
        event_type=TicketTimelineEventType.TOOL_EXECUTION_STARTED,
        title="Tool execution started",
        description=f"Tool {tool_name} started.",
    )

    db.commit()
    db.refresh(execution)

    if tool_definition.requires_approval and not allow_risky_execution:
        execution.status = ToolExecutionStatus.BLOCKED_APPROVAL_REQUIRED.value
        execution.approval_status = ToolApprovalStatus.PENDING.value
        execution.duration_ms = int((time.perf_counter() - started_at) * 1000)
        execution.completed_at = datetime.now(timezone.utc)

        add_tool_timeline_event(
            db=db,
            organization_id=organization.id,
            ticket_id=ticket_id,
            actor_user_id=requested_by_user_id,
            event_type=TicketTimelineEventType.TOOL_EXECUTION_BLOCKED,
            title="Tool execution blocked",
            description=f"Tool {tool_name} requires human approval.",
        )

        db.commit()
        db.refresh(execution)

        return execution

    try:
        if tool_name == ToolName.URBANKART_GET_ORDER_CONTEXT.value:
            output = await execute_urbankart_get_order_context(
                db=db,
                organization=organization,
                args=args,
            )
        elif tool_name == ToolName.URBANKART_REQUEST_REFUND.value:
            output = await execute_urbankart_request_refund(
                db=db,
                organization=organization,
                args=args,
                support_ticket_id=ticket_id,
                idempotency_key=idempotency_key or str(execution.id),
            )
        else:
            raise ValueError(f"No executor configured for tool: {tool_name}")

        execution.status = ToolExecutionStatus.SUCCESS.value
        execution.output_json = output
        execution.duration_ms = int((time.perf_counter() - started_at) * 1000)
        execution.completed_at = datetime.now(timezone.utc)

        add_tool_timeline_event(
            db=db,
            organization_id=organization.id,
            ticket_id=ticket_id,
            actor_user_id=requested_by_user_id,
            event_type=TicketTimelineEventType.TOOL_EXECUTION_COMPLETED,
            title="Tool execution completed",
            description=f"Tool {tool_name} completed successfully.",
        )

        db.commit()
        db.refresh(execution)

        return execution

    except Exception as exc:
        execution.status = ToolExecutionStatus.FAILED.value
        execution.error_message = str(exc)
        execution.duration_ms = int((time.perf_counter() - started_at) * 1000)
        execution.completed_at = datetime.now(timezone.utc)

        add_tool_timeline_event(
            db=db,
            organization_id=organization.id,
            ticket_id=ticket_id,
            actor_user_id=requested_by_user_id,
            event_type=TicketTimelineEventType.TOOL_EXECUTION_FAILED,
            title="Tool execution failed",
            description=str(exc),
        )

        db.commit()
        db.refresh(execution)

        return execution


async def execute_safe_tools_from_agent_run(
    db: Session,
    organization: Organization,
    agent_run: AgentRun,
    requested_by_user_id: UUID | None,
) -> list[ToolExecution]:
    planned_tools = agent_run.planned_tools or []
    executions: list[ToolExecution] = []

    for index, planned_tool in enumerate(planned_tools):
        tool_name = planned_tool.get("tool_name")
        args = planned_tool.get("args") or {}
        requires_approval = bool(planned_tool.get("requires_approval"))

        idempotency_key = f"agent_run:{agent_run.id}:tool:{index}:{tool_name}"

        execution = await execute_tool(
            db=db,
            organization=organization,
            tool_name=tool_name,
            args=args,
            requested_by_user_id=requested_by_user_id,
            ticket_id=agent_run.ticket_id,
            agent_run_id=agent_run.id,
            idempotency_key=idempotency_key,
            allow_risky_execution=False,
        )

        executions.append(execution)

    return executions


async def execute_approved_tool_execution(
    db: Session,
    organization: Organization,
    execution: ToolExecution,
    approved_by_user_id: UUID | None,
) -> ToolExecution:
    tool_definition = get_tool_definition(execution.tool_name)

    if not tool_definition.requires_approval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This tool execution does not require approval.",
        )

    if execution.approval_status != ToolApprovalStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool execution is not approved.",
        )

    if execution.status == ToolExecutionStatus.SUCCESS.value:
        return execution

    started_at = time.perf_counter()

    execution.status = ToolExecutionStatus.STARTED.value
    execution.error_message = None

    add_tool_timeline_event(
        db=db,
        organization_id=organization.id,
        ticket_id=execution.ticket_id,
        actor_user_id=approved_by_user_id,
        event_type=TicketTimelineEventType.APPROVED_TOOL_EXECUTION_STARTED,
        title="Approved tool execution started",
        description=f"Approved tool {execution.tool_name} started.",
    )

    db.commit()
    db.refresh(execution)

    try:
        if execution.tool_name == ToolName.URBANKART_REQUEST_REFUND.value:
            output = await execute_urbankart_request_refund(
                db=db,
                organization=organization,
                args=execution.input_args or {},
                support_ticket_id=execution.ticket_id,
                idempotency_key=execution.idempotency_key or str(execution.id),
            )
        elif execution.tool_name == ToolName.URBANKART_GET_ORDER_CONTEXT.value:
            output = await execute_urbankart_get_order_context(
                db=db,
                organization=organization,
                args=execution.input_args or {},
            )
        else:
            raise ValueError(f"No executor configured for tool: {execution.tool_name}")

        execution.status = ToolExecutionStatus.SUCCESS.value
        execution.output_json = output
        execution.error_message = None
        execution.duration_ms = int((time.perf_counter() - started_at) * 1000)
        execution.completed_at = datetime.now(timezone.utc)

        add_tool_timeline_event(
            db=db,
            organization_id=organization.id,
            ticket_id=execution.ticket_id,
            actor_user_id=approved_by_user_id,
            event_type=TicketTimelineEventType.APPROVED_TOOL_EXECUTION_COMPLETED,
            title="Approved tool execution completed",
            description=f"Approved tool {execution.tool_name} completed successfully.",
        )

        db.commit()
        db.refresh(execution)

        return execution

    except Exception as exc:
        execution.status = ToolExecutionStatus.FAILED.value
        execution.error_message = str(exc)
        execution.duration_ms = int((time.perf_counter() - started_at) * 1000)
        execution.completed_at = datetime.now(timezone.utc)

        add_tool_timeline_event(
            db=db,
            organization_id=organization.id,
            ticket_id=execution.ticket_id,
            actor_user_id=approved_by_user_id,
            event_type=TicketTimelineEventType.APPROVED_TOOL_EXECUTION_FAILED,
            title="Approved tool execution failed",
            description=str(exc),
        )

        db.commit()
        db.refresh(execution)

        return execution