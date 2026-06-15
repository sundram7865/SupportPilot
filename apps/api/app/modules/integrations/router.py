from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.common.enums import IntegrationProvider, IntegrationStatus
from app.db.session import get_db
from app.modules.auth.dependencies import get_current_organization, require_permission
from app.modules.auth.permissions import Permission
from app.modules.integrations.crypto import decrypt_secret, encrypt_secret
from app.modules.integrations.models import ExternalApiLog, IntegrationConnection
from app.modules.integrations.schemas import (
    ExternalApiLogResponse,
    UpsertUrbanKartIntegrationRequest,
    UrbanKartHealthCheckResponse,
    UrbanKartIntegrationResponse,
)
from app.modules.integrations.urbankart_client import UrbanKartClient
from app.modules.organizations.models import Organization

router = APIRouter(prefix="/integrations", tags=["Integrations"])


def to_integration_response(
    connection: IntegrationConnection,
) -> UrbanKartIntegrationResponse:
    return UrbanKartIntegrationResponse(
        id=str(connection.id),
        organization_id=str(connection.organization_id),
        provider=connection.provider,
        base_url=connection.base_url,
        status=connection.status,
        last_health_status=connection.last_health_status,
        last_health_message=connection.last_health_message,
        last_checked_at=connection.last_checked_at,
    )


def get_urbankart_connection_or_404(
    organization: Organization,
    db: Session,
) -> IntegrationConnection:
    connection = db.scalar(
        select(IntegrationConnection)
        .where(IntegrationConnection.organization_id == organization.id)
        .where(IntegrationConnection.provider == IntegrationProvider.URBANKART.value)
    )

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="UrbanKart integration is not configured for this organization.",
        )

    return connection


def get_urbankart_client(
    organization: Organization,
    db: Session,
) -> UrbanKartClient:
    connection = get_urbankart_connection_or_404(organization, db)

    if connection.status == IntegrationStatus.INACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="UrbanKart integration is inactive.",
        )

    api_key = decrypt_secret(connection.encrypted_api_key)

    return UrbanKartClient(
        connection=connection,
        api_key=api_key,
        db=db,
    )


@router.put(
    "/urbankart",
    response_model=UrbanKartIntegrationResponse,
    dependencies=[Depends(require_permission(Permission.ORGANIZATION_UPDATE))],
)
def upsert_urbankart_integration(
    payload: UpsertUrbanKartIntegrationRequest,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    connection = db.scalar(
        select(IntegrationConnection)
        .where(IntegrationConnection.organization_id == organization.id)
        .where(IntegrationConnection.provider == IntegrationProvider.URBANKART.value)
    )

    encrypted_api_key = encrypt_secret(payload.api_key)

    if connection:
        connection.base_url = payload.base_url.rstrip("/")
        connection.encrypted_api_key = encrypted_api_key
        connection.status = IntegrationStatus.ACTIVE.value
    else:
        connection = IntegrationConnection(
            organization_id=organization.id,
            provider=IntegrationProvider.URBANKART.value,
            base_url=payload.base_url.rstrip("/"),
            encrypted_api_key=encrypted_api_key,
            status=IntegrationStatus.ACTIVE.value,
        )
        db.add(connection)

    db.commit()
    db.refresh(connection)

    return to_integration_response(connection)


@router.get(
    "/urbankart",
    response_model=UrbanKartIntegrationResponse,
    dependencies=[Depends(require_permission(Permission.ORGANIZATION_READ))],
)
def get_urbankart_integration(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    connection = get_urbankart_connection_or_404(organization, db)
    return to_integration_response(connection)


@router.post(
    "/urbankart/test-connection",
    response_model=UrbanKartHealthCheckResponse,
    dependencies=[Depends(require_permission(Permission.ORGANIZATION_UPDATE))],
)
async def test_urbankart_connection(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    connection = get_urbankart_connection_or_404(organization, db)
    client = get_urbankart_client(organization, db)

    try:
        result = await client.health()

        connection.last_health_status = "OK"
        connection.last_health_message = "UrbanKart connection successful."
        connection.last_checked_at = datetime.now(timezone.utc)
        connection.status = IntegrationStatus.ACTIVE.value

        db.commit()
        db.refresh(connection)

        return UrbanKartHealthCheckResponse(
            connected=True,
            status_code=200,
            message="UrbanKart connection successful.",
            provider_response=result,
        )

    except Exception as exc:
        connection.last_health_status = "FAILED"
        connection.last_health_message = str(exc)
        connection.last_checked_at = datetime.now(timezone.utc)
        connection.status = IntegrationStatus.ERROR.value

        db.commit()

        return UrbanKartHealthCheckResponse(
            connected=False,
            status_code=None,
            message=f"UrbanKart connection failed: {str(exc)}",
            provider_response=None,
        )


@router.patch(
    "/urbankart/deactivate",
    response_model=UrbanKartIntegrationResponse,
    dependencies=[Depends(require_permission(Permission.ORGANIZATION_UPDATE))],
)
def deactivate_urbankart_integration(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    connection = get_urbankart_connection_or_404(organization, db)

    connection.status = IntegrationStatus.INACTIVE.value

    db.commit()
    db.refresh(connection)

    return to_integration_response(connection)


@router.get(
    "/urbankart/orders/{order_id}",
    dependencies=[Depends(require_permission(Permission.ORGANIZATION_READ))],
)
async def get_order_details_from_urbankart(
    order_id: str,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    client = get_urbankart_client(organization, db)

    try:
        order = await client.get_order_details(order_id)
        payment = await client.get_payment_status(order_id)
        shipment = await client.get_shipment_status(order_id)

        return {
            "order": order,
            "payment": payment,
            "shipment": shipment,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch UrbanKart order data: {str(exc)}",
        )


@router.get(
    "/logs",
    response_model=list[ExternalApiLogResponse],
    dependencies=[Depends(require_permission(Permission.AUDIT_VIEW))],
)
def list_external_api_logs(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    logs = db.scalars(
        select(ExternalApiLog)
        .where(ExternalApiLog.organization_id == organization.id)
        .order_by(desc(ExternalApiLog.created_at))
        .limit(50)
    ).all()

    return [
        ExternalApiLogResponse(
            id=str(log.id),
            provider=log.provider,
            method=log.method,
            endpoint=log.endpoint,
            status=log.status,
            status_code=log.status_code,
            duration_ms=log.duration_ms,
            error_message=log.error_message,
            created_at=log.created_at,
        )
        for log in logs
    ]