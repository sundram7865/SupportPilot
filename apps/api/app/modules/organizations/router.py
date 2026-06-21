from uuid import UUID, uuid4
from sqlalchemy import func, select
from fastapi import APIRouter, Depends, HTTPException, status
from slugify import slugify
from sqlalchemy.orm import Session

from app.common.enums import MemberStatus, OrganizationRole
from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_membership,
    get_current_organization,
    get_or_create_current_user,
    require_permission,
)
from app.modules.auth.permissions import Permission
from app.modules.organizations.models import Organization, OrganizationMember,OrganizationInvitation
from app.modules.organizations.schemas import (
    CreateOrganizationRequest,
    InviteMemberRequest,
    OrganizationMemberResponse,
    OrganizationResponse,
    UpdateMemberRoleRequest,
    UpdateOrganizationRequest,
    InviteMemberResultResponse,
)
from app.modules.users.models import User

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def enum_value(value):
    if hasattr(value, "value"):
        return value.value
    return value

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
    response_model=InviteMemberResultResponse,
    dependencies=[Depends(require_permission(Permission.TEAM_INVITE))],
)
def invite_member(
    payload: InviteMemberRequest,
    current_membership: OrganizationMember = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    email = payload.email.strip().lower()

    organization_id = current_membership.organization_id
    invited_by_user_id = current_membership.user_id

    existing_user = db.scalar(
        select(User).where(func.lower(User.email) == email)
    )

    # Case 1: User already signed up.
    # Directly add ACTIVE membership.
    if existing_user:
        existing_membership = db.scalar(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == organization_id)
            .where(OrganizationMember.user_id == existing_user.id)
        )

        if existing_membership:
            return {
                "type": "membership",
                "created": False,
                "message": "User is already a member of this organization.",
                "membership": {
                    "id": str(existing_membership.id),
                    "organization_id": str(existing_membership.organization_id),
                    "user_id": str(existing_membership.user_id),
                    "role": enum_value(existing_membership.role),
                    "status": enum_value(existing_membership.status),
                },
                "invitation": None,
            }

        membership = OrganizationMember(
            id=uuid4(),
            organization_id=organization_id,
            user_id=existing_user.id,
            role=payload.role,
            status="ACTIVE",
        )

        db.add(membership)
        db.commit()
        db.refresh(membership)

        return {
            "type": "membership",
            "created": True,
            "message": "Existing user added to organization.",
            "membership": {
                "id": str(membership.id),
                "organization_id": str(membership.organization_id),
                "user_id": str(membership.user_id),
                "role": enum_value(membership.role),
                "status": enum_value(membership.status),
            },
            "invitation": None,
        }

    # Case 2: User has not signed up yet.
    # Store only a pending invitation, not a fake user.
    existing_pending_invitation = db.scalar(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.organization_id == organization_id)
        .where(func.lower(OrganizationInvitation.email) == email)
        .where(OrganizationInvitation.status == "PENDING")
    )

    if existing_pending_invitation:
        return {
            "type": "invitation",
            "created": False,
            "message": "Invitation is already pending for this email.",
            "membership": None,
            "invitation": {
                "id": str(existing_pending_invitation.id),
                "organization_id": str(existing_pending_invitation.organization_id),
                "email": existing_pending_invitation.email,
                "name": existing_pending_invitation.name,
                "role": enum_value(existing_pending_invitation.role),
                "status": enum_value(existing_pending_invitation.status),
            },
        }

    invitation = OrganizationInvitation(
        id=uuid4(),
        organization_id=organization_id,
        email=email,
        name=payload.name,
        role=payload.role,
        status="PENDING",
        invited_by_user_id=invited_by_user_id,
    )

    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return {
        "type": "invitation",
        "created": True,
        "message": "Invitation created. User will be added when they sign up.",
        "membership": None,
        "invitation": {
            "id": str(invitation.id),
            "organization_id": str(invitation.organization_id),
            "email": invitation.email,
            "name": invitation.name,
            "role": enum_value(invitation.role),
            "status": enum_value(invitation.status),
        },
    }


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

@router.get("/invitations")
def list_organization_invitations(
    current_membership: OrganizationMember = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    invitations = db.scalars(
        select(OrganizationInvitation)
        .where(OrganizationInvitation.organization_id == current_membership.organization_id)
        .order_by(OrganizationInvitation.created_at.desc())
    ).all()

    return [
        {
            "id": str(invitation.id),
            "organization_id": str(invitation.organization_id),
            "email": invitation.email,
            "name": invitation.name,
            "role": invitation.role,
            "status": invitation.status,
            "invited_by_user_id": str(invitation.invited_by_user_id)
            if invitation.invited_by_user_id
            else None,
            "accepted_by_user_id": str(invitation.accepted_by_user_id)
            if invitation.accepted_by_user_id
            else None,
            "accepted_at": invitation.accepted_at.isoformat()
            if invitation.accepted_at
            else None,
            "created_at": invitation.created_at.isoformat()
            if invitation.created_at
            else None,
        }
        for invitation in invitations
    ]

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