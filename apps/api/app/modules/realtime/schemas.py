from pydantic import BaseModel, Field


class DevPingRequest(BaseModel):
    message: str = Field(default="hello from SupportPilot realtime")