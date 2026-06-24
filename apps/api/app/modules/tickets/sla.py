from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.common.enums import (
    TicketPriority,
    TicketSlaStatus,
    TicketStatus,
    TicketTimelineEventType,
)
from app.modules.realtime.publisher import publish_timeline_event_after_commit
from app.modules.tickets.models import Ticket, TicketTimelineEvent


FIRST_RESPONSE_SLA = {
    TicketPriority.URGENT.value: timedelta(minutes=30),
    TicketPriority.HIGH.value: timedelta(hours=1),
    TicketPriority.MEDIUM.value: timedelta(hours=4),
    TicketPriority.LOW.value: timedelta(hours=8),
}

RESOLUTION_SLA = {
    TicketPriority.URGENT.value: timedelta(hours=4),
    TicketPriority.HIGH.value: timedelta(hours=8),
    TicketPriority.MEDIUM.value: timedelta(hours=24),
    TicketPriority.LOW.value: timedelta(hours=48),
}

NEAR_BREACH_WINDOW = timedelta(minutes=30)


def get_sla_start_time(ticket: Ticket) -> datetime:
    if ticket.created_at:
        return ticket.created_at

    return datetime.now(timezone.utc)


def initialize_ticket_sla(ticket: Ticket) -> None:
    now = datetime.now(timezone.utc)

    priority = ticket.priority or TicketPriority.MEDIUM.value

    first_response_delta = FIRST_RESPONSE_SLA.get(
        priority,
        FIRST_RESPONSE_SLA[TicketPriority.MEDIUM.value],
    )

    resolution_delta = RESOLUTION_SLA.get(
        priority,
        RESOLUTION_SLA[TicketPriority.MEDIUM.value],
    )

    start_time = ticket.created_at or now

    ticket.first_response_due_at = start_time + first_response_delta
    ticket.resolution_due_at = start_time + resolution_delta
    ticket.sla_status = TicketSlaStatus.OK.value
    ticket.sla_near_breach_notified_at = None
    ticket.sla_breached_at = None


def is_ticket_resolved(ticket: Ticket) -> bool:
    return ticket.status in {
        TicketStatus.RESOLVED.value,
        TicketStatus.CLOSED.value,
    }


def is_first_response_pending(ticket: Ticket) -> bool:
    return ticket.first_response_at is None


def get_sla_breach_reason(ticket: Ticket, now: datetime) -> str | None:
    if (
        is_first_response_pending(ticket)
        and ticket.first_response_due_at
        and now >= ticket.first_response_due_at
    ):
        return "First response SLA breached."

    if (
        not is_ticket_resolved(ticket)
        and ticket.resolution_due_at
        and now >= ticket.resolution_due_at
    ):
        return "Resolution SLA breached."

    return None


def get_sla_near_breach_reason(ticket: Ticket, now: datetime) -> str | None:
    if (
        is_first_response_pending(ticket)
        and ticket.first_response_due_at
        and now < ticket.first_response_due_at
        and ticket.first_response_due_at - now <= NEAR_BREACH_WINDOW
    ):
        return "First response SLA is near breach."

    if (
        not is_ticket_resolved(ticket)
        and ticket.resolution_due_at
        and now < ticket.resolution_due_at
        and ticket.resolution_due_at - now <= NEAR_BREACH_WINDOW
    ):
        return "Resolution SLA is near breach."

    return None


def add_sla_timeline_event(
    db: Session,
    ticket: Ticket,
    actor_user_id: UUID | None,
    event_type: TicketTimelineEventType,
    title: str,
    description: str,
) -> TicketTimelineEvent:
    event = TicketTimelineEvent(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        actor_user_id=actor_user_id,
        event_type=event_type.value,
        title=title,
        description=description,
        metadata_json={
            "sla_status": ticket.sla_status,
            "first_response_due_at": (
                ticket.first_response_due_at.isoformat()
                if ticket.first_response_due_at
                else None
            ),
            "resolution_due_at": (
                ticket.resolution_due_at.isoformat()
                if ticket.resolution_due_at
                else None
            ),
        },
    )

    db.add(event)
    db.flush()

    return event


def publish_sla_event_after_commit(
    db: Session,
    ticket: Ticket,
    event: TicketTimelineEvent,
) -> None:
    publish_timeline_event_after_commit(
        db=db,
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        event=event,
    )


def update_ticket_sla_status(
    db: Session,
    ticket: Ticket,
    actor_user_id: UUID | None = None,
    create_timeline_events: bool = True,
) -> None:
    now = datetime.now(timezone.utc)

    old_status = ticket.sla_status or TicketSlaStatus.OK.value

    breach_reason = get_sla_breach_reason(ticket, now)

    if breach_reason:
        ticket.sla_status = TicketSlaStatus.BREACHED.value

        should_create_breach_event = ticket.sla_breached_at is None

        if ticket.sla_breached_at is None:
            ticket.sla_breached_at = now

        if create_timeline_events and should_create_breach_event:
            add_sla_timeline_event(
                db=db,
                ticket=ticket,
                actor_user_id=actor_user_id,
                event_type=TicketTimelineEventType.SLA_BREACHED,
                title="SLA breached",
                description=breach_reason,
            )

        return

    near_breach_reason = get_sla_near_breach_reason(ticket, now)

    if near_breach_reason:
        ticket.sla_status = TicketSlaStatus.NEAR_BREACH.value

        should_create_near_event = ticket.sla_near_breach_notified_at is None

        if ticket.sla_near_breach_notified_at is None:
            ticket.sla_near_breach_notified_at = now

        if create_timeline_events and should_create_near_event:
            add_sla_timeline_event(
                db=db,
                ticket=ticket,
                actor_user_id=actor_user_id,
                event_type=TicketTimelineEventType.SLA_NEAR_BREACH,
                title="SLA near breach",
                description=near_breach_reason,
            )

        return

    if old_status != TicketSlaStatus.BREACHED.value:
        ticket.sla_status = TicketSlaStatus.OK.value