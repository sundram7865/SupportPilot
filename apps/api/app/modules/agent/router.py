from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.modules.agent.models import AgentRun, AgentRunStep
from app.modules.agent.schemas import (
    AgentRunListItemResponse,
    AgentRunListResponse,
    AgentRunResponse,
    AgentRunStepResponse,
    RunTicketAgentRequest,
)
from app.modules.agent.service import run_ticket_agent
from app.modules.auth.dependencies import (
    get_current_organization,
    get_or_create_current_user,
    require_permission,
)
from app.modules.auth.permissions import Permission
from app.modules.organizations.models import Organization
from app.modules.tickets.models import Ticket
from app.modules.users.models import User

router = APIRouter(prefix="/agent", tags=["Agent"])


def get_agent_run_or_404(
    db: Session,
    organization_id: UUID,
    run_id: UUID,
) -> AgentRun:
    agent_run = db.scalar(
        select(AgentRun)
        .options(selectinload(AgentRun.steps))
        .where(AgentRun.id == run_id)
        .where(AgentRun.organization_id == organization_id)
    )

    if not agent_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent run not found.",
        )

    return agent_run


def to_step_response(step: AgentRunStep) -> AgentRunStepResponse:
    return AgentRunStepResponse(
        id=str(step.id),
        step_name=step.step_name,
        status=step.status,
        input_json=step.input_json,
        output_json=step.output_json,
        error_message=step.error_message,
        duration_ms=step.duration_ms,
        created_at=step.created_at,
        completed_at=step.completed_at,
    )


def to_agent_run_response(agent_run: AgentRun) -> AgentRunResponse:
    return AgentRunResponse(
        id=str(agent_run.id),
        organization_id=str(agent_run.organization_id),
        ticket_id=str(agent_run.ticket_id),
        started_by_user_id=(
            str(agent_run.started_by_user_id) if agent_run.started_by_user_id else None
        ),
        status=agent_run.status,
        provider=agent_run.provider,
        model_name=agent_run.model_name,
        detected_category=agent_run.detected_category,
        detected_priority=agent_run.detected_priority,
        risk_level=agent_run.risk_level,
        decision=agent_run.decision,
        draft_response=agent_run.draft_response,
        reasoning_summary=agent_run.reasoning_summary,
        planned_tools=agent_run.planned_tools,
        retrieved_context=agent_run.retrieved_context,
        final_state=agent_run.final_state,
        error_message=agent_run.error_message,
        duration_ms=agent_run.duration_ms,
        created_at=agent_run.created_at,
        completed_at=agent_run.completed_at,
        steps=[to_step_response(step) for step in agent_run.steps],
    )


def to_agent_run_list_item(agent_run: AgentRun) -> AgentRunListItemResponse:
    return AgentRunListItemResponse(
        id=str(agent_run.id),
        ticket_id=str(agent_run.ticket_id),
        status=agent_run.status,
        risk_level=agent_run.risk_level,
        decision=agent_run.decision,
        detected_category=agent_run.detected_category,
        detected_priority=agent_run.detected_priority,
        duration_ms=agent_run.duration_ms,
        created_at=agent_run.created_at,
        completed_at=agent_run.completed_at,
    )


@router.post(
    "/tickets/{ticket_id}/run",
    response_model=AgentRunResponse,
    dependencies=[Depends(require_permission(Permission.AGENT_RUN))],
)
def run_agent_for_ticket(
    ticket_id: UUID,
    payload: RunTicketAgentRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .where(Ticket.organization_id == organization.id)
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    agent_run = run_ticket_agent(
        db=db,
        organization_id=organization.id,
        ticket_id=ticket.id,
        user_id=current_user.id,
    )

    agent_run = get_agent_run_or_404(db, organization.id, agent_run.id)

    return to_agent_run_response(agent_run)


@router.get(
    "/runs/{run_id}",
    response_model=AgentRunResponse,
    dependencies=[Depends(require_permission(Permission.AGENT_READ))],
)
def get_agent_run(
    run_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    agent_run = get_agent_run_or_404(db, organization.id, run_id)
    return to_agent_run_response(agent_run)


@router.get(
    "/tickets/{ticket_id}/runs",
    response_model=AgentRunListResponse,
    dependencies=[Depends(require_permission(Permission.AGENT_READ))],
)
def list_ticket_agent_runs(
    ticket_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .where(Ticket.organization_id == organization.id)
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    total = (
        db.scalar(
            select(func.count(AgentRun.id))
            .where(AgentRun.ticket_id == ticket_id)
            .where(AgentRun.organization_id == organization.id)
        )
        or 0
    )

    runs = db.scalars(
        select(AgentRun)
        .where(AgentRun.ticket_id == ticket_id)
        .where(AgentRun.organization_id == organization.id)
        .order_by(desc(AgentRun.created_at))
    ).all()

    return AgentRunListResponse(
        items=[to_agent_run_list_item(run) for run in runs],
        total=total,
    )