from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import get_or_create_current_user
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


def serialize_org_membership(membership: OrganizationMember) -> dict:
    organization = membership.organization

    return {
        "organization_id": str(membership.organization_id),
        "role": membership.role.value if hasattr(membership.role, "value") else membership.role,
        "status": membership.status.value
        if hasattr(membership.status, "value")
        else membership.status,
        "organization": {
            "id": str(organization.id),
            "name": organization.name,
            "slug": organization.slug,
        }
        if organization
        else None,
    }


@router.get("/me")
def get_me(
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    memberships = db.scalars(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
    ).all()

    return {
        "user": {
            "id": str(current_user.id),
            "clerk_user_id": current_user.clerk_user_id,
            "email": current_user.email,
            "name": current_user.name,
            "avatar_url": current_user.avatar_url,
        },
        "memberships": [serialize_org_membership(membership) for membership in memberships],
        "organizations": [
            serialize_org_membership(membership)["organization"]
            for membership in memberships
            if serialize_org_membership(membership)["organization"]
        ],
    }


@router.post("/bootstrap-org")
def bootstrap_org(
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    existing_membership = db.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
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