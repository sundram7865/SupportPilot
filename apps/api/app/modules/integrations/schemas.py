from datetime import datetime
from pydantic import BaseModel, Field


class UpsertUrbanKartIntegrationRequest(BaseModel):
    base_url: str = Field(min_length=5, max_length=500)
    api_key: str = Field(min_length=3, max_length=500)


class UrbanKartIntegrationResponse(BaseModel):
    id: str
    organization_id: str
    provider: str
    base_url: str
    status: str
    last_health_status: str | None
    last_health_message: str | None
    last_checked_at: datetime | None


class UrbanKartHealthCheckResponse(BaseModel):
    connected: bool
    status_code: int | None = None
    message: str
    provider_response: dict | None = None


class ExternalApiLogResponse(BaseModel):
    id: str
    provider: str
    method: str
    endpoint: str
    status: str
    status_code: int | None
    duration_ms: int | None
    error_message: str | None
    created_at: datetime