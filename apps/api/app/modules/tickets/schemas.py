from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.common.enums import (
    TicketCategory,
    TicketMessageSenderType,
    TicketPriority,
    TicketSource,
    TicketStatus,
    TicketTransitionTrigger,
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
    status_reason: str | None = Field(default=None, max_length=2000)

    priority: TicketPriority | None = None
    category: TicketCategory | None = None

    assigned_to_user_id: UUID | None = None

    customer_name: str | None = Field(default=None, max_length=255)
    customer_email: EmailStr | None = None
    customer_phone: str | None = Field(default=None, max_length=50)
    external_order_id: str | None = Field(default=None, max_length=100)


class TransitionTicketStatusRequest(BaseModel):
    to_status: TicketStatus
    reason: str | None = Field(default=None, max_length=2000)
    trigger: TicketTransitionTrigger = TicketTransitionTrigger.AGENT_ACTION
    metadata_json: dict | None = None


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


class TicketStatusTransitionResponse(BaseModel):
    id: str
    actor_user_id: str | None
    from_status: str
    to_status: str
    trigger: str
    reason: str | None
    is_allowed: bool
    blocked_reason: str | None
    created_at: datetime


class TicketLifecycleRulesResponse(BaseModel):
    transitions: dict[str, list[str]]
    terminal_statuses: list[str]
    reopen_allowed_from: list[str]


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
    sla_status: str | None = None
    first_response_due_at: datetime | None = None
    resolution_due_at: datetime | None = None


class TicketDetailResponse(BaseModel):
    id: str
    organization_id: str
    ticket_number: str
    subject: str
    description: str
    status: str
    status_changed_at: datetime | None
    status_changed_by_user_id: str | None
    status_reason: str | None

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
    first_response_due_at: datetime | None
    resolution_due_at: datetime | None
    sla_status: str
    sla_near_breach_notified_at: datetime | None
    sla_breached_at: datetime | None
    ai_summary: str | None
    ai_confidence_score: int | None

    created_at: datetime
    updated_at: datetime

    messages: list[TicketMessageResponse]
    internal_notes: list[TicketInternalNoteResponse]
    timeline_events: list[TicketTimelineEventResponse]
    status_transitions: list[TicketStatusTransitionResponse]


class TicketListResponse(BaseModel):
    items: list[TicketListItemResponse]
    total: int
    limit: int
    offset: int