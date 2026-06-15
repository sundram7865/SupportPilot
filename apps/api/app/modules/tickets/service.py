from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.enums import (
    TicketMessageSenderType,
    TicketStatus,
    TicketTimelineEventType,
)
from app.modules.tickets.models import (
    Ticket,
    TicketInternalNote,
    TicketMessage,
    TicketTimelineEvent,
)


def generate_ticket_number(db: Session, organization_id: UUID) -> str:
    count = db.scalar(
        select(func.count(Ticket.id)).where(Ticket.organization_id == organization_id)
    )

    next_number = int(count or 0) + 1

    return f"TICK-{next_number:05d}"


def add_timeline_event(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID,
    event_type: TicketTimelineEventType,
    title: str,
    actor_user_id: UUID | None = None,
    description: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    metadata_json: dict | None = None,
) -> TicketTimelineEvent:
    event = TicketTimelineEvent(
        organization_id=organization_id,
        ticket_id=ticket_id,
        actor_user_id=actor_user_id,
        event_type=event_type.value,
        title=title,
        description=description,
        old_value=old_value,
        new_value=new_value,
        metadata_json=metadata_json,
    )

    db.add(event)

    return event


def add_public_message(
    db: Session,
    ticket: Ticket,
    body: str,
    sender_type: TicketMessageSenderType,
    sender_user_id: UUID | None = None,
    sender_name: str | None = None,
    sender_email: str | None = None,
    metadata_json: dict | None = None,
) -> TicketMessage:
    message = TicketMessage(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        sender_type=sender_type.value,
        sender_user_id=sender_user_id,
        sender_name=sender_name,
        sender_email=sender_email,
        body=body,
        is_public=True,
        metadata_json=metadata_json,
    )

    db.add(message)

    add_timeline_event(
        db=db,
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        actor_user_id=sender_user_id,
        event_type=TicketTimelineEventType.MESSAGE_ADDED,
        title="Message added",
        description=f"{sender_type.value} added a public message.",
    )

    if sender_type in {TicketMessageSenderType.AGENT, TicketMessageSenderType.AI}:
        if ticket.first_response_at is None:
            ticket.first_response_at = datetime.now(timezone.utc)

    return message


def add_internal_note(
    db: Session,
    ticket: Ticket,
    body: str,
    author_user_id: UUID | None,
    metadata_json: dict | None = None,
) -> TicketInternalNote:
    note = TicketInternalNote(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        author_user_id=author_user_id,
        body=body,
        metadata_json=metadata_json,
    )

    db.add(note)

    add_timeline_event(
        db=db,
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        actor_user_id=author_user_id,
        event_type=TicketTimelineEventType.INTERNAL_NOTE_ADDED,
        title="Internal note added",
        description="A private internal note was added.",
    )

    return note


def apply_status_side_effects(ticket: Ticket, new_status: str) -> None:
    now = datetime.now(timezone.utc)

    if new_status == TicketStatus.RESOLVED.value and ticket.resolved_at is None:
        ticket.resolved_at = now

    if new_status == TicketStatus.CLOSED.value and ticket.closed_at is None:
        ticket.closed_at = now

    if new_status not in {TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value}:
        ticket.resolved_at = None
        ticket.closed_at = None