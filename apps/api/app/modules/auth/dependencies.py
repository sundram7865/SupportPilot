from typing import Callable
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.permissions import Permission, role_has_permission
from app.modules.auth.security import AuthContext, get_auth_context_from_request
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.users.models import User


def get_or_create_current_user(
    auth_context: AuthContext = Depends(get_auth_context_from_request),
    db: Session = Depends(get_db),
) -> User:
    user = None

    if auth_context.clerk_user_id:
        user = db.scalar(
            select(User).where(User.clerk_user_id == auth_context.clerk_user_id)
        )

    if not user and auth_context.email:
        user = db.scalar(select(User).where(User.email == auth_context.email))

    if user:
        updated = False

        if auth_context.clerk_user_id and user.clerk_user_id != auth_context.clerk_user_id:
            user.clerk_user_id = auth_context.clerk_user_id
            updated = True

        if auth_context.name and user.name != auth_context.name:
            user.name = auth_context.name
            updated = True

        if updated:
            db.commit()
            db.refresh(user)

        return user

    email = auth_context.email or f"{auth_context.clerk_user_id}@dev.local"

    user = User(
        clerk_user_id=auth_context.clerk_user_id,
        email=email,
        name=auth_context.name,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_current_membership(
    x_organization_id: str | None = Header(default=None),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
) -> OrganizationMember:
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
        .where(OrganizationMember.user_id == current_user.id)
        .where(OrganizationMember.organization_id == organization_id)
        .where(OrganizationMember.status == "ACTIVE")
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this organization.",
        )

    return membership

def get_current_organization(
    membership: OrganizationMember = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> Organization:
    organization = db.get(Organization, membership.organization_id)

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found.",
        )

    return organization


def require_permission(permission: Permission) -> Callable:
    def dependency(
        membership: OrganizationMember = Depends(get_current_membership),
    ) -> OrganizationMember:
        if not role_has_permission(membership.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission.value}",
            )

        return membership

    return dependency