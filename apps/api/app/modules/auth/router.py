from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.auth.dependencies import get_or_create_current_user
from app.modules.auth.schemas import AuthenticatedUserResponse, SyncUserRequest
from app.modules.organizations.models import OrganizationMember
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/sync-user", response_model=AuthenticatedUserResponse)
def sync_user(
    payload: SyncUserRequest,
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    current_user.email = payload.email
    current_user.name = payload.name
    current_user.avatar_url = payload.avatar_url

    db.commit()
    db.refresh(current_user)

    return AuthenticatedUserResponse(
        id=str(current_user.id),
        clerk_user_id=current_user.clerk_user_id,
        email=current_user.email,
        name=current_user.name,
    )


@router.get("/me")
def get_me(
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    memberships = db.scalars(
        select(OrganizationMember).where(OrganizationMember.user_id == current_user.id)
    ).all()

    return {
        "id": str(current_user.id),
        "clerk_user_id": current_user.clerk_user_id,
        "email": current_user.email,
        "name": current_user.name,
        "memberships": [
            {
                "id": str(membership.id),
                "organization_id": str(membership.organization_id),
                "role": membership.role,
                "status": membership.status,
            }
            for membership in memberships
        ],
    }