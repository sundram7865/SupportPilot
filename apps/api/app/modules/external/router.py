import secrets
import time
from app.core.rate_limit import external_api_rate_limit
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import (
    ExternalApiStatus,
    IntegrationProvider,
    IntegrationStatus,
    TicketMessageSenderType,
    TicketStatus,
    TicketTimelineEventType,
)
from app.db.session import get_db
from app.modules.external.schemas import (
    ExternalTicketCreateRequest,
    ExternalTicketCreateResponse,
)
from app.modules.integrations.crypto import decrypt_secret
from app.modules.integrations.models import ExternalApiLog, IntegrationConnection
from app.modules.organizations.models import Organization
from app.modules.tickets.models import Ticket, TicketMessage, TicketTimelineEvent
from app.modules.tickets.service import generate_ticket_number
from app.modules.tickets.sla import initialize_ticket_sla

router = APIRouter(prefix="/external", tags=["External API"])


EXTERNAL_TICKETS_ENDPOINT = "/external/tickets"


def write_external_api_log(
    db: Session,
    organization_id,
    integration_connection_id,
    status_value: ExternalApiStatus,
    status_code: int | None,
    duration_ms: int,
    request_payload: dict | None = None,
    response_payload: dict | None = None,
    error_message: str | None = None,
) -> None:
    log = ExternalApiLog(
        organization_id=organization_id,
        integration_connection_id=integration_connection_id,
        provider="SUPPORTPILOT_EXTERNAL_API",
        method="POST",
        endpoint=EXTERNAL_TICKETS_ENDPOINT,
        status=status_value.value,
        status_code=status_code,
        duration_ms=duration_ms,
        request_payload=request_payload,
        response_payload=response_payload,
        error_message=error_message,
    )

    db.add(log)
    db.commit()


def get_organization_by_slug_or_404(
    db: Session,
    slug: str,
) -> Organization:
    organization = db.scalar(
        select(Organization).where(Organization.slug == slug)
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    return organization


def get_active_api_connection_or_401(
    db: Session,
    organization: Organization,
    api_key: str,
) -> IntegrationConnection:
    connection = db.scalar(
        select(IntegrationConnection)
        .where(IntegrationConnection.organization_id == organization.id)
        .where(IntegrationConnection.provider == IntegrationProvider.URBANKART.value)
    )

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API access is not configured for this organization.",
        )

    if connection.status != IntegrationStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API access is inactive for this organization.",
        )

    decrypted_api_key = decrypt_secret(connection.encrypted_api_key)

    if not secrets.compare_digest(decrypted_api_key, api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    return connection


@router.post(
    "/tickets",
    response_model=ExternalTicketCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(external_api_rate_limit)]
)
def create_external_ticket(
    payload: ExternalTicketCreateRequest,
    request: Request,
    x_organization_slug: str = Header(..., alias="x-organization-slug"),
    x_supportpilot_api_key: str = Header(..., alias="x-supportpilot-api-key"),
    db: Session = Depends(get_db),
):
    started_at = time.perf_counter()

    organization = get_organization_by_slug_or_404(
        db=db,
        slug=x_organization_slug,
    )

    connection = None

    try:
        connection = get_active_api_connection_or_401(
            db=db,
            organization=organization,
            api_key=x_supportpilot_api_key,
        )

        metadata_json = payload.metadata_json or {}
        metadata_json.update(
            {
                "intake_channel": "external_api",
                "organization_slug": x_organization_slug,
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
            priority=payload.priority,
            category=payload.category,
            source=payload.source,
            customer_name=payload.customer_name,
            customer_email=str(payload.customer_email),
            customer_phone=payload.customer_phone,
            external_order_id=payload.external_order_id,
            created_by_user_id=None,
            status_changed_by_user_id=None,
            status_reason="Ticket created from external API.",
            metadata_json=metadata_json,
        )

        initialize_ticket_sla(ticket)
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
                "intake_channel": "external_api",
            },
        )

        db.add(message)

        timeline_event = TicketTimelineEvent(
            organization_id=organization.id,
            ticket_id=ticket.id,
            actor_user_id=None,
            event_type=TicketTimelineEventType.TICKET_CREATED.value,
            title="Ticket created from external API",
            description=f"External API created ticket {ticket.ticket_number}.",
            metadata_json={
                "intake_channel": "external_api",
            },
        )

        db.add(timeline_event)

        db.commit()
        db.refresh(ticket)

        response_payload = {
            "id": str(ticket.id),
            "ticket_number": ticket.ticket_number,
            "status": ticket.status,
        }

        duration_ms = int((time.perf_counter() - started_at) * 1000)

        write_external_api_log(
            db=db,
            organization_id=organization.id,
            integration_connection_id=connection.id,
            status_value=ExternalApiStatus.SUCCESS,
            status_code=status.HTTP_201_CREATED,
            duration_ms=duration_ms,
            request_payload={
                "subject": payload.subject,
                "customer_email": str(payload.customer_email),
                "external_order_id": payload.external_order_id,
                "source": payload.source,
            },
            response_payload=response_payload,
        )

        return ExternalTicketCreateResponse(
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
            message="Ticket created successfully from external API.",
        )

    except HTTPException as exc:
        duration_ms = int((time.perf_counter() - started_at) * 1000)

        if connection:
            write_external_api_log(
                db=db,
                organization_id=organization.id,
                integration_connection_id=connection.id,
                status_value=ExternalApiStatus.FAILED,
                status_code=exc.status_code,
                duration_ms=duration_ms,
                request_payload={
                    "subject": payload.subject,
                    "customer_email": str(payload.customer_email),
                    "external_order_id": payload.external_order_id,
                    "source": payload.source,
                },
                error_message=str(exc.detail),
            )

        raise

    except Exception as exc:
        db.rollback()

        duration_ms = int((time.perf_counter() - started_at) * 1000)

        if connection:
            write_external_api_log(
                db=db,
                organization_id=organization.id,
                integration_connection_id=connection.id,
                status_value=ExternalApiStatus.FAILED,
                status_code=500,
                duration_ms=duration_ms,
                request_payload={
                    "subject": payload.subject,
                    "customer_email": str(payload.customer_email),
                    "external_order_id": payload.external_order_id,
                    "source": payload.source,
                },
                error_message=str(exc),
            )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create external ticket.",
        )