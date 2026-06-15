from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.common.enums import (
    TicketMessageSenderType,
    TicketTimelineEventType,
)
from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_organization,
    get_or_create_current_user,
    require_permission,
)
from app.modules.auth.permissions import Permission
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.tickets.models import Ticket, TicketInternalNote, TicketMessage, TicketTimelineEvent
from app.modules.tickets.schemas import (
    AddInternalNoteRequest,
    AddTicketMessageRequest,
    CreateTicketRequest,
    TicketDetailResponse,
    TicketInternalNoteResponse,
    TicketListItemResponse,
    TicketListResponse,
    TicketMessageResponse,
    TicketTimelineEventResponse,
    UpdateTicketRequest,
)
from app.modules.tickets.service import (
    add_internal_note,
    add_public_message,
    add_timeline_event,
    apply_status_side_effects,
    generate_ticket_number,
)
from app.modules.users.models import User

router = APIRouter(prefix="/tickets", tags=["Tickets"])


def get_ticket_or_404(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID,
) -> Ticket:
    ticket = db.scalar(
        select(Ticket)
        .options(
            selectinload(Ticket.messages),
            selectinload(Ticket.internal_notes),
            selectinload(Ticket.timeline_events),
        )
        .where(Ticket.id == ticket_id)
        .where(Ticket.organization_id == organization_id)
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    return ticket


def to_message_response(message: TicketMessage) -> TicketMessageResponse:
    return TicketMessageResponse(
        id=str(message.id),
        sender_type=message.sender_type,
        sender_user_id=str(message.sender_user_id) if message.sender_user_id else None,
        sender_name=message.sender_name,
        sender_email=message.sender_email,
        body=message.body,
        is_public=message.is_public,
        created_at=message.created_at,
    )


def to_internal_note_response(note: TicketInternalNote) -> TicketInternalNoteResponse:
    return TicketInternalNoteResponse(
        id=str(note.id),
        author_user_id=str(note.author_user_id) if note.author_user_id else None,
        body=note.body,
        created_at=note.created_at,
    )


def to_timeline_event_response(event: TicketTimelineEvent) -> TicketTimelineEventResponse:
    return TicketTimelineEventResponse(
        id=str(event.id),
        actor_user_id=str(event.actor_user_id) if event.actor_user_id else None,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        old_value=event.old_value,
        new_value=event.new_value,
        created_at=event.created_at,
    )


def to_ticket_list_item(ticket: Ticket) -> TicketListItemResponse:
    return TicketListItemResponse(
        id=str(ticket.id),
        ticket_number=ticket.ticket_number,
        subject=ticket.subject,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        source=ticket.source,
        customer_name=ticket.customer_name,
        customer_email=ticket.customer_email,
        external_order_id=ticket.external_order_id,
        assigned_to_user_id=(
            str(ticket.assigned_to_user_id) if ticket.assigned_to_user_id else None
        ),
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    )


def to_ticket_detail(ticket: Ticket) -> TicketDetailResponse:
    return TicketDetailResponse(
        id=str(ticket.id),
        organization_id=str(ticket.organization_id),
        ticket_number=ticket.ticket_number,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        source=ticket.source,
        customer_name=ticket.customer_name,
        customer_email=ticket.customer_email,
        customer_phone=ticket.customer_phone,
        external_order_id=ticket.external_order_id,
        assigned_to_user_id=(
            str(ticket.assigned_to_user_id) if ticket.assigned_to_user_id else None
        ),
        created_by_user_id=(
            str(ticket.created_by_user_id) if ticket.created_by_user_id else None
        ),
        first_response_at=ticket.first_response_at,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        ai_summary=ticket.ai_summary,
        ai_confidence_score=ticket.ai_confidence_score,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        messages=[to_message_response(message) for message in ticket.messages],
        internal_notes=[to_internal_note_response(note) for note in ticket.internal_notes],
        timeline_events=[
            to_timeline_event_response(event) for event in ticket.timeline_events
        ],
    )


def ensure_assignee_is_org_member(
    db: Session,
    organization_id: UUID,
    assigned_to_user_id: UUID | None,
) -> None:
    if assigned_to_user_id is None:
        return

    membership = db.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == organization_id)
        .where(OrganizationMember.user_id == assigned_to_user_id)
        .where(OrganizationMember.status == "ACTIVE")
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assigned user must be an active member of the organization.",
        )


@router.post(
    "",
    response_model=TicketDetailResponse,
    dependencies=[Depends(require_permission(Permission.TICKET_CREATE))],
)
def create_ticket(
    payload: CreateTicketRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    ticket = Ticket(
        organization_id=organization.id,
        ticket_number=generate_ticket_number(db, organization.id),
        subject=payload.subject,
        description=payload.description,
        status="OPEN",
        priority=payload.priority.value,
        category=payload.category.value,
        source=payload.source.value,
        customer_name=payload.customer_name,
        customer_email=str(payload.customer_email),
        customer_phone=payload.customer_phone,
        external_order_id=payload.external_order_id,
        created_by_user_id=current_user.id,
        metadata_json=payload.metadata_json,
    )

    db.add(ticket)
    db.flush()

    add_public_message(
        db=db,
        ticket=ticket,
        body=payload.description,
        sender_type=TicketMessageSenderType.CUSTOMER,
        sender_name=payload.customer_name,
        sender_email=str(payload.customer_email),
    )

    add_timeline_event(
        db=db,
        organization_id=organization.id,
        ticket_id=ticket.id,
        actor_user_id=current_user.id,
        event_type=TicketTimelineEventType.TICKET_CREATED,
        title="Ticket created",
        description=f"Ticket {ticket.ticket_number} was created.",
    )

    db.commit()

    ticket = get_ticket_or_404(db, organization.id, ticket.id)

    return to_ticket_detail(ticket)


@router.get(
    "",
    response_model=TicketListResponse,
    dependencies=[Depends(require_permission(Permission.TICKET_READ))],
)
def list_tickets(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    category: str | None = Query(default=None),
    assigned_to_user_id: UUID | None = Query(default=None),
    customer_email: str | None = Query(default=None),
    external_order_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    filters = [Ticket.organization_id == organization.id]

    if status_filter:
        filters.append(Ticket.status == status_filter)

    if priority:
        filters.append(Ticket.priority == priority)

    if category:
        filters.append(Ticket.category == category)

    if assigned_to_user_id:
        filters.append(Ticket.assigned_to_user_id == assigned_to_user_id)

    if customer_email:
        filters.append(Ticket.customer_email == customer_email)

    if external_order_id:
        filters.append(Ticket.external_order_id == external_order_id)

    if search:
        like_pattern = f"%{search}%"
        filters.append(
            Ticket.subject.ilike(like_pattern)
            | Ticket.description.ilike(like_pattern)
            | Ticket.customer_email.ilike(like_pattern)
            | Ticket.ticket_number.ilike(like_pattern)
        )

    total = db.scalar(select(func.count(Ticket.id)).where(and_(*filters))) or 0

    tickets = db.scalars(
        select(Ticket)
        .where(and_(*filters))
        .order_by(desc(Ticket.created_at))
        .limit(limit)
        .offset(offset)
    ).all()

    return TicketListResponse(
        items=[to_ticket_list_item(ticket) for ticket in tickets],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    dependencies=[Depends(require_permission(Permission.TICKET_READ))],
)
def get_ticket(
    ticket_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(db, organization.id, ticket_id)
    return to_ticket_detail(ticket)


@router.patch(
    "/{ticket_id}",
    response_model=TicketDetailResponse,
    dependencies=[Depends(require_permission(Permission.TICKET_UPDATE))],
)
def update_ticket(
    ticket_id: UUID,
    payload: UpdateTicketRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(db, organization.id, ticket_id)

    if payload.assigned_to_user_id is not None:
        ensure_assignee_is_org_member(db, organization.id, payload.assigned_to_user_id)

    if payload.subject is not None:
        ticket.subject = payload.subject

    if payload.description is not None:
        ticket.description = payload.description

    if payload.status is not None and ticket.status != payload.status.value:
        old_value = ticket.status
        ticket.status = payload.status.value
        apply_status_side_effects(ticket, payload.status.value)

        add_timeline_event(
            db=db,
            organization_id=organization.id,
            ticket_id=ticket.id,
            actor_user_id=current_user.id,
            event_type=TicketTimelineEventType.STATUS_CHANGED,
            title="Status changed",
            old_value=old_value,
            new_value=payload.status.value,
        )

    if payload.priority is not None and ticket.priority != payload.priority.value:
        old_value = ticket.priority
        ticket.priority = payload.priority.value

        add_timeline_event(
            db=db,
            organization_id=organization.id,
            ticket_id=ticket.id,
            actor_user_id=current_user.id,
            event_type=TicketTimelineEventType.PRIORITY_CHANGED,
            title="Priority changed",
            old_value=old_value,
            new_value=payload.priority.value,
        )

    if payload.category is not None and ticket.category != payload.category.value:
        old_value = ticket.category
        ticket.category = payload.category.value

        add_timeline_event(
            db=db,
            organization_id=organization.id,
            ticket_id=ticket.id,
            actor_user_id=current_user.id,
            event_type=TicketTimelineEventType.CATEGORY_CHANGED,
            title="Category changed",
            old_value=old_value,
            new_value=payload.category.value,
        )

    if payload.assigned_to_user_id is not None:
        old_value = str(ticket.assigned_to_user_id) if ticket.assigned_to_user_id else None
        ticket.assigned_to_user_id = payload.assigned_to_user_id

        add_timeline_event(
            db=db,
            organization_id=organization.id,
            ticket_id=ticket.id,
            actor_user_id=current_user.id,
            event_type=TicketTimelineEventType.ASSIGNEE_CHANGED,
            title="Assignee changed",
            old_value=old_value,
            new_value=str(payload.assigned_to_user_id),
        )

    customer_changed = False

    if payload.customer_name is not None:
        ticket.customer_name = payload.customer_name
        customer_changed = True

    if payload.customer_email is not None:
        ticket.customer_email = str(payload.customer_email)
        customer_changed = True

    if payload.customer_phone is not None:
        ticket.customer_phone = payload.customer_phone
        customer_changed = True

    if payload.external_order_id is not None:
        ticket.external_order_id = payload.external_order_id
        customer_changed = True

    if customer_changed:
        add_timeline_event(
            db=db,
            organization_id=organization.id,
            ticket_id=ticket.id,
            actor_user_id=current_user.id,
            event_type=TicketTimelineEventType.CUSTOMER_UPDATED,
            title="Customer details updated",
        )

    db.commit()

    ticket = get_ticket_or_404(db, organization.id, ticket_id)

    return to_ticket_detail(ticket)


@router.post(
    "/{ticket_id}/messages",
    response_model=TicketMessageResponse,
    dependencies=[Depends(require_permission(Permission.TICKET_UPDATE))],
)
def add_ticket_message(
    ticket_id: UUID,
    payload: AddTicketMessageRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(db, organization.id, ticket_id)

    sender_user_id = None

    if payload.sender_type in {
        TicketMessageSenderType.AGENT,
        TicketMessageSenderType.AI,
        TicketMessageSenderType.SYSTEM,
    }:
        sender_user_id = current_user.id

    message = add_public_message(
        db=db,
        ticket=ticket,
        body=payload.body,
        sender_type=payload.sender_type,
        sender_user_id=sender_user_id,
        sender_name=payload.sender_name or current_user.name,
        sender_email=str(payload.sender_email) if payload.sender_email else current_user.email,
        metadata_json=payload.metadata_json,
    )

    db.commit()
    db.refresh(message)

    return to_message_response(message)


@router.post(
    "/{ticket_id}/internal-notes",
    response_model=TicketInternalNoteResponse,
    dependencies=[Depends(require_permission(Permission.TICKET_INTERNAL_NOTE))],
)
def add_ticket_internal_note(
    ticket_id: UUID,
    payload: AddInternalNoteRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(db, organization.id, ticket_id)

    note = add_internal_note(
        db=db,
        ticket=ticket,
        body=payload.body,
        author_user_id=current_user.id,
        metadata_json=payload.metadata_json,
    )

    db.commit()
    db.refresh(note)

    return to_internal_note_response(note)


@router.get(
    "/{ticket_id}/timeline",
    response_model=list[TicketTimelineEventResponse],
    dependencies=[Depends(require_permission(Permission.TICKET_READ))],
)
def get_ticket_timeline(
    ticket_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    ticket = get_ticket_or_404(db, organization.id, ticket_id)

    return [to_timeline_event_response(event) for event in ticket.timeline_events]