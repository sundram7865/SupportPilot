from app.modules.tickets.models import TicketTimelineEvent


def serialize_timeline_event(event: TicketTimelineEvent) -> dict:
    return {
        "id": str(event.id),
        "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
        "event_type": event.event_type,
        "title": event.title,
        "description": event.description,
        "old_value": event.old_value,
        "new_value": event.new_value,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }