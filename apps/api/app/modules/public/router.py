from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import (
    TicketCategory,
    TicketMessageSenderType,
    TicketPriority,
    TicketSource,
    TicketStatus,
    TicketTimelineEventType,
)
from app.db.session import get_db
from app.modules.organizations.models import Organization
from app.modules.public.schemas import (
    PublicOrganizationResponse,
    PublicTicketCreateRequest,
    PublicTicketCreateResponse,
)
from app.core.rate_limit import public_read_rate_limit, public_write_rate_limit
from app.modules.tickets.models import Ticket, TicketMessage, TicketTimelineEvent
from app.modules.tickets.service import generate_ticket_number

router = APIRouter(prefix="/public", tags=["Public Intake"])


def get_public_organization_or_404(
    db: Session,
    slug: str,
) -> Organization:
    organization = db.scalar(
        select(Organization).where(Organization.slug == slug)
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Support portal not found.",
        )

    return organization


@router.get(
    "/organizations/{slug}",
    response_model=PublicOrganizationResponse,
     dependencies=[Depends(public_read_rate_limit)]
)
def get_public_organization(
    slug: str,
    db: Session = Depends(get_db),
):
    organization = get_public_organization_or_404(db, slug)

    return PublicOrganizationResponse(
        id=str(organization.id),
        name=organization.name,
        slug=organization.slug,
        support_email=organization.support_email,
    )


@router.post(
    "/organizations/{slug}/tickets",
    response_model=PublicTicketCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(public_write_rate_limit)],
)
def create_public_ticket(
    slug: str,
    payload: PublicTicketCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    organization = get_public_organization_or_404(db, slug)

    metadata_json = payload.metadata_json or {}
    metadata_json.update(
        {
            "intake_channel": "public_support_form",
            "organization_slug": slug,
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
    )

    ticket = Ticket(
        organization_id=organization.id,
        ticket_number=generate_ticket_number(db, organization.id),
        subject=payload.subject,
        description=payload.description,
        status=TicketStatus.OPEN.value,
        priority=TicketPriority.MEDIUM.value,
        category=TicketCategory.OTHER.value,
        source=TicketSource.SUPPORT_FORM.value,
        customer_name=payload.customer_name,
        customer_email=str(payload.customer_email),
        customer_phone=payload.customer_phone,
        external_order_id=payload.external_order_id,
        created_by_user_id=None,
        status_changed_by_user_id=None,
        status_reason="Ticket created from public support form.",
        metadata_json=metadata_json,
    )

    db.add(ticket)
    db.flush()

    message = TicketMessage(
        organization_id=organization.id,
        ticket_id=ticket.id,
        sender_type=TicketMessageSenderType.CUSTOMER.value,
        sender_user_id=None,
        sender_name=payload.customer_name,
        sender_email=str(payload.customer_email),
        body=payload.description,
        is_public=True,
        metadata_json={
            "intake_channel": "public_support_form",
        },
    )

    db.add(message)

    timeline_event = TicketTimelineEvent(
        organization_id=organization.id,
        ticket_id=ticket.id,
        actor_user_id=None,
        event_type=TicketTimelineEventType.TICKET_CREATED.value,
        title="Ticket created from public support form",
        description=f"Customer submitted ticket {ticket.ticket_number}.",
        metadata_json={
            "intake_channel": "public_support_form",
        },
    )

    db.add(timeline_event)

    db.commit()
    db.refresh(ticket)

    return PublicTicketCreateResponse(
        id=str(ticket.id),
        organization_id=str(ticket.organization_id),
        ticket_number=ticket.ticket_number,
        subject=ticket.subject,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        source=ticket.source,
        customer_email=ticket.customer_email,
        external_order_id=ticket.external_order_id,
        created_at=ticket.created_at,
        message="Your support ticket has been created successfully.",
    )