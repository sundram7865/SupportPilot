from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.enums import (
    ApprovalRequestStatus,
    CustomerReplyDraftStatus,
    TicketSlaStatus,
    TicketStatus,
    ToolExecutionStatus,
)
from app.modules.agent.models import AgentRun
from app.modules.approvals.models import ApprovalRequest
from app.modules.audit.models import AuditLog
from app.modules.replies.models import CustomerReplyDraft
from app.modules.tickets.models import Ticket
from app.modules.tools.models import ToolExecution
from app.modules.analytics.schemas import AnalyticsBreakdownItem, AnalyticsOverviewResponse, AnalyticsTrendPoint


def count_rows(db: Session, model, organization_id: UUID, *conditions) -> int:
    query = select(func.count(model.id)).where(model.organization_id == organization_id)

    for condition in conditions:
        query = query.where(condition)

    return db.scalar(query) or 0


def group_count(
    db: Session,
    model,
    column,
    organization_id: UUID,
) -> list[AnalyticsBreakdownItem]:
    rows = db.execute(
        select(column, func.count(model.id))
        .where(model.organization_id == organization_id)
        .group_by(column)
        .order_by(func.count(model.id).desc())
    ).all()

    return [
        AnalyticsBreakdownItem(
            key=str(key) if key is not None else "UNKNOWN",
            count=int(count),
        )
        for key, count in rows
    ]


def average_minutes_between(
    rows: list[tuple[datetime | None, datetime | None]],
) -> float | None:
    durations: list[float] = []

    for start_at, end_at in rows:
        if not start_at or not end_at:
            continue

        seconds = (end_at - start_at).total_seconds()

        if seconds < 0:
            continue

        durations.append(seconds / 60)

    if not durations:
        return None

    return round(sum(durations) / len(durations), 2)


def get_avg_first_response_minutes(
    db: Session,
    organization_id: UUID,
) -> float | None:
    rows = db.execute(
        select(Ticket.created_at, Ticket.first_response_at)
        .where(Ticket.organization_id == organization_id)
        .where(Ticket.first_response_at.is_not(None))
    ).all()

    return average_minutes_between(rows)


def get_avg_resolution_minutes(
    db: Session,
    organization_id: UUID,
) -> float | None:
    rows = db.execute(
        select(Ticket.created_at, Ticket.resolved_at)
        .where(Ticket.organization_id == organization_id)
        .where(Ticket.resolved_at.is_not(None))
    ).all()

    return average_minutes_between(rows)


def get_recent_ticket_trend(
    db: Session,
    organization_id: UUID,
    days: int = 7,
) -> list[AnalyticsTrendPoint]:
    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=days - 1)).date()

    date_counts: dict[str, int] = {
        (start_date + timedelta(days=index)).isoformat(): 0
        for index in range(days)
    }

    rows = db.execute(
        select(Ticket.created_at)
        .where(Ticket.organization_id == organization_id)
        .where(Ticket.created_at >= datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc))
    ).all()

    for (created_at,) in rows:
        if not created_at:
            continue

        key = created_at.date().isoformat()

        if key in date_counts:
            date_counts[key] += 1

    return [
        AnalyticsTrendPoint(date=date_key, count=count)
        for date_key, count in date_counts.items()
    ]


def get_analytics_overview(
    db: Session,
    organization_id: UUID,
) -> AnalyticsOverviewResponse:
    total_tickets = count_rows(db, Ticket, organization_id)

    open_tickets = count_rows(
        db,
        Ticket,
        organization_id,
        Ticket.status == TicketStatus.OPEN.value,
    )

    in_progress_tickets = count_rows(
        db,
        Ticket,
        organization_id,
        Ticket.status == TicketStatus.IN_PROGRESS.value,
    )

    waiting_tickets = count_rows(
        db,
        Ticket,
        organization_id,
        Ticket.status.in_(
            [
                TicketStatus.WAITING_FOR_CUSTOMER.value,
                TicketStatus.WAITING_FOR_INTERNAL_REVIEW.value,
            ]
        ),
    )

    resolved_tickets = count_rows(
        db,
        Ticket,
        organization_id,
        Ticket.status == TicketStatus.RESOLVED.value,
    )

    closed_tickets = count_rows(
        db,
        Ticket,
        organization_id,
        Ticket.status == TicketStatus.CLOSED.value,
    )

    urgent_tickets = count_rows(
        db,
        Ticket,
        organization_id,
        Ticket.priority == "URGENT",
    )

    sla_ok_tickets = count_rows(
        db,
        Ticket,
        organization_id,
        Ticket.sla_status == TicketSlaStatus.OK.value,
    )

    sla_near_breach_tickets = count_rows(
        db,
        Ticket,
        organization_id,
        Ticket.sla_status == TicketSlaStatus.NEAR_BREACH.value,
    )

    sla_breached_tickets = count_rows(
        db,
        Ticket,
        organization_id,
        Ticket.sla_status == TicketSlaStatus.BREACHED.value,
    )

    agent_runs_total = count_rows(db, AgentRun, organization_id)
    agent_runs_completed = count_rows(
        db,
        AgentRun,
        organization_id,
        AgentRun.status == "COMPLETED",
    )
    agent_runs_failed = count_rows(
        db,
        AgentRun,
        organization_id,
        AgentRun.status == "FAILED",
    )

    tool_executions_total = count_rows(db, ToolExecution, organization_id)
    tool_executions_success = count_rows(
        db,
        ToolExecution,
        organization_id,
        ToolExecution.status == ToolExecutionStatus.SUCCESS.value,
    )
    tool_executions_failed = count_rows(
        db,
        ToolExecution,
        organization_id,
        ToolExecution.status == ToolExecutionStatus.FAILED.value,
    )
    tool_executions_blocked = count_rows(
        db,
        ToolExecution,
        organization_id,
        ToolExecution.status == ToolExecutionStatus.BLOCKED_APPROVAL_REQUIRED.value,
    )

    approvals_total = count_rows(db, ApprovalRequest, organization_id)
    approvals_pending = count_rows(
        db,
        ApprovalRequest,
        organization_id,
        ApprovalRequest.status == ApprovalRequestStatus.PENDING.value,
    )
    approvals_approved = count_rows(
        db,
        ApprovalRequest,
        organization_id,
        ApprovalRequest.status == ApprovalRequestStatus.APPROVED.value,
    )
    approvals_rejected = count_rows(
        db,
        ApprovalRequest,
        organization_id,
        ApprovalRequest.status == ApprovalRequestStatus.REJECTED.value,
    )

    replies_total = count_rows(db, CustomerReplyDraft, organization_id)
    replies_sent = count_rows(
        db,
        CustomerReplyDraft,
        organization_id,
        CustomerReplyDraft.status == CustomerReplyDraftStatus.SENT.value,
    )

    audit_events_total = count_rows(db, AuditLog, organization_id)

    return AnalyticsOverviewResponse(
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        in_progress_tickets=in_progress_tickets,
        waiting_tickets=waiting_tickets,
        resolved_tickets=resolved_tickets,
        closed_tickets=closed_tickets,
        urgent_tickets=urgent_tickets,
        sla_ok_tickets=sla_ok_tickets,
        sla_near_breach_tickets=sla_near_breach_tickets,
        sla_breached_tickets=sla_breached_tickets,
        agent_runs_total=agent_runs_total,
        agent_runs_completed=agent_runs_completed,
        agent_runs_failed=agent_runs_failed,
        tool_executions_total=tool_executions_total,
        tool_executions_success=tool_executions_success,
        tool_executions_failed=tool_executions_failed,
        tool_executions_blocked=tool_executions_blocked,
        approvals_total=approvals_total,
        approvals_pending=approvals_pending,
        approvals_approved=approvals_approved,
        approvals_rejected=approvals_rejected,
        replies_total=replies_total,
        replies_sent=replies_sent,
        audit_events_total=audit_events_total,
        avg_first_response_minutes=get_avg_first_response_minutes(
            db=db,
            organization_id=organization_id,
        ),
        avg_resolution_minutes=get_avg_resolution_minutes(
            db=db,
            organization_id=organization_id,
        ),
        tickets_by_status=group_count(db, Ticket, Ticket.status, organization_id),
        tickets_by_priority=group_count(db, Ticket, Ticket.priority, organization_id),
        tickets_by_category=group_count(db, Ticket, Ticket.category, organization_id),
        tickets_by_source=group_count(db, Ticket, Ticket.source, organization_id),
        tickets_by_sla_status=group_count(db, Ticket, Ticket.sla_status, organization_id),
        recent_ticket_trend=get_recent_ticket_trend(
            db=db,
            organization_id=organization_id,
        ),
    )