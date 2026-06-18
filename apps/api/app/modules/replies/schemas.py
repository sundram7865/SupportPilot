from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.common.enums import CustomerReplyDraftSource


class CreateReplyDraftRequest(BaseModel):
    ticket_id: UUID
    subject: str | None = Field(default=None, max_length=255)
    body: str = Field(min_length=1, max_length=10000)
    source: CustomerReplyDraftSource = CustomerReplyDraftSource.AGENT
    metadata_json: dict | None = None


class UpdateReplyDraftRequest(BaseModel):
    subject: str | None = Field(default=None, max_length=255)
    body: str | None = Field(default=None, min_length=1, max_length=10000)
    metadata_json: dict | None = None


class SubmitReplyDraftApprovalRequest(BaseModel):
    request_reason: str | None = Field(default=None, max_length=2000)


class DecideReplyDraftRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)


class SendReplyDraftRequest(BaseModel):
    send_notes: str | None = Field(default=None, max_length=2000)


class ReplyDraftResponse(BaseModel):
    id: str
    organization_id: str
    ticket_id: str
    agent_run_id: str | None
    approval_request_id: str | None

    created_by_user_id: str | None
    updated_by_user_id: str | None
    approved_by_user_id: str | None
    rejected_by_user_id: str | None
    sent_by_user_id: str | None
    sent_message_id: str | None

    source: str
    status: str
    subject: str | None
    body: str
    rejection_reason: str | None
    approval_reason: str | None
    send_notes: str | None
    metadata_json: dict | None

    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None
    rejected_at: datetime | None
    sent_at: datetime | None


class ReplyDraftListResponse(BaseModel):
    items: list[ReplyDraftResponse]
    total: int