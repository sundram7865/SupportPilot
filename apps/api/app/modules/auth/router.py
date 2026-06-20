from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.clerk import verify_clerk_token
from app.modules.auth.dependencies import get_or_create_current_user
from app.modules.auth.schemas import AuthSyncRequest
from app.modules.organizations.models import (
    Organization,
    OrganizationInvitation,
    OrganizationMember,
)
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


def enum_value(value):
    if hasattr(value, "value"):
        return value.value
    return value


def normalize_email(email: str) -> str:
    return email.strip().lower()


def serialize_user(user: User) -> dict:
    return {
        "id": str(user.id),
        "clerk_user_id": user.clerk_user_id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
    }


def serialize_membership(db: Session, membership: OrganizationMember) -> dict:
    organization = db.scalar(
        select(Organization).where(Organization.id == membership.organization_id)
    )

    return {
        "organization_id": str(membership.organization_id),
        "role": enum_value(membership.role),
        "status": enum_value(membership.status),
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "slug": organization.slug,
        }
        if organization
        else None,
    }


def get_auth_payload_from_header(authorization: str | None) -> dict:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required.",
        )

    parts = authorization.split(" ", 1)

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be Bearer token.",
        )

    return verify_clerk_token(parts[1])


def activate_pending_memberships(db: Session, user: User) -> None:
    memberships = db.scalars(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    ).all()

    for membership in memberships:
        if enum_value(membership.status) == "INVITED":
            membership.status = "ACTIVE"


def accept_pending_invitations(db: Session, user: User) -> None:
    email = normalize_email(user.email)

    pending_invitations = db.scalars(
        select(OrganizationInvitation)
        .where(func.lower(OrganizationInvitation.email) == email)
        .where(OrganizationInvitation.status == "PENDING")
    ).all()

    for invitation in pending_invitations:
        existing_membership = db.scalar(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == invitation.organization_id)
            .where(OrganizationMember.user_id == user.id)
        )

        if not existing_membership:
            membership = OrganizationMember(
                id=uuid4(),
                organization_id=invitation.organization_id,
                user_id=user.id,
                role=invitation.role,
                status="ACTIVE",
            )

            db.add(membership)

        elif enum_value(existing_membership.status) == "INVITED":
            existing_membership.status = "ACTIVE"

        invitation.status = "ACCEPTED"
        invitation.accepted_by_user_id = user.id
        invitation.accepted_at = datetime.now(timezone.utc)


def merge_duplicate_clerk_user_into_target(
    db: Session,
    duplicate_user: User,
    target_user: User,
) -> None:
    duplicate_memberships = db.scalars(
        select(OrganizationMember).where(
            OrganizationMember.user_id == duplicate_user.id
        )
    ).all()

    for duplicate_membership in duplicate_memberships:
        existing_target_membership = db.scalar(
            select(OrganizationMember)
            .where(
                OrganizationMember.organization_id
                == duplicate_membership.organization_id
            )
            .where(OrganizationMember.user_id == target_user.id)
        )

        if existing_target_membership:
            if enum_value(existing_target_membership.status) == "INVITED":
                existing_target_membership.status = "ACTIVE"

            db.delete(duplicate_membership)
        else:
            duplicate_membership.user_id = target_user.id

            if enum_value(duplicate_membership.status) == "INVITED":
                duplicate_membership.status = "ACTIVE"

    duplicate_user.clerk_user_id = None
    duplicate_user.email = f"merged-{duplicate_user.id}@clerk.local"
    duplicate_user.name = duplicate_user.name or "Merged Clerk User"


@router.post("/sync")
def sync_auth_user(
    payload: AuthSyncRequest,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    token_payload = get_auth_payload_from_header(authorization)

    token_clerk_user_id = token_payload.get("sub")

    if not token_clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Clerk token: missing subject.",
        )

    if token_clerk_user_id != payload.clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk token does not match sync payload.",
        )

    email = normalize_email(payload.email)

    existing_by_clerk = db.scalar(
        select(User).where(User.clerk_user_id == payload.clerk_user_id)
    )

    existing_by_email = db.scalar(
        select(User).where(func.lower(User.email) == email)
    )

    if existing_by_clerk and existing_by_email and existing_by_clerk.id != existing_by_email.id:
        merge_duplicate_clerk_user_into_target(
            db=db,
            duplicate_user=existing_by_clerk,
            target_user=existing_by_email,
        )

        existing_by_email.clerk_user_id = payload.clerk_user_id
        existing_by_email.email = email
        existing_by_email.name = payload.name or existing_by_email.name
        existing_by_email.avatar_url = payload.avatar_url or existing_by_email.avatar_url

        activate_pending_memberships(db, existing_by_email)
        accept_pending_invitations(db, existing_by_email)

        db.commit()
        db.refresh(existing_by_email)

        return {
            "user": serialize_user(existing_by_email),
            "merged": True,
            "linked_by": "email",
        }

    if existing_by_clerk:
        existing_by_clerk.email = email
        existing_by_clerk.name = payload.name or existing_by_clerk.name
        existing_by_clerk.avatar_url = payload.avatar_url or existing_by_clerk.avatar_url

        activate_pending_memberships(db, existing_by_clerk)
        accept_pending_invitations(db, existing_by_clerk)

        db.commit()
        db.refresh(existing_by_clerk)

        return {
            "user": serialize_user(existing_by_clerk),
            "merged": False,
            "linked_by": "clerk_user_id",
        }

    if existing_by_email:
        existing_by_email.clerk_user_id = payload.clerk_user_id
        existing_by_email.email = email
        existing_by_email.name = payload.name or existing_by_email.name
        existing_by_email.avatar_url = payload.avatar_url or existing_by_email.avatar_url

        activate_pending_memberships(db, existing_by_email)
        accept_pending_invitations(db, existing_by_email)

        db.commit()
        db.refresh(existing_by_email)

        return {
            "user": serialize_user(existing_by_email),
            "merged": False,
            "linked_by": "email",
        }

    user = User(
        id=uuid4(),
        clerk_user_id=payload.clerk_user_id,
        email=email,
        name=payload.name,
        avatar_url=payload.avatar_url,
    )

    db.add(user)
    db.flush()

    accept_pending_invitations(db, user)

    db.commit()
    db.refresh(user)

    return {
        "user": serialize_user(user),
        "merged": False,
        "linked_by": "new_user",
    }


@router.get("/me")
def get_me(
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    memberships = db.scalars(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    ).all()

    serialized_memberships = [
        serialize_membership(db, membership) for membership in memberships
    ]

    organizations = [
        membership["organization"]
        for membership in serialized_memberships
        if membership.get("organization")
    ]

    return {
        "user": serialize_user(current_user),
        "memberships": serialized_memberships,
        "organizations": organizations,
    }


@router.post("/bootstrap-org")
def bootstrap_org(
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    existing_membership = db.scalar(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    )

    if existing_membership:
        return {
            "created": False,
            "organization_id": str(existing_membership.organization_id),
        }

    org = Organization(
        id=uuid4(),
        name="UrbanKart Demo",
        slug=f"urbankart-{str(current_user.id)[:8]}",
    )

    membership = OrganizationMember(
        id=uuid4(),
        organization_id=org.id,
        user_id=current_user.id,
        role="OWNER",
        status="ACTIVE",
    )

    db.add(org)
    db.add(membership)
    db.commit()
    db.refresh(org)

    return {
        "created": True,
        "organization_id": str(org.id),
    }