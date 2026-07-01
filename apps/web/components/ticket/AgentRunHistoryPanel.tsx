import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { formatDate, statusTone } from "@/lib/format";
import type { AgentRun } from "@/types/api";

export function AgentRunHistoryPanel({
  runs,
  selectedRunId,
  onSelectRun,
}: {
  runs: AgentRun[];
  selectedRunId: string | null;
  onSelectRun: (runId: string) => void;
}) {
  return (
    <Section title="Agent Run History">
      <div className="list">
        {runs.map((run, index) => {
          const selected = run.id === selectedRunId;

          return (
            <button
              key={run.id}
              className="list-item"
              style={{
                width: "100%",
                textAlign: "left",
                cursor: "pointer",
                borderColor: selected ? "#2563eb" : undefined,
                background: selected ? "rgba(37, 99, 235, 0.06)" : undefined,
              }}
              onClick={() => onSelectRun(run.id)}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <div>
                  <strong>
                    Run #{runs.length - index} · {run.id.slice(0, 8)}...
                  </strong>
                  <div className="muted" style={{ marginTop: 4 }}>
                    {run.created_at ? formatDate(run.created_at) : "N/A"}
                  </div>
                </div>

                <Badge tone={statusTone(run.status) as any}>{run.status}</Badge>
              </div>

              <div className="grid grid-3" style={{ marginTop: 12 }}>
                <div>
                  <div className="muted">Decision</div>
                  <strong>{run.decision || "NO_ACTION"}</strong>
                </div>

                <div>
                  <div className="muted">Risk</div>
                  <strong>{run.risk_level || "LOW"}</strong>
                </div>

                <div>
                  <div className="muted">Category</div>
                  <strong>{run.detected_category || "N/A"}</strong>
                </div>
              </div>
            </button>
          );
        })}

        {runs.length === 0 ? (
          <EmptyState message="No agent runs yet. Run the agent to start analysis." />
        ) : null}
      </div>
    </Section>
  );
}