import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { formatDate, statusTone } from "@/lib/format";
import type { AgentRunStep } from "@/types/api";

function formatDuration(ms?: number | null) {
  if (ms == null) return "N/A";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function AgentRunStepDetailPanel({
  steps,
}: {
  steps: AgentRunStep[];
}) {
  const [openStepId, setOpenStepId] = useState<string | null>(null);

  return (
    <Section title="Agent Step Details">
      <div className="list">
        {steps.map((step, index) => {
          const open = openStepId === step.id;

          return (
            <div key={step.id} className="list-item">
              <button
                style={{
                  width: "100%",
                  textAlign: "left",
                  background: "transparent",
                  border: 0,
                  padding: 0,
                  cursor: "pointer",
                }}
                onClick={() => setOpenStepId(open ? null : step.id)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                  <div>
                    <strong>
                      {index + 1}. {step.step_name}
                    </strong>

                    <div className="muted" style={{ marginTop: 6 }}>
                      Duration: {formatDuration(step.duration_ms)} ·{" "}
                      {formatDate(step.created_at)}
                    </div>
                  </div>

                  <Badge tone={statusTone(step.status) as any}>{step.status}</Badge>
                </div>
              </button>

              {step.error_message ? (
                <div className="error" style={{ marginTop: 10 }}>
                  {step.error_message}
                </div>
              ) : null}

              {open ? (
                <div style={{ marginTop: 12 }}>
                  <div className="grid grid-2">
                    <div>
                      <div className="muted">Input</div>
                      <pre className="code">
                        {JSON.stringify(step.input_json || {}, null, 2)}
                      </pre>
                    </div>

                    <div>
                      <div className="muted">Output</div>
                      <pre className="code">
                        {JSON.stringify(step.output_json || {}, null, 2)}
                      </pre>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          );
        })}

        {steps.length === 0 ? (
          <EmptyState message="No step-level trace yet. Run the agent to see node execution details." />
        ) : null}
      </div>
    </Section>
  );
}