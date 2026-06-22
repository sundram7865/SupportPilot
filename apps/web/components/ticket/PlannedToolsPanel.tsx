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
        {plannedTools.map((tool, index) => (
          <div key={index} className="list-item">
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>{String(tool.tool_name || "Unknown tool")}</strong>
              <Badge tone={tool.requires_approval ? "yellow" : "green"}>
                {tool.requires_approval ? "Approval required" : "Safe"}
              </Badge>
            </div>

            <div className="muted" style={{ marginTop: 6 }}>
              Risk: {String(tool.risk || "UNKNOWN")}
            </div>

            {tool.reason ? (
              <div style={{ marginTop: 8 }}>{String(tool.reason)}</div>
            ) : null}

            {tool.args ? (
              <pre className="code" style={{ marginTop: 10 }}>
                {JSON.stringify(tool.args, null, 2)}
              </pre>
            ) : null}
          </div>
        ))}

        {plannedTools.length === 0 ? (
          <EmptyState message="No tools planned yet." />
        ) : null}
      </div>
    </Section>
  );
}