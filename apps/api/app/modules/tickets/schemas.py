from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.common.enums import (
    TicketCategory,
    TicketMessageSenderType,
    TicketPriority,
    TicketSource,
    TicketStatus,
)


class CreateTicketRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=3)

    customer_name: str | None = Field(default=None, max_length=255)
    customer_email: EmailStr
    customer_phone: str | None = Field(default=None, max_length=50)

    external_order_id: str | None = Field(default=None, max_length=100)

    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.OTHER
    source: TicketSource = TicketSource.SUPPORT_FORM

    metadata_json: dict | None = None


class UpdateTicketRequest(BaseModel):
    subject: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=3)

    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category: TicketCategory | None = None

    assigned_to_user_id: UUID | None = None

    customer_name: str | None = Field(default=None, max_length=255)
    customer_email: EmailStr | None = None
    customer_phone: str | None = Field(default=None, max_length=50)
    external_order_id: str | None = Field(default=None, max_length=100)


class AddTicketMessageRequest(BaseModel):
    body: str = Field(min_length=1)
    sender_type: TicketMessageSenderType = TicketMessageSenderType.AGENT
    sender_name: str | None = Field(default=None, max_length=255)
    sender_email: EmailStr | None = None
    metadata_json: dict | None = None


class AddInternalNoteRequest(BaseModel):
    body: str = Field(min_length=1)
    metadata_json: dict | None = None


class TicketMessageResponse(BaseModel):
    id: str
    sender_type: str
    sender_user_id: str | None
    sender_name: str | None
    sender_email: str | None
    body: str
    is_public: bool
    created_at: datetime


class TicketInternalNoteResponse(BaseModel):
    id: str
    author_user_id: str | None
    body: str
    created_at: datetime


class TicketTimelineEventResponse(BaseModel):
    id: str
    actor_user_id: str | None
    event_type: str
    title: str
    description: str | None
    old_value: str | None
    new_value: str | None
    created_at: datetime


class TicketListItemResponse(BaseModel):
    id: str
    ticket_number: str
    subject: str
    status: str
    priority: str
    category: str
    source: str
    customer_name: str | None
    customer_email: str
    external_order_id: str | None
    assigned_to_user_id: str | None
    created_at: datetime
    updated_at: datetime


class TicketDetailResponse(BaseModel):
    id: str
    organization_id: str
    ticket_number: str
    subject: str
    description: str
    status: str
    priority: str
    category: str
    source: str

    customer_name: str | None
    customer_email: str
    customer_phone: str | None
    external_order_id: str | None

    assigned_to_user_id: str | None
    created_by_user_id: str | None

    first_response_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None

    ai_summary: str | None
    ai_confidence_score: int | None

    created_at: datetime
    updated_at: datetime

    messages: list[TicketMessageResponse]
    internal_notes: list[TicketInternalNoteResponse]
    timeline_events: list[TicketTimelineEventResponse]


class TicketListResponse(BaseModel):
    items: list[TicketListItemResponse]
    total: int
    limit: int
    offset: int