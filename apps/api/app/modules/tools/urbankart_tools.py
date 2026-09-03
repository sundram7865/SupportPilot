from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import IntegrationProvider, IntegrationStatus
from app.modules.integrations.crypto import decrypt_secret
from app.modules.integrations.models import IntegrationConnection
from app.modules.integrations.urbankart_client import UrbanKartClient
from app.modules.organizations.models import Organization


def get_urbankart_client_for_org(
    db: Session,
    organization: Organization,
) -> UrbanKartClient:
    connection = db.scalar(
        select(IntegrationConnection)
        .where(IntegrationConnection.organization_id == organization.id)
        .where(IntegrationConnection.provider == IntegrationProvider.URBANKART.value)
    )

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="UrbanKart integration is not configured.",
        )

    if connection.status != IntegrationStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UrbanKart integration is not active.",
        )

    api_key = decrypt_secret(connection.encrypted_api_key)

    return UrbanKartClient(
        connection=connection,
        api_key=api_key,
        db=db,
    )


async def execute_urbankart_get_order_context(
    db: Session,
    organization: Organization,
    args: dict,
) -> dict:
    order_id = args.get("order_id")

    if not order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_id is required.",
        )

    client = get_urbankart_client_for_org(db, organization)

    order = await client.get_order_details(order_id)
    payment = await client.get_payment_status(order_id)
    shipment = await client.get_shipment_status(order_id)

    return {
        "order": order,
        "payment": payment,
        "shipment": shipment,
    }


async def execute_urbankart_request_refund(
    db: Session,
    organization: Organization,
    args: dict,
    support_ticket_id: UUID | None,
    idempotency_key: str,
) -> dict:
    order_id = args.get("order_id")
    amount = args.get("amount")
    reason = args.get("reason") or "Refund requested from SupportPilot."

    if not order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_id is required.",
        )

    if amount is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="amount is required.",
        )

    client = get_urbankart_client_for_org(db, organization)

    return await client.request_refund(
        order_id=order_id,
        amount=float(amount),
        reason=reason,
        support_ticket_id=str(support_ticket_id) if support_ticket_id else "manual-tool-execution",
        idempotency_key=idempotency_key,
    )


async def execute_urbankart_request_replacement(
    db: Session,
    organization: Organization,
    args: dict,
    support_ticket_id: UUID | None,
    idempotency_key: str,
) -> dict:
    order_id = args.get("order_id")
    reason = args.get("reason") or "Replacement requested from SupportPilot."
    evidence_urls = args.get("evidence_urls") or []

    if not order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_id is required.",
        )

    client = get_urbankart_client_for_org(db, organization)

    return await client.request_replacement(
        order_id=order_id,
        reason=reason,
        support_ticket_id=str(support_ticket_id) if support_ticket_id else "manual-tool-execution",
        idempotency_key=idempotency_key,
        evidence_urls=evidence_urls,
    )