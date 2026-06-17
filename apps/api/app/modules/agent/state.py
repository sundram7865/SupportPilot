from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    organization_id: str
    ticket_id: str
    agent_run_id: str
    user_id: str | None

    ticket: dict[str, Any]
    messages: list[dict[str, Any]]
    internal_notes: list[dict[str, Any]]
    knowledge_context: list[dict[str, Any]]

    detected_category: str
    detected_priority: str
    risk_level: str
    risk_reasons: list[str]

    planned_tools: list[dict[str, Any]]

    draft_response: str
    reasoning_summary: str
    decision: str

    error_message: str | None