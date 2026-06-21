from functools import lru_cache

import httpx
import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError,PyJWTError


from app.core.config import get_settings


@lru_cache()
def get_jwks_client() -> PyJWKClient:
    settings = get_settings()

    if not settings.clerk_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_JWKS_URL is not configured.",
        )

    return PyJWKClient(settings.clerk_jwks_url)


from functools import lru_cache



from app.core.config import get_settings


@lru_cache()
def get_jwks_client() -> PyJWKClient:
    settings = get_settings()

    if not settings.clerk_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_JWKS_URL is not configured.",
        )

    return PyJWKClient(settings.clerk_jwks_url)


def verify_clerk_token(token: str) -> dict:
    settings = get_settings()

    if not settings.clerk_issuer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_ISSUER is not configured.",
        )

    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={
                "verify_aud": False,
            },
            leeway=60,
        )

    except HTTPException:
        raise

    except (InvalidTokenError, PyJWTError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Clerk token: {str(exc)}",
        )

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Clerk token verification failed: {str(exc)}",
        )

async def fetch_clerk_user_email(clerk_user_id: str, token: str) -> str | None:
    settings = get_settings()

    if not settings.clerk_issuer:
        return None

    base_url = settings.clerk_issuer.rstrip("/")
    url = f"{base_url}/v1/users/{clerk_user_id}"

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                },
            )

        if not response.is_success:
            return None

        data = response.json()
        emails = data.get("email_addresses") or []
        primary_id = data.get("primary_email_address_id")

        for email in emails:
            if email.get("id") == primary_id:
                return email.get("email_address")

        if emails:
            return emails[0].get("email_address")

    except Exception:
        return None

    return None