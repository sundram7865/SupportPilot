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
        {runs.map((run) => {
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
              }}
              onClick={() => onSelectRun(run.id)}
            >
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{run.id.slice(0, 8)}...</strong>
                <Badge tone={statusTone(run.status) as any}>{run.status}</Badge>
              </div>

              <div className="muted" style={{ marginTop: 6 }}>
                Decision: {run.decision || "NO_ACTION"}
              </div>

              <div className="muted" style={{ marginTop: 6 }}>
                Risk: {run.risk_level || "LOW"} · Category:{" "}
                {run.detected_category || "N/A"}
              </div>

              <div className="muted" style={{ marginTop: 6 }}>
                {run.created_at ? formatDate(run.created_at) : "N/A"}
              </div>
            </button>
          );
        })}

        {runs.length === 0 ? (
          <EmptyState message="No agent runs yet." />
        ) : null}
      </div>
    </Section>
  );
}