from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums import MemberStatus, OrganizationRole
from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_organization,
    get_or_create_current_user,
    require_permission,
)
from app.modules.auth.permissions import Permission
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.organizations.schemas import (
    CreateOrganizationRequest,
    InviteMemberRequest,
    OrganizationMemberResponse,
    OrganizationResponse,
    UpdateMemberRoleRequest,
    UpdateOrganizationRequest,
)
from app.modules.users.models import User

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def to_organization_response(organization: Organization) -> OrganizationResponse:
    return OrganizationResponse(
        id=str(organization.id),
        name=organization.name,
        slug=organization.slug,
        support_email=organization.support_email,
        plan=organization.plan,
    )


def make_unique_slug(db: Session, name: str) -> str:
    base_slug = slugify(name)
    slug = base_slug
    counter = 1

    while db.scalar(select(Organization).where(Organization.slug == slug)):
        counter += 1
        slug = f"{base_slug}-{counter}"

    return slug


@router.post("", response_model=OrganizationResponse)
def create_organization(
    payload: CreateOrganizationRequest,
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    organization = Organization(
        name=payload.name,
        slug=make_unique_slug(db, payload.name),
        support_email=str(payload.support_email) if payload.support_email else None,
        plan="FREE",
    )

    db.add(organization)
    db.flush()

    membership = OrganizationMember(
        organization_id=organization.id,
        user_id=current_user.id,
        role=OrganizationRole.OWNER.value,
        status=MemberStatus.ACTIVE.value,
    )

    db.add(membership)
    db.commit()
    db.refresh(organization)

    return to_organization_response(organization)


@router.get("/current", response_model=OrganizationResponse)
def get_current_org(
    organization: Organization = Depends(get_current_organization),
):
    return to_organization_response(organization)


@router.patch(
    "/current",
    response_model=OrganizationResponse,
    dependencies=[Depends(require_permission(Permission.ORGANIZATION_UPDATE))],
)
def update_current_org(
    payload: UpdateOrganizationRequest,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    if payload.name is not None:
        organization.name = payload.name

    if payload.support_email is not None:
        organization.support_email = str(payload.support_email)

    db.commit()
    db.refresh(organization)

    return to_organization_response(organization)


@router.get(
    "/members",
    response_model=list[OrganizationMemberResponse],
    dependencies=[Depends(require_permission(Permission.TEAM_READ))],
)
def list_members(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(OrganizationMember, User)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == organization.id)
    ).all()

    return [
        OrganizationMemberResponse(
            id=str(member.id),
            user_id=str(user.id),
            email=user.email,
            name=user.name,
            role=member.role,
            status=member.status,
        )
        for member, user in rows
    ]


@router.post(
    "/invite",
    response_model=OrganizationMemberResponse,
    dependencies=[Depends(require_permission(Permission.TEAM_INVITE))],
)
def invite_member(
    payload: InviteMemberRequest,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == str(payload.email)))

    if not user:
        user = User(
            email=str(payload.email),
            name=payload.name,
        )
        db.add(user)
        db.flush()

    existing_membership = db.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.organization_id == organization.id)
        .where(OrganizationMember.user_id == user.id)
    )

    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization.",
        )

    membership = OrganizationMember(
        organization_id=organization.id,
        user_id=user.id,
        role=payload.role.value,
        status=MemberStatus.INVITED.value,
    )

    db.add(membership)
    db.commit()
    db.refresh(membership)

    return OrganizationMemberResponse(
        id=str(membership.id),
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        role=membership.role,
        status=membership.status,
    )


@router.patch(
    "/members/{member_id}/role",
    response_model=OrganizationMemberResponse,
    dependencies=[Depends(require_permission(Permission.TEAM_UPDATE))],
)
def update_member_role(
    member_id: UUID,
    payload: UpdateMemberRoleRequest,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    member = db.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.id == member_id)
        .where(OrganizationMember.organization_id == organization.id)
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found.",
        )

    if member.role == OrganizationRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner role cannot be changed.",
        )

    member.role = payload.role.value

    db.commit()
    db.refresh(member)

    user = db.get(User, member.user_id)

    return OrganizationMemberResponse(
        id=str(member.id),
        user_id=str(user.id),
        email=user.email,
        name=user.name,
        role=member.role,
        status=member.status,
    )


@router.delete(
    "/members/{member_id}",
    dependencies=[Depends(require_permission(Permission.TEAM_REMOVE))],
)
def remove_member(
    member_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    member = db.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.id == member_id)
        .where(OrganizationMember.organization_id == organization.id)
    )

    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found.",
        )

    if member.role == OrganizationRole.OWNER.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner cannot be removed.",
        )

    db.delete(member)
    db.commit()

    return {
        "success": True,
        "message": "Member removed successfully.",
    }