import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { formatDate, statusTone } from "@/lib/format";
import type { AgentRun } from "@/types/api";

function formatDuration(ms?: number | null) {
  if (ms == null) return "N/A";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function AgentRunSummaryPanel({
  latestAgentRun,
}: {
  latestAgentRun: AgentRun | null;
}) {
  if (!latestAgentRun) {
    return (
      <Section title="Latest Agent Run">
        <EmptyState message="No agent run yet. Click Run Agent to start classification, risk check, planning, and drafting." />
      </Section>
    );
  }

  return (
    <Section
      title="Latest Agent Run"
      action={
        <Badge tone={statusTone(latestAgentRun.status) as any}>
          {latestAgentRun.status}
        </Badge>
      }
    >
      <div className="grid grid-3">
        <div>
          <div className="muted">Decision</div>
          <strong>{latestAgentRun.decision || "NO_ACTION"}</strong>
        </div>

        <div>
          <div className="muted">Risk</div>
          <Badge tone={statusTone(latestAgentRun.risk_level || "LOW") as any}>
            {latestAgentRun.risk_level || "LOW"}
          </Badge>
        </div>

        <div>
          <div className="muted">Duration</div>
          <strong>{formatDuration(latestAgentRun.duration_ms)}</strong>
        </div>
      </div>

      <div className="grid grid-3" style={{ marginTop: 14 }}>
        <div>
          <div className="muted">Detected Category</div>
          <strong>{latestAgentRun.detected_category || "Not detected"}</strong>
        </div>

        <div>
          <div className="muted">Detected Priority</div>
          <strong>{latestAgentRun.detected_priority || "Not detected"}</strong>
        </div>

        <div>
          <div className="muted">Provider</div>
          <strong>
            {latestAgentRun.provider || "N/A"}
            {latestAgentRun.model_name ? ` · ${latestAgentRun.model_name}` : ""}
          </strong>
        </div>
      </div>

      {latestAgentRun.reasoning_summary ? (
        <div className="list-item" style={{ marginTop: 14 }}>
          <div className="muted">Reasoning Summary</div>
          <p style={{ marginBottom: 0, whiteSpace: "pre-wrap" }}>
            {latestAgentRun.reasoning_summary}
          </p>
        </div>
      ) : null}

      {latestAgentRun.draft_response ? (
        <div className="list-item" style={{ marginTop: 14 }}>
          <div className="muted">Draft Response</div>
          <div style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>
            {latestAgentRun.draft_response}
          </div>
        </div>
      ) : null}

      {latestAgentRun.error_message ? (
        <div className="error" style={{ marginTop: 14 }}>
          {latestAgentRun.error_message}
        </div>
      ) : null}

      <div className="muted" style={{ marginTop: 14 }}>
        Created:{" "}
        {latestAgentRun.created_at ? formatDate(latestAgentRun.created_at) : "N/A"}
      </div>
    </Section>
  );
}