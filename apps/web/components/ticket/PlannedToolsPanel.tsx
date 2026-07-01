import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";

export function PlannedToolsPanel({
  plannedTools,
}: {
  plannedTools: Array<Record<string, unknown>>;
}) {
  return (
    <Section title="Planned Tools">
      <div className="list">
        {plannedTools.map((tool, index) => {
          const requiresApproval = Boolean(tool.requires_approval);

          return (
            <div key={index} className="list-item">
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <div>
                  <strong>{String(tool.tool_name || "Unknown tool")}</strong>
                  <div className="muted" style={{ marginTop: 6 }}>
                    Risk: {String(tool.risk || tool.risk_level || "UNKNOWN")}
                  </div>
                </div>

                <Badge tone={requiresApproval ? "yellow" : "green"}>
                  {requiresApproval ? "Approval required" : "Safe"}
                </Badge>
              </div>

              {tool.reason ? (
                <div className="warning" style={{ marginTop: 10 }}>
                  {String(tool.reason)}
                </div>
              ) : null}

              {tool.args ? (
                <details style={{ marginTop: 12 }}>
                  <summary className="muted" style={{ cursor: "pointer" }}>
                    Tool Arguments
                  </summary>
                  <pre className="code" style={{ marginTop: 10 }}>
                    {JSON.stringify(tool.args, null, 2)}
                  </pre>
                </details>
              ) : null}
            </div>
          );
        })}

        {plannedTools.length === 0 ? (
          <EmptyState message="No tools planned yet. Run the agent to generate a tool plan." />
        ) : null}
      </div>
    </Section>
  );
}