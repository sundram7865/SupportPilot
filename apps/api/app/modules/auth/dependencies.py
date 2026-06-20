from uuid import UUID, uuid4

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.modules.auth.permissions import ROLE_PERMISSIONS, Permission
from app.modules.auth.clerk import verify_clerk_token
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.users.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def normalize_status(value) -> str:
    if hasattr(value, "value"):
        return value.value
    return str(value)


def get_or_create_user(
    db: Session,
    external_user_id: str,
    email: str,
    name: str | None = None,
    avatar_url: str | None = None,
) -> User:
    user = db.scalar(
        select(User).where(User.clerk_user_id == external_user_id)
    )

    if user:
        user.email = email
        user.name = name or user.name
        user.avatar_url = avatar_url or user.avatar_url
        db.commit()
        db.refresh(user)
        return user

    existing_email_user = db.scalar(select(User).where(User.email == email))

    if existing_email_user:
        existing_email_user.clerk_user_id = external_user_id
        existing_email_user.name = name or existing_email_user.name
        existing_email_user.avatar_url = avatar_url or existing_email_user.avatar_url
        db.commit()
        db.refresh(existing_email_user)
        return existing_email_user

    user = User(
        id=uuid4(),
        clerk_user_id=external_user_id,
        email=email,
        name=name,
        avatar_url=avatar_url,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def extract_email_from_claims(payload: dict) -> str:
    email = payload.get("email")

    if email:
        return email

    claims = payload.get("claims") or {}
    email = claims.get("email")

    if email:
        return email

    sub = payload.get("sub")

    return f"{sub}@clerk.local"


def extract_name_from_claims(payload: dict) -> str | None:
    name = payload.get("name")

    if name:
        return name

    claims = payload.get("claims") or {}
    first_name = claims.get("first_name")
    last_name = claims.get("last_name")

    full_name = " ".join([part for part in [first_name, last_name] if part])

    return full_name or None


def get_or_create_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_dev_user_id: str | None = Header(default=None),
    x_dev_email: str | None = Header(default=None),
    x_dev_name: str | None = Header(default=None),
) -> User:
    settings = get_settings()

    if credentials and credentials.credentials:
        payload = verify_clerk_token(credentials.credentials)

        clerk_user_id = payload.get("sub")

        if not clerk_user_id:
            raise HTTPException(status_code=401, detail="Invalid Clerk token.")

        user = db.scalar(
            select(User).where(User.clerk_user_id == clerk_user_id)
        )

        if user:
            return user

        raise HTTPException(
        status_code=409,
        detail="Auth sync required before accessing this resource.",
        )
    if settings.dev_auth_enabled:
        dev_user_id = x_dev_user_id or "dev-owner-1"
        dev_email = x_dev_email or "owner@urbankart.demo"
        dev_name = x_dev_name or "UrbanKart Owner"

        return get_or_create_user(
            db=db,
            external_user_id=dev_user_id,
            email=dev_email,
            name=dev_name,
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
    )


def get_current_organization(
    x_organization_id: str | None = Header(default=None),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
) -> Organization:
    if not x_organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x-organization-id header is required for organization-scoped routes.",
        )

    try:
        organization_id = UUID(x_organization_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid x-organization-id header.",
        )

    membership = db.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == organization_id)
        .where(OrganizationMember.user_id == current_user.id)
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization.",
        )

    if normalize_status(membership.status) != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization membership is not active.",
        )

    organization = db.scalar(
        select(Organization).where(Organization.id == organization_id)
    )

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    return organization


def get_current_membership(
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
) -> OrganizationMember:
    membership = db.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == organization.id)
        .where(OrganizationMember.user_id == current_user.id)
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization.",
        )

    return membership


def require_permission(permission: Permission):
    def dependency(
        membership: OrganizationMember = Depends(get_current_membership),
    ) -> OrganizationMember:
        role = membership.role

        if hasattr(role, "value"):
            role = role.value

        permissions = ROLE_PERMISSIONS.get(role, set())

        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing required permission.",
            )

        return membership

    return dependency