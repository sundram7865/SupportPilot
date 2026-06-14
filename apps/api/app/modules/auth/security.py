from dataclasses import dataclass

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient

from app.core.config import get_settings


@dataclass
class AuthContext:
    clerk_user_id: str
    email: str | None = None
    name: str | None = None


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None

    parts = authorization.split(" ")

    if len(parts) != 2:
        return None

    scheme, token = parts

    if scheme.lower() != "bearer":
        return None

    return token


def verify_clerk_token(token: str) -> AuthContext:
    settings = get_settings()

    if not settings.clerk_jwks_url or not settings.clerk_issuer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk JWT verification is not configured.",
        )

    try:
        jwks_client = PyJWKClient(settings.clerk_jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token).key

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"verify_aud": False},
        )

        clerk_user_id = payload.get("sub")

        if not clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing subject.",
            )

        email = (
            payload.get("email")
            or payload.get("email_address")
            or payload.get("primary_email_address")
        )

        name = payload.get("name") or payload.get("full_name")

        return AuthContext(
            clerk_user_id=clerk_user_id,
            email=email,
            name=name,
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(exc)}",
        )


def get_auth_context_from_request(
    authorization: str | None = Header(default=None),
    x_dev_user_id: str | None = Header(default=None),
    x_dev_email: str | None = Header(default=None),
    x_dev_name: str | None = Header(default=None),
) -> AuthContext:
    settings = get_settings()
    token = _extract_bearer_token(authorization)

    if token:
        return verify_clerk_token(token)

    if settings.dev_auth_enabled:
        return AuthContext(
            clerk_user_id=x_dev_user_id or "dev-user-1",
            email=x_dev_email or "owner@urbankart.demo",
            name=x_dev_name or "UrbanKart Owner",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
    )