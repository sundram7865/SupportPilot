import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.enums import (
    AgentDecision,
    AgentRiskLevel,
    AgentRunStatus,
    TicketTimelineEventType,
)
from app.core.config import get_settings
from app.modules.agent.graph import build_ticket_agent_graph
from app.modules.agent.models import AgentRun
from app.modules.agent.state import AgentState
from app.modules.tickets.models import TicketTimelineEvent


def add_agent_timeline_event(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID,
    actor_user_id: UUID | None,
    event_type: TicketTimelineEventType,
    title: str,
    description: str | None = None,
) -> None:
    event = TicketTimelineEvent(
        organization_id=organization_id,
        ticket_id=ticket_id,
        actor_user_id=actor_user_id,
        event_type=event_type.value,
        title=title,
        description=description,
    )

    db.add(event)


def run_ticket_agent(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID,
    user_id: UUID | None,
) -> AgentRun:
    settings = get_settings()
    started_at = time.perf_counter()

    agent_run = AgentRun(
        organization_id=organization_id,
        ticket_id=ticket_id,
        started_by_user_id=user_id,
        status=AgentRunStatus.STARTED.value,
        provider=settings.ai_provider,
        model_name=settings.gemini_model if settings.ai_provider == "gemini" else "mock-agent",
        risk_level=AgentRiskLevel.LOW.value,
        decision=AgentDecision.NO_ACTION.value,
    )

    db.add(agent_run)
    db.flush()

    add_agent_timeline_event(
        db=db,
        organization_id=organization_id,
        ticket_id=ticket_id,
        actor_user_id=user_id,
        event_type=TicketTimelineEventType.AGENT_RUN_STARTED,
        title="Agent run started",
        description=f"Agent run {agent_run.id} started.",
    )

    db.commit()
    db.refresh(agent_run)

    initial_state: AgentState = {
        "organization_id": str(organization_id),
        "ticket_id": str(ticket_id),
        "agent_run_id": str(agent_run.id),
        "user_id": str(user_id) if user_id else None,
    }

    try:
        graph = build_ticket_agent_graph(db)
        final_state = graph.invoke(initial_state)

        duration_ms = int((time.perf_counter() - started_at) * 1000)

        agent_run.status = AgentRunStatus.COMPLETED.value
        agent_run.detected_category = final_state.get("detected_category")
        agent_run.detected_priority = final_state.get("detected_priority")
        agent_run.risk_level = final_state.get("risk_level", AgentRiskLevel.LOW.value)
        agent_run.decision = final_state.get("decision", AgentDecision.NO_ACTION.value)
        agent_run.draft_response = final_state.get("draft_response")
        agent_run.reasoning_summary = final_state.get("reasoning_summary")
        agent_run.planned_tools = final_state.get("planned_tools")
        agent_run.retrieved_context = final_state.get("knowledge_context")
        agent_run.final_state = dict(final_state)
        agent_run.duration_ms = duration_ms
        agent_run.completed_at = datetime.now(timezone.utc)

        add_agent_timeline_event(
            db=db,
            organization_id=organization_id,
            ticket_id=ticket_id,
            actor_user_id=user_id,
            event_type=TicketTimelineEventType.AGENT_RUN_COMPLETED,
            title="Agent run completed",
            description=f"Decision: {agent_run.decision}",
        )

        db.commit()
        db.refresh(agent_run)

        return agent_run

    except Exception as exc:
        duration_ms = int((time.perf_counter() - started_at) * 1000)

        agent_run.status = AgentRunStatus.FAILED.value
        agent_run.error_message = str(exc)
        agent_run.duration_ms = duration_ms
        agent_run.completed_at = datetime.now(timezone.utc)

        add_agent_timeline_event(
            db=db,
            organization_id=organization_id,
            ticket_id=ticket_id,
            actor_user_id=user_id,
            event_type=TicketTimelineEventType.AGENT_RUN_FAILED,
            title="Agent run failed",
            description=str(exc),
        )

        db.commit()
        db.refresh(agent_run)

        raise