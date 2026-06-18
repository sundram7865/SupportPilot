import asyncio
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.realtime.event_bus import publish_timeline_event
from app.modules.tickets.models import TicketTimelineEvent
from app.modules.tickets.timeline_events import serialize_timeline_event


def publish_timeline_event_after_commit(
    db: Session,
    organization_id: UUID,
    ticket_id: UUID,
    event: TicketTimelineEvent,
) -> None:
    """
    Simple dev-friendly publisher.

    We call this after DB commit/refresh in service functions.
    It is safe for our current sync FastAPI service style.

    Later, in production, this can be moved to an outbox table.
    """

    payload = serialize_timeline_event(event)

    try:
        loop = asyncio.get_event_loop()

        if loop.is_running():
            loop.create_task(
                publish_timeline_event(
                    organization_id=organization_id,
                    ticket_id=ticket_id,
                    event=payload,
                )
            )
        else:
            loop.run_until_complete(
                publish_timeline_event(
                    organization_id=organization_id,
                    ticket_id=ticket_id,
                    event=payload,
                )
            )

    except RuntimeError:
        asyncio.run(
            publish_timeline_event(
                organization_id=organization_id,
                ticket_id=ticket_id,
                event=payload,
            )
        )