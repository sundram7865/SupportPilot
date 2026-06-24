from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.common.enums import TicketSlaStatus, TicketStatus
from app.db.session import SessionLocal
from app.modules.tickets.models import Ticket
from app.modules.tickets.sla import update_ticket_sla_status

from app.db.base import import_all_models

import_all_models()

TERMINAL_STATUSES = {
    TicketStatus.RESOLVED.value,
    TicketStatus.CLOSED.value,
}


def get_open_sla_tickets(db: Session) -> list[Ticket]:
    return (
        db.query(Ticket)
        .filter(Ticket.status.notin_(TERMINAL_STATUSES))
        .filter(Ticket.sla_status != TicketSlaStatus.BREACHED.value)
        .all()
    )


from app.worker.celery_app import celery_app


@celery_app.task(name="tickets.check_sla")
def check_ticket_sla() -> dict:
    db = SessionLocal()

    checked = 0
    changed = 0

    try:
        tickets = get_open_sla_tickets(db)

        for ticket in tickets:
            old_status = ticket.sla_status

            update_ticket_sla_status(
                db=db,
                ticket=ticket,
                actor_user_id=None,
                create_timeline_events=True,
            )

            checked += 1

            if ticket.sla_status != old_status:
                changed += 1

        db.commit()

        return {
            "ok": True,
            "checked": checked,
            "changed": changed,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()