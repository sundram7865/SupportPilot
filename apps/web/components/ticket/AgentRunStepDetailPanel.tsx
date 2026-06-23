import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { formatDate, statusTone } from "@/lib/format";
import type { AgentRunStep } from "@/types/api";

export function AgentRunStepDetailPanel({
  steps,
}: {
  steps: AgentRunStep[];
}) {
  const [openStepId, setOpenStepId] = useState<string | null>(null);

  return (
    <Section title="Agent Step Details">
      <div className="list">
        {steps.map((step) => {
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
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{step.step_name}</strong>
                  <Badge tone={statusTone(step.status) as any}>
                    {step.status}
                  </Badge>
                </div>

                <div className="muted" style={{ marginTop: 6 }}>
                  Duration:{" "}
                  {step.duration_ms != null ? `${step.duration_ms}ms` : "N/A"} ·{" "}
                  {formatDate(step.created_at)}
                </div>
              </button>

              {step.error_message ? (
                <div className="error" style={{ marginTop: 10 }}>
                  {step.error_message}
                </div>
              ) : null}

              {open ? (
                <div style={{ marginTop: 12 }}>
                  <div className="muted">Input</div>
                  <pre className="code">
                    {JSON.stringify(step.input_json || {}, null, 2)}
                  </pre>

                  <div className="muted" style={{ marginTop: 12 }}>
                    Output
                  </div>
                  <pre className="code">
                    {JSON.stringify(step.output_json || {}, null, 2)}
                  </pre>
                </div>
              ) : null}
            </div>
          );
        })}

        {steps.length === 0 ? (
          <EmptyState message="No agent step details yet." />
        ) : null}
      </div>
    </Section>
  );
}