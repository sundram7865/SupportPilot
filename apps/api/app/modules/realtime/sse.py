import asyncio
import json
from collections.abc import AsyncGenerator

from starlette.requests import Request

from app.modules.realtime.event_bus import get_redis_client


def format_sse_event(
    data: dict,
    event_name: str = "message",
    event_id: str | None = None,
) -> str:
    lines: list[str] = []

    if event_id:
        lines.append(f"id: {event_id}")

    lines.append(f"event: {event_name}")
    lines.append(f"data: {json.dumps(data)}")
    lines.append("")

    return "\n".join(lines) + "\n"


async def redis_sse_generator(
    request: Request,
    channel: str,
    heartbeat_seconds: int = 15,
) -> AsyncGenerator[str, None]:
    client = await get_redis_client()
    pubsub = client.pubsub()

    await pubsub.subscribe(channel)

    try:
        yield format_sse_event(
            {
                "type": "connected",
                "channel": channel,
            },
            event_name="connected",
        )

        while True:
            if await request.is_disconnected():
                break

            message = await pubsub.get_message(
                ignore_subscribe_messages=True,
                timeout=1.0,
            )

            if message and message.get("type") == "message":
                raw_data = message.get("data")

                try:
                    payload = json.loads(raw_data)
                except Exception:
                    payload = {
                        "type": "raw",
                        "data": raw_data,
                    }

                event_id = None

                if isinstance(payload, dict):
                    event = payload.get("event") or {}
                    if isinstance(event, dict):
                        event_id = event.get("id")

                yield format_sse_event(
                    payload,
                    event_name=payload.get("type", "message")
                    if isinstance(payload, dict)
                    else "message",
                    event_id=event_id,
                )

            await asyncio.sleep(0.05)

    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await client.aclose()