import hashlib
from collections.abc import Callable

import redis
from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings


def get_redis_client(settings: Settings) -> redis.Redis:
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )


def get_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host
    else:
        client_ip = "unknown"

    user_agent = request.headers.get("user-agent", "unknown")

    raw_identifier = f"{client_ip}:{user_agent}"

    return hashlib.sha256(raw_identifier.encode("utf-8")).hexdigest()


def get_rate_limit_key(
    request: Request,
    scope: str,
) -> str:
    client_identifier = get_client_identifier(request)
    path_identifier = request.url.path

    return f"rate_limit:{scope}:{client_identifier}:{path_identifier}"


def rate_limit(
    scope: str,
    limit_per_minute: Callable[[Settings], int],
):
    def dependency(
        request: Request,
        settings: Settings = Depends(get_settings),
    ) -> None:
        if not settings.rate_limit_enabled:
            return

        limit = limit_per_minute(settings)

        if limit <= 0:
            return

        key = get_rate_limit_key(request=request, scope=scope)

        try:
            redis_client = get_redis_client(settings)
            current_count = redis_client.incr(key)

            if current_count == 1:
                redis_client.expire(key, 60)

            if current_count > limit:
                ttl = redis_client.ttl(key)

                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please try again later.",
                    headers={
                        "Retry-After": str(ttl if ttl and ttl > 0 else 60),
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                    },
                )

        except HTTPException:
            raise

        except Exception:
            # Fail open: if Redis is temporarily unavailable, do not block support intake.
            return

    return dependency


public_read_rate_limit = rate_limit(
    scope="public_read",
    limit_per_minute=lambda settings: settings.public_read_rate_limit_per_minute,
)

public_write_rate_limit = rate_limit(
    scope="public_write",
    limit_per_minute=lambda settings: settings.public_write_rate_limit_per_minute,
)

external_api_rate_limit = rate_limit(
    scope="external_api",
    limit_per_minute=lambda settings: settings.external_api_rate_limit_per_minute,
)