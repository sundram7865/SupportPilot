from datetime import datetime

from pydantic import BaseModel, Field


class RunTicketAgentRequest(BaseModel):
    force: bool = False
    notes: str | None = Field(default=None, max_length=2000)


class AgentRunStepResponse(BaseModel):
    id: str
    step_name: str
    status: str
    input_json: dict | None
    output_json: dict | None
    error_message: str | None
    duration_ms: int | None
    created_at: datetime
    completed_at: datetime | None


class AgentRunResponse(BaseModel):
    id: str
    organization_id: str
    ticket_id: str
    started_by_user_id: str | None
    status: str
    provider: str
    model_name: str | None
    detected_category: str | None
    detected_priority: str | None
    risk_level: str
    decision: str
    draft_response: str | None
    reasoning_summary: str | None
    planned_tools: list | None
    retrieved_context: list | None
    final_state: dict | None
    error_message: str | None
    duration_ms: int | None
    created_at: datetime
    completed_at: datetime | None
    steps: list[AgentRunStepResponse]


class AgentRunListItemResponse(BaseModel):
    id: str
    ticket_id: str
    status: str
    risk_level: str
    decision: str
    detected_category: str | None
    detected_priority: str | None
    duration_ms: int | None
    created_at: datetime
    completed_at: datetime | None


class AgentRunListResponse(BaseModel):
    items: list[AgentRunListItemResponse]
    total: int