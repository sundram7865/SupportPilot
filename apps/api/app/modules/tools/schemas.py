from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.common.enums import ToolName


class ExecuteToolRequest(BaseModel):
    tool_name: ToolName
    ticket_id: UUID | None = None
    agent_run_id: UUID | None = None
    args: dict = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, max_length=255)


class ExecuteAgentRunToolsRequest(BaseModel):
    execute_read_only_only: bool = True


class ToolExecutionResponse(BaseModel):
    id: str
    organization_id: str
    ticket_id: str | None
    agent_run_id: str | None
    requested_by_user_id: str | None
    tool_name: str
    risk_level: str
    status: str
    approval_status: str
    idempotency_key: str | None
    input_args: dict | None
    output_json: dict | None
    error_message: str | None
    duration_ms: int | None
    created_at: datetime
    completed_at: datetime | None


class ToolExecutionListResponse(BaseModel):
    items: list[ToolExecutionResponse]
    total: int


class AgentRunToolExecutionResponse(BaseModel):
    agent_run_id: str
    executions: list[ToolExecutionResponse]