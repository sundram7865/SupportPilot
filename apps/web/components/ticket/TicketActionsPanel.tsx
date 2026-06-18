import type { AgentRun, Ticket } from "@/types/api";

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
  return (
    <section className="section">
      <div className="section-header">
        <div className="section-title">Agent & Tool Actions</div>
      </div>

      <div className="btn-row">
        <button className="btn" onClick={onRunAgent}>
          Run Agent
        </button>

        <button className="btn btn-secondary" onClick={onExecuteAgentTools}>
          Execute Agent Tools
        </button>

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
        <pre className="code" style={{ marginTop: 14 }}>
          {JSON.stringify(latestAgentRun, null, 2)}
        </pre>
      ) : null}
    </section>
  );
}