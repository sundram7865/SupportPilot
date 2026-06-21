from pydantic import BaseModel, EmailStr, Field

from app.common.enums import OrganizationRole


class CreateOrganizationRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    support_email: EmailStr | None = None


class UpdateOrganizationRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    support_email: EmailStr | None = None


class InviteMemberRequest(BaseModel):
    email: EmailStr
    name: str | None = None
    role: OrganizationRole = OrganizationRole.SUPPORT_AGENT


class UpdateMemberRoleRequest(BaseModel):
    role: OrganizationRole


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    support_email: str | None
    plan: str


class OrganizationMemberResponse(BaseModel):
    id: str
    user_id: str
    email: str
    name: str | None
    role: str
    status: str
    
    
class OrganizationInvitationResponse(BaseModel):
    id: str
    organization_id: str
    email: str
    name: str | None = None
    role: str
    status: str


class OrganizationMembershipInviteResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    role: str
    status: str


class InviteMemberResultResponse(BaseModel):
    type: str
    created: bool
    message: str
    membership: OrganizationMembershipInviteResponse | None = None
    invitation: OrganizationInvitationResponse | None = None