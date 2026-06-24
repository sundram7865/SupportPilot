from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: UUID
    organization_id: UUID
    actor_user_id: UUID | None

    action: str
    resource_type: str
    resource_id: UUID | None

    ticket_id: UUID | None
    agent_run_id: UUID | None
    tool_execution_id: UUID | None
    approval_request_id: UUID | None
    reply_draft_id: UUID | None

    description: str | None
    metadata_json: dict | None
    ip_address: str | None
    user_agent: str | None

    created_at: datetime

    model_config = {
        "from_attributes": True,
    }


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    limit: int
    offset: int