from pydantic import BaseModel


class AnalyticsMetricResponse(BaseModel):
    label: str
    value: int | float
    helper: str | None = None


class AnalyticsBreakdownItem(BaseModel):
    key: str
    count: int


class AnalyticsTrendPoint(BaseModel):
    date: str
    count: int


class AnalyticsOverviewResponse(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    waiting_tickets: int
    resolved_tickets: int
    closed_tickets: int

    urgent_tickets: int
    sla_ok_tickets: int
    sla_near_breach_tickets: int
    sla_breached_tickets: int

    agent_runs_total: int
    agent_runs_completed: int
    agent_runs_failed: int

    tool_executions_total: int
    tool_executions_success: int
    tool_executions_failed: int
    tool_executions_blocked: int

    approvals_total: int
    approvals_pending: int
    approvals_approved: int
    approvals_rejected: int

    replies_total: int
    replies_sent: int

    audit_events_total: int

    avg_first_response_minutes: float | None
    avg_resolution_minutes: float | None

    tickets_by_status: list[AnalyticsBreakdownItem]
    tickets_by_priority: list[AnalyticsBreakdownItem]
    tickets_by_category: list[AnalyticsBreakdownItem]
    tickets_by_source: list[AnalyticsBreakdownItem]
    tickets_by_sla_status: list[AnalyticsBreakdownItem]

    recent_ticket_trend: list[AnalyticsTrendPoint]