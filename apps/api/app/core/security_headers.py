from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response


async def security_headers_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=()",
    )

    if request.url.path.startswith(
        (
            "/auth",
            "/organizations",
            "/tickets",
            "/agent",
            "/tools",
            "/approvals",
            "/replies",
            "/analytics",
            "/audit-logs",
            "/integrations",
            "/knowledge",
        )
    ):
        response.headers.setdefault(
            "Cache-Control",
            "no-store, no-cache, must-revalidate, max-age=0",
        )
        response.headers.setdefault("Pragma", "no-cache")

    return response