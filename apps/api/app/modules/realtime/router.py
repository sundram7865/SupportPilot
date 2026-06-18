from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_organization,
    require_permission,
)
from app.modules.auth.permissions import Permission
from app.modules.organizations.models import Organization
from app.modules.realtime.event_bus import (
    organization_channel,
    publish_dev_ping,
    ticket_channel,
)
from app.modules.realtime.schemas import DevPingRequest
from app.modules.realtime.sse import redis_sse_generator
from app.modules.tickets.models import Ticket

router = APIRouter(prefix="/realtime", tags=["Realtime"])


def validate_ticket_access(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID,
) -> None:
    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .where(Ticket.organization_id == organization_id)
    )

    if not ticket:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )


@router.get(
    "/tickets/{ticket_id}/timeline/stream",
    dependencies=[Depends(require_permission(Permission.TICKET_READ))],
)
async def stream_ticket_timeline(
    ticket_id: UUID,
    request: Request,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    validate_ticket_access(
        db=db,
        organization_id=organization.id,
        ticket_id=ticket_id,
    )

    return StreamingResponse(
        redis_sse_generator(
            request=request,
            channel=ticket_channel(ticket_id),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/organizations/stream",
    dependencies=[Depends(require_permission(Permission.TICKET_READ))],
)
async def stream_organization_events(
    request: Request,
    organization: Organization = Depends(get_current_organization),
):
    return StreamingResponse(
        redis_sse_generator(
            request=request,
            channel=organization_channel(organization.id),
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/dev/ping",
    dependencies=[Depends(require_permission(Permission.TICKET_READ))],
)
async def dev_ping_realtime(
    payload: DevPingRequest,
    organization: Organization = Depends(get_current_organization),
):
    await publish_dev_ping(
        organization_id=organization.id,
        message=payload.message,
    )

    return {
        "ok": True,
        "message": "Ping published.",
    }