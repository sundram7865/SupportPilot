from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.common.enums import (
    TicketMessageSenderType,
    TicketStatus,
    TicketTimelineEventType,
    TicketTransitionTrigger,
)
from app.modules.tickets.models import (
    Ticket,
    TicketInternalNote,
    TicketMessage,
    TicketStatusTransition,
    TicketTimelineEvent,
)
from app.modules.tickets.state_machine import validate_status_transition


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


def record_status_transition(
    db: Session,
    ticket: Ticket,
    actor_user_id: UUID | None,
    from_status: str,
    to_status: str,
    trigger: TicketTransitionTrigger,
    reason: str | None,
    is_allowed: bool,
    blocked_reason: str | None = None,
    metadata_json: dict | None = None,
) -> TicketStatusTransition:
    transition = TicketStatusTransition(
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        actor_user_id=actor_user_id,
        from_status=from_status,
        to_status=to_status,
        trigger=trigger.value,
        reason=reason,
        is_allowed=is_allowed,
        blocked_reason=blocked_reason,
        metadata_json=metadata_json,
    )

    db.add(transition)

    return transition


def transition_ticket_status(
    db: Session,
    ticket: Ticket,
    to_status: TicketStatus,
    actor_user_id: UUID | None,
    trigger: TicketTransitionTrigger = TicketTransitionTrigger.AGENT_ACTION,
    reason: str | None = None,
    metadata_json: dict | None = None,
) -> TicketStatusTransition:
    from_status = ticket.status
    validation = validate_status_transition(
        from_status=from_status,
        to_status=to_status.value,
    )

    if not validation.allowed:
        record_status_transition(
            db=db,
            ticket=ticket,
            actor_user_id=actor_user_id,
            from_status=from_status,
            to_status=to_status.value,
            trigger=trigger,
            reason=reason,
            is_allowed=False,
            blocked_reason=validation.reason,
            metadata_json=metadata_json,
        )

        add_timeline_event(
            db=db,
            organization_id=ticket.organization_id,
            ticket_id=ticket.id,
            actor_user_id=actor_user_id,
            event_type=TicketTimelineEventType.LIFECYCLE_TRANSITION_BLOCKED,
            title="Status transition blocked",
            description=validation.reason,
            old_value=from_status,
            new_value=to_status.value,
        )

        db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=validation.reason,
        )

    transition = record_status_transition(
        db=db,
        ticket=ticket,
        actor_user_id=actor_user_id,
        from_status=from_status,
        to_status=to_status.value,
        trigger=trigger,
        reason=reason,
        is_allowed=True,
        metadata_json=metadata_json,
    )

    ticket.status = to_status.value
    ticket.status_changed_at = datetime.now(timezone.utc)
    ticket.status_changed_by_user_id = actor_user_id
    ticket.status_reason = reason

    apply_status_side_effects(ticket, to_status.value)

    add_timeline_event(
        db=db,
        organization_id=ticket.organization_id,
        ticket_id=ticket.id,
        actor_user_id=actor_user_id,
        event_type=TicketTimelineEventType.LIFECYCLE_TRANSITION,
        title="Ticket status changed",
        description=reason,
        old_value=from_status,
        new_value=to_status.value,
    )

    return transition