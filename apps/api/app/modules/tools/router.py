from uuid import UUID
from app.common.enums import ToolApprovalStatus, ToolExecutionStatus
from app.modules.approvals.service import create_approval_request_for_tool_execution
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.agent.models import AgentRun
from app.modules.auth.dependencies import (
    get_current_organization,
    get_or_create_current_user,
    require_permission,
)
from app.modules.auth.permissions import Permission
from app.modules.organizations.models import Organization
from app.modules.tools.models import ToolExecution
from app.modules.tools.schemas import (
    AgentRunToolExecutionResponse,
    ExecuteAgentRunToolsRequest,
    ExecuteToolRequest,
    ToolExecutionListResponse,
    ToolExecutionResponse,
)
from app.modules.tools.service import execute_safe_tools_from_agent_run, execute_tool
from app.modules.users.models import User

router = APIRouter(prefix="/tools", tags=["Tool Gateway"])


def to_tool_execution_response(execution: ToolExecution) -> ToolExecutionResponse:
    return ToolExecutionResponse(
        id=str(execution.id),
        organization_id=str(execution.organization_id),
        ticket_id=str(execution.ticket_id) if execution.ticket_id else None,
        agent_run_id=str(execution.agent_run_id) if execution.agent_run_id else None,
        requested_by_user_id=(
            str(execution.requested_by_user_id)
            if execution.requested_by_user_id
            else None
        ),
        tool_name=execution.tool_name,
        risk_level=execution.risk_level,
        status=execution.status,
        approval_status=execution.approval_status,
        idempotency_key=execution.idempotency_key,
        input_args=execution.input_args,
        output_json=execution.output_json,
        error_message=execution.error_message,
        duration_ms=execution.duration_ms,
        created_at=execution.created_at,
        completed_at=execution.completed_at,
    )


def get_execution_or_404(
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


@router.post(
    "/execute",
    response_model=ToolExecutionResponse,
    dependencies=[Depends(require_permission(Permission.TOOL_EXECUTE))],
)
async def execute_tool_route(
    payload: ExecuteToolRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    execution = await execute_tool(
        db=db,
        organization=organization,
        tool_name=payload.tool_name.value,
        args=payload.args,
        requested_by_user_id=current_user.id,
        ticket_id=payload.ticket_id,
        agent_run_id=payload.agent_run_id,
        idempotency_key=payload.idempotency_key,
        allow_risky_execution=False,
    )

    return to_tool_execution_response(execution)


@router.post(
    "/agent-runs/{run_id}/execute-safe",
    response_model=AgentRunToolExecutionResponse,
    dependencies=[Depends(require_permission(Permission.TOOL_EXECUTE))],
)
async def execute_agent_run_safe_tools(
    run_id: UUID,
    payload: ExecuteAgentRunToolsRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    agent_run = db.scalar(
        select(AgentRun)
        .where(AgentRun.id == run_id)
        .where(AgentRun.organization_id == organization.id)
    )

    if not agent_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found.",
        )

    executions = await execute_safe_tools_from_agent_run(
        db=db,
        organization=organization,
        agent_run=agent_run,
        requested_by_user_id=current_user.id,
    )

    for execution in executions:
        should_create_approval = (
            execution.status == ToolExecutionStatus.BLOCKED_APPROVAL_REQUIRED.value
            and execution.approval_status
            in {
                ToolApprovalStatus.PENDING.value,
                ToolApprovalStatus.REQUIRED.value,
            }
        )

        if should_create_approval:
            create_approval_request_for_tool_execution(
                db=db,
                organization_id=organization.id,
                execution_id=execution.id,
                requested_by_user_id=current_user.id,
                request_reason=(
                    "Approval automatically created because the agent planned "
                    "a risky tool execution."
                ),
                metadata_json={
                    "source": "agent_run_execute_safe",
                    "agent_run_id": str(agent_run.id),
                    "ticket_id": str(agent_run.ticket_id),
                    "tool_name": execution.tool_name,
                },
            )

    refreshed_executions = db.scalars(
        select(ToolExecution)
        .where(ToolExecution.organization_id == organization.id)
        .where(ToolExecution.agent_run_id == agent_run.id)
        .order_by(desc(ToolExecution.created_at))
    ).all()

    return AgentRunToolExecutionResponse(
        agent_run_id=str(agent_run.id),
        executions=[
            to_tool_execution_response(execution)
            for execution in refreshed_executions
        ],
    )

@router.get(
    "/executions/{execution_id}",
    response_model=ToolExecutionResponse,
    dependencies=[Depends(require_permission(Permission.TOOL_READ))],
)
def get_tool_execution(
    execution_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    execution = get_execution_or_404(db, organization.id, execution_id)
    return to_tool_execution_response(execution)


@router.get(
    "/tickets/{ticket_id}/executions",
    response_model=ToolExecutionListResponse,
    dependencies=[Depends(require_permission(Permission.TOOL_READ))],
)
def list_ticket_tool_executions(
    ticket_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    total = (
        db.scalar(
            select(func.count(ToolExecution.id))
            .where(ToolExecution.organization_id == organization.id)
            .where(ToolExecution.ticket_id == ticket_id)
        )
        or 0
    )

    executions = db.scalars(
        select(ToolExecution)
        .where(ToolExecution.organization_id == organization.id)
        .where(ToolExecution.ticket_id == ticket_id)
        .order_by(desc(ToolExecution.created_at))
    ).all()

    return ToolExecutionListResponse(
        items=[to_tool_execution_response(execution) for execution in executions],
        total=total,
    )