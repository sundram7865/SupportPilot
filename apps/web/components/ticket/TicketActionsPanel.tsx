import type { AgentRun, Ticket } from "@/types/api";

function countPlannedTools(latestAgentRun: AgentRun | null) {
  return latestAgentRun?.planned_tools?.length || 0;
}

function countApprovalTools(latestAgentRun: AgentRun | null) {
  return (
    latestAgentRun?.planned_tools?.filter((tool) =>
      Boolean(tool.requires_approval)
    ).length || 0
  );
}

function countSafeTools(latestAgentRun: AgentRun | null) {
  return countPlannedTools(latestAgentRun) - countApprovalTools(latestAgentRun);
}

export function TicketActionsPanel({
  ticket,
  latestAgentRun,
  onRunAgent,
  onExecuteAgentTools,
  onOrderTool,
  onRefundTool,
}: {
  ticket: Ticket | null;
  latestAgentRun: AgentRun | null;
  onRunAgent: () => Promise<void>;
  onExecuteAgentTools: () => Promise<void>;
  onOrderTool: () => Promise<void>;
  onRefundTool: () => Promise<void>;
}) {
  const plannedToolCount = countPlannedTools(latestAgentRun);
  const safeToolCount = countSafeTools(latestAgentRun);
  const approvalToolCount = countApprovalTools(latestAgentRun);

  const canExecuteAgentTools = Boolean(latestAgentRun?.id && plannedToolCount > 0);

  return (
    <section className="section">
      <div className="section-header">
        <div>
          <div className="section-title">Agent & Tool Actions</div>
          <div className="muted">
            Run the agent first, then execute its planned tools.
          </div>
        </div>
      </div>

      <div className="grid grid-3">
        <div className="stat-card">
          <div className="muted">Planned tools</div>
          <div className="stat-value">{plannedToolCount}</div>
        </div>

        <div className="stat-card">
          <div className="muted">Safe tools</div>
          <div className="stat-value">{safeToolCount}</div>
        </div>

        <div className="stat-card">
          <div className="muted">Approval tools</div>
          <div className="stat-value">{approvalToolCount}</div>
        </div>
      </div>

      <div className="btn-row" style={{ marginTop: 16 }}>
        <button className="btn" onClick={onRunAgent}>
          Run Agent
        </button>

        <button
          className="btn btn-secondary"
          onClick={onExecuteAgentTools}
          disabled={!canExecuteAgentTools}
          title={
            canExecuteAgentTools
              ? "Execute safe tools and create approval blocks for risky tools."
              : "Run agent first to generate a tool plan."
          }
        >
          Execute Agent Tools
        </button>
      </div>

      <div className="warning" style={{ marginTop: 14 }}>
        Execute Agent Tools means:
        <br />
        Safe read tools run immediately.
        <br />
        Risky write tools become approval requests and do not execute until
        approved.
      </div>

      <div className="section-title" style={{ marginTop: 18 }}>
        Manual Tool Tests
      </div>

      <div className="btn-row" style={{ marginTop: 10 }}>
        <button className="btn btn-secondary" onClick={onOrderTool}>
          Get Order Context
        </button>

        <button className="btn btn-danger" onClick={onRefundTool}>
          Request Refund
        </button>
      </div>

      <div className="muted" style={{ marginTop: 12 }}>
        Order: {ticket?.external_order_id || "ORD-1001"}
      </div>

      {latestAgentRun ? (
        <div className="muted" style={{ marginTop: 8 }}>
          Latest run: {latestAgentRun.id.slice(0, 8)}... ·{" "}
          {latestAgentRun.status}
        </div>
      ) : null}
    </section>
  );
}