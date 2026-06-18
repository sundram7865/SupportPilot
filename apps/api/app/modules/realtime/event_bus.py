import json
from datetime import datetime
from uuid import UUID

import redis.asyncio as redis

from app.core.config import settings


REDIS_CHANNEL_ORGANIZATION_PREFIX = "supportpilot:org"
REDIS_CHANNEL_TICKET_PREFIX = "supportpilot:ticket"


def serialize_for_json(value):
    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def ticket_channel(ticket_id: UUID | str) -> str:
    return f"{REDIS_CHANNEL_TICKET_PREFIX}:{ticket_id}:timeline"


def organization_channel(organization_id: UUID | str) -> str:
    return f"{REDIS_CHANNEL_ORGANIZATION_PREFIX}:{organization_id}:timeline"


async def get_redis_client():
    return redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


async def publish_event(channel: str, payload: dict) -> None:
    client = await get_redis_client()

    try:
        await client.publish(
            channel,
            json.dumps(payload, default=serialize_for_json),
        )
    finally:
        await client.aclose()


async def publish_timeline_event(
    organization_id: UUID | str,
    ticket_id: UUID | str,
    event: dict,
) -> None:
    payload = {
        "type": "timeline_event",
        "organization_id": str(organization_id),
        "ticket_id": str(ticket_id),
        "event": event,
    }

    await publish_event(ticket_channel(ticket_id), payload)
    await publish_event(organization_channel(organization_id), payload)


async def publish_dev_ping(
    organization_id: UUID | str,
    message: str,
) -> None:
    payload = {
        "type": "dev_ping",
        "organization_id": str(organization_id),
        "message": message,
        "created_at": datetime.utcnow().isoformat(),
    }

    await publish_event(organization_channel(organization_id), payload)