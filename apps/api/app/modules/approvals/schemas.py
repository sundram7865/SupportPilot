from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateApprovalRequestBody(BaseModel):
    request_reason: str | None = Field(default=None, max_length=2000)
    metadata_json: dict | None = None


class DecideApprovalRequestBody(BaseModel):
    decision_reason: str | None = Field(default=None, max_length=2000)


class ApprovalRequestResponse(BaseModel):
    id: str
    organization_id: str
    ticket_id: str | None
    agent_run_id: str | None
    tool_execution_id: str | None
    requested_by_user_id: str | None
    decided_by_user_id: str | None
    request_type: str
    status: str
    title: str
    description: str | None
    risk_level: str
    tool_name: str | None
    input_args: dict | None
    request_reason: str | None
    decision_reason: str | None
    result_json: dict | None
    metadata_json: dict | None
    created_at: datetime
    decided_at: datetime | None


class ApprovalRequestListResponse(BaseModel):
    items: list[ApprovalRequestResponse]
    total: int