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