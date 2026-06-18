import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { statusTone } from "@/lib/format";
import type { ToolExecution } from "@/types/api";

export function ToolExecutionPanel({
  tools,
  onRequestApproval,
}: {
  tools: ToolExecution[];
  onRequestApproval: (executionId: string) => Promise<void>;
}) {
  return (
    <Section title="Tool Executions">
      <div className="list">
        {tools.map((tool) => (
          <div key={tool.id} className="list-item">
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>{tool.tool_name}</strong>
              <Badge tone={statusTone(tool.status) as any}>{tool.status}</Badge>
            </div>

            <div className="muted" style={{ marginTop: 6 }}>
              {tool.risk_level} · approval: {tool.approval_status}
            </div>

            {tool.status === "BLOCKED_APPROVAL_REQUIRED" &&
            tool.approval_status === "PENDING" ? (
              <button
                className="btn"
                style={{ marginTop: 10 }}
                onClick={() => onRequestApproval(tool.id)}
              >
                Request Approval
              </button>
            ) : null}

            {tool.error_message ? (
              <div className="error" style={{ marginTop: 10 }}>
                {tool.error_message}
              </div>
            ) : null}
          </div>
        ))}

        {tools.length === 0 ? <EmptyState message="No tool executions yet." /> : null}
      </div>
    </Section>
  );
}