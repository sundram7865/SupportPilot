import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";

type PlannedTool = Record<string, unknown>;

function getToolName(tool: PlannedTool) {
  return String(tool.tool_name || "Unknown tool");
}

function isApprovalRequired(tool: PlannedTool) {
  return Boolean(tool.requires_approval);
}

function getRisk(tool: PlannedTool) {
  return String(tool.risk || "UNKNOWN");
}

function getRiskTone(tool: PlannedTool) {
  const risk = getRisk(tool);

  if (risk === "READ_ONLY") return "green";
  if (risk === "WRITE_ACTION") return "yellow";
  if (risk === "HIGH_RISK") return "red";

  return "blue";
}

export function PlannedToolsPanel({
  plannedTools,
}: {
  plannedTools: PlannedTool[];
}) {
  const readOnlyTools = plannedTools.filter((tool) => !isApprovalRequired(tool));
  const approvalTools = plannedTools.filter((tool) => isApprovalRequired(tool));

  return (
    <Section title="Agent Tool Plan">
      <div className="grid grid-3">
        <div className="stat-card">
          <div className="muted">Total planned</div>
          <div className="stat-value">{plannedTools.length}</div>
        </div>

        <div className="stat-card">
          <div className="muted">Safe tools</div>
          <div className="stat-value">{readOnlyTools.length}</div>
        </div>

        <div className="stat-card">
          <div className="muted">Needs approval</div>
          <div className="stat-value">{approvalTools.length}</div>
        </div>
      </div>

      <div className="list" style={{ marginTop: 16 }}>
        {plannedTools.map((tool, index) => {
          const approvalRequired = isApprovalRequired(tool);

          return (
            <div key={index} className="list-item">
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{getToolName(tool)}</strong>

                <Badge tone={approvalRequired ? "yellow" : "green"}>
                  {approvalRequired ? "Approval Required" : "Safe Auto Tool"}
                </Badge>
              </div>

              <div className="muted" style={{ marginTop: 6 }}>
                Risk:{" "}
                <Badge tone={getRiskTone(tool) as any}>{getRisk(tool)}</Badge>
              </div>

              {tool.reason ? (
                <div style={{ marginTop: 10 }}>
                  <div className="muted">Reason</div>
                  <div>{String(tool.reason)}</div>
                </div>
              ) : null}

              <div style={{ marginTop: 10 }}>
                <div className="muted">Tool Args</div>
                <pre className="code">
                  {JSON.stringify(tool.args || {}, null, 2)}
                </pre>
              </div>

              {approvalRequired ? (
                <div className="warning" style={{ marginTop: 10 }}>
                  This tool will not execute directly. It will create a blocked
                  execution and require human approval first.
                </div>
              ) : (
                <div className="success" style={{ marginTop: 10 }}>
                  This is read-only and can be executed safely.
                </div>
              )}
            </div>
          );
        })}

        {plannedTools.length === 0 ? (
          <EmptyState message="No tools planned yet. Run the agent first." />
        ) : null}
      </div>
    </Section>
  );
}