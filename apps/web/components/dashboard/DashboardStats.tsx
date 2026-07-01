import { Badge } from "@/components/ui/Badge";
import type { AnalyticsBreakdownItem, AnalyticsOverview, Ticket } from "@/types/api";

function formatNumber(value: number | null | undefined) {
  return typeof value === "number" ? value.toLocaleString() : "0";
}

function formatMinutes(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";

  if (value < 60) {
    return `${value.toFixed(value % 1 === 0 ? 0 : 1)}m`;
  }

  const hours = value / 60;
  return `${hours.toFixed(hours % 1 === 0 ? 0 : 1)}h`;
}

function percentage(value: number, total: number) {
  if (!total) return 0;
  return Math.round((value / total) * 100);
}

function fallbackAnalyticsFromTickets(tickets: Ticket[]): AnalyticsOverview {
  const open = tickets.filter((ticket) => ticket.status === "OPEN").length;
  const inProgress = tickets.filter((ticket) => ticket.status === "IN_PROGRESS").length;
  const waiting = tickets.filter((ticket) => ticket.status.includes("WAITING")).length;
  const resolved = tickets.filter((ticket) => ticket.status === "RESOLVED").length;
  const closed = tickets.filter((ticket) => ticket.status === "CLOSED").length;
  const urgent = tickets.filter((ticket) => ticket.priority === "URGENT").length;
  const slaBreached = tickets.filter((ticket) => ticket.sla_status === "BREACHED").length;
  const slaNear = tickets.filter((ticket) => ticket.sla_status === "NEAR_BREACH").length;
  const slaOk = tickets.filter((ticket) => ticket.sla_status === "OK").length;

  function groupBy(key: keyof Ticket): AnalyticsBreakdownItem[] {
    const map = new Map<string, number>();

    tickets.forEach((ticket) => {
      const value = String(ticket[key] || "UNKNOWN");
      map.set(value, (map.get(value) || 0) + 1);
    });

    return Array.from(map.entries()).map(([itemKey, count]) => ({
      key: itemKey,
      count,
    }));
  }

  return {
    total_tickets: tickets.length,
    open_tickets: open,
    in_progress_tickets: inProgress,
    waiting_tickets: waiting,
    resolved_tickets: resolved,
    closed_tickets: closed,
    urgent_tickets: urgent,
    sla_ok_tickets: slaOk,
    sla_near_breach_tickets: slaNear,
    sla_breached_tickets: slaBreached,
    agent_runs_total: 0,
    agent_runs_completed: 0,
    agent_runs_failed: 0,
    tool_executions_total: 0,
    tool_executions_success: 0,
    tool_executions_failed: 0,
    tool_executions_blocked: 0,
    approvals_total: 0,
    approvals_pending: 0,
    approvals_approved: 0,
    approvals_rejected: 0,
    replies_total: 0,
    replies_sent: 0,
    audit_events_total: 0,
    avg_first_response_minutes: null,
    avg_resolution_minutes: null,
    tickets_by_status: groupBy("status"),
    tickets_by_priority: groupBy("priority"),
    tickets_by_category: groupBy("category"),
    tickets_by_source: groupBy("source"),
    tickets_by_sla_status: groupBy("sla_status"),
    recent_ticket_trend: [],
  };
}

function StatCard({
  label,
  value,
  helper,
  tone,
}: {
  label: string;
  value: string | number;
  helper?: string;
  tone?: "green" | "yellow" | "red" | "blue" | "gray";
}) {
  return (
    <div className="stat-card" style={{ minHeight: 112 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div className="muted">{label}</div>
        {tone ? <Badge tone={tone as any}>{tone.toUpperCase()}</Badge> : null}
      </div>

      <div className="stat-value" style={{ marginTop: 10 }}>
        {value}
      </div>

      {helper ? (
        <div className="muted" style={{ marginTop: 6, fontSize: 13 }}>
          {helper}
        </div>
      ) : null}
    </div>
  );
}

function BreakdownCard({
  title,
  items,
  total,
}: {
  title: string;
  items: AnalyticsBreakdownItem[];
  total: number;
}) {
  const visibleItems = items.slice(0, 6);

  return (
    <div className="section">
      <div className="section-title">{title}</div>

      <div style={{ display: "grid", gap: 10 }}>
        {visibleItems.length > 0 ? (
          visibleItems.map((item) => {
            const width = percentage(item.count, total);

            return (
              <div key={item.key}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 12,
                    marginBottom: 6,
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{item.key}</span>
                  <span className="muted">{item.count}</span>
                </div>

                <div
                  style={{
                    height: 8,
                    borderRadius: 999,
                    background: "rgba(148, 163, 184, 0.18)",
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      width: `${width}%`,
                      height: "100%",
                      borderRadius: 999,
                      background:
                        "linear-gradient(90deg, rgba(59,130,246,.95), rgba(16,185,129,.95))",
                    }}
                  />
                </div>
              </div>
            );
          })
        ) : (
          <p className="muted">No data yet.</p>
        )}
      </div>
    </div>
  );
}

function TrendCard({ analytics }: { analytics: AnalyticsOverview }) {
  const max = Math.max(
    1,
    ...analytics.recent_ticket_trend.map((point) => point.count)
  );

  return (
    <div className="section">
      <div className="section-title">7-day Ticket Trend</div>

      <div
        style={{
          display: "flex",
          alignItems: "end",
          gap: 10,
          height: 150,
          paddingTop: 12,
        }}
      >
        {analytics.recent_ticket_trend.length > 0 ? (
          analytics.recent_ticket_trend.map((point) => {
            const height = Math.max(8, Math.round((point.count / max) * 110));

            return (
              <div
                key={point.date}
                style={{
                  display: "grid",
                  gap: 8,
                  justifyItems: "center",
                  flex: 1,
                }}
              >
                <div
                  title={`${point.date}: ${point.count}`}
                  style={{
                    height,
                    width: "100%",
                    maxWidth: 34,
                    borderRadius: 10,
                    background:
                      "linear-gradient(180deg, rgba(59,130,246,.95), rgba(99,102,241,.9))",
                  }}
                />

                <div className="muted" style={{ fontSize: 11 }}>
                  {point.date.slice(5)}
                </div>
              </div>
            );
          })
        ) : (
          <p className="muted">No trend data yet.</p>
        )}
      </div>
    </div>
  );
}

export function DashboardStats({
  tickets,
  analytics,
  loading,
}: {
  tickets: Ticket[];
  analytics?: AnalyticsOverview | null;
  loading?: boolean;
}) {
  const data = analytics || fallbackAnalyticsFromTickets(tickets);
  const total = data.total_tickets;

  const activeTickets =
    data.open_tickets + data.in_progress_tickets + data.waiting_tickets;

  const automationRate = percentage(data.agent_runs_completed, Math.max(1, total));
  const replyRate = percentage(data.replies_sent, Math.max(1, data.replies_total));

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {loading ? (
        <div className="section">
          <p className="muted">Loading analytics...</p>
        </div>
      ) : null}

      <div className="grid grid-4">
        <StatCard
          label="Total Tickets"
          value={formatNumber(data.total_tickets)}
          helper={`${activeTickets} active tickets`}
          tone="blue"
        />

        <StatCard
          label="SLA Breached"
          value={formatNumber(data.sla_breached_tickets)}
          helper={`${data.sla_near_breach_tickets} near breach`}
          tone={data.sla_breached_tickets > 0 ? "red" : "green"}
        />

        <StatCard
          label="Avg First Response"
          value={formatMinutes(data.avg_first_response_minutes)}
          helper="Across replied tickets"
          tone="green"
        />

        <StatCard
          label="Avg Resolution"
          value={formatMinutes(data.avg_resolution_minutes)}
          helper="Across resolved tickets"
          tone="blue"
        />
      </div>

      <div className="grid grid-4">
        <StatCard
          label="AI Runs"
          value={formatNumber(data.agent_runs_total)}
          helper={`${data.agent_runs_completed} completed · ${data.agent_runs_failed} failed`}
          tone="blue"
        />

        <StatCard
          label="Tool Executions"
          value={formatNumber(data.tool_executions_total)}
          helper={`${data.tool_executions_success} success · ${data.tool_executions_blocked} blocked`}
          tone="yellow"
        />

        <StatCard
          label="Approvals"
          value={formatNumber(data.approvals_total)}
          helper={`${data.approvals_pending} pending · ${data.approvals_approved} approved`}
          tone={data.approvals_pending > 0 ? "yellow" : "green"}
        />

        <StatCard
          label="Replies Sent"
          value={formatNumber(data.replies_sent)}
          helper={`${replyRate}% of drafts sent`}
          tone="green"
        />
      </div>

      <div className="grid grid-3">
        <BreakdownCard
          title="Tickets by Status"
          items={data.tickets_by_status}
          total={Math.max(1, total)}
        />

        <BreakdownCard
          title="Tickets by Priority"
          items={data.tickets_by_priority}
          total={Math.max(1, total)}
        />

        <BreakdownCard
          title="SLA Health"
          items={data.tickets_by_sla_status}
          total={Math.max(1, total)}
        />
      </div>

      <div className="grid grid-2">
        <BreakdownCard
          title="Tickets by Category"
          items={data.tickets_by_category}
          total={Math.max(1, total)}
        />

        <TrendCard analytics={data} />
      </div>

      <div className="section">
        <div className="section-title">Operational Summary</div>

        <div className="grid grid-4">
          <div>
            <div className="muted">Automation completion</div>
            <strong>{automationRate}%</strong>
          </div>

          <div>
            <div className="muted">Audit events</div>
            <strong>{formatNumber(data.audit_events_total)}</strong>
          </div>

          <div>
            <div className="muted">Closed tickets</div>
            <strong>{formatNumber(data.closed_tickets)}</strong>
          </div>

          <div>
            <div className="muted">Urgent tickets</div>
            <strong>{formatNumber(data.urgent_tickets)}</strong>
          </div>
        </div>
      </div>
    </div>
  );
}