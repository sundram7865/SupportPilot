from pydantic import BaseModel, EmailStr


class AuthSyncRequest(BaseModel):
    clerk_user_id: str
    email: EmailStr
    name: str | None = None
    avatar_url: str | None = None

class AuthenticatedUserResponse(BaseModel):
    id: str
    clerk_user_id: str | None
    email: str
    name: str | None