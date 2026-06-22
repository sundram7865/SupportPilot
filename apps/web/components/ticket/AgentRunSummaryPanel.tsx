import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { formatDate, statusTone } from "@/lib/format";
import type { AgentRun } from "@/types/api";

export function AgentRunSummaryPanel({
  latestAgentRun,
}: {
  latestAgentRun: AgentRun | null;
}) {
  if (!latestAgentRun) {
    return (
      <Section title="Latest Agent Run">
        <EmptyState message="No agent run yet. Click Run Agent to start." />
      </Section>
    );
  }

  return (
    <Section title="Latest Agent Run">
      <div className="grid grid-3">
        <div>
          <div className="muted">Status</div>
          <Badge tone={statusTone(latestAgentRun.status) as any}>
            {latestAgentRun.status}
          </Badge>
        </div>

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
      </div>

      <div className="grid grid-3" style={{ marginTop: 14 }}>
        <div>
          <div className="muted">Category</div>
          <strong>{latestAgentRun.detected_category || "Not detected"}</strong>
        </div>

        <div>
          <div className="muted">Priority</div>
          <strong>{latestAgentRun.detected_priority || "Not detected"}</strong>
        </div>

        <div>
          <div className="muted">Duration</div>
          <strong>
            {latestAgentRun.duration_ms != null
              ? `${latestAgentRun.duration_ms}ms`
              : "N/A"}
          </strong>
        </div>
      </div>

      {latestAgentRun.reasoning_summary ? (
        <div style={{ marginTop: 14 }}>
          <div className="muted">Reasoning Summary</div>
          <p>{latestAgentRun.reasoning_summary}</p>
        </div>
      ) : null}

      {latestAgentRun.draft_response ? (
        <div style={{ marginTop: 14 }}>
          <div className="muted">Draft Response</div>
          <div className="list-item">{latestAgentRun.draft_response}</div>
        </div>
      ) : null}

      {latestAgentRun.error_message ? (
        <div className="error" style={{ marginTop: 14 }}>
          {latestAgentRun.error_message}
        </div>
      ) : null}

      <div className="muted" style={{ marginTop: 14 }}>
        Created:{" "}
        {latestAgentRun.created_at
          ? formatDate(latestAgentRun.created_at)
          : "N/A"}
      </div>

      {latestAgentRun.steps?.length ? (
        <div style={{ marginTop: 16 }}>
          <div className="section-title">Agent Steps</div>

          <div className="list">
            {latestAgentRun.steps.map((step) => (
              <div key={step.id} className="list-item">
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{step.step_name}</strong>
                  <Badge tone={statusTone(step.status) as any}>
                    {step.status}
                  </Badge>
                </div>

                <div className="muted" style={{ marginTop: 6 }}>
                  Duration:{" "}
                  {step.duration_ms != null ? `${step.duration_ms}ms` : "N/A"}
                </div>

                {step.error_message ? (
                  <div className="error" style={{ marginTop: 8 }}>
                    {step.error_message}
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </Section>
  );
}