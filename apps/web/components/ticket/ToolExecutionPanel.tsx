import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { statusTone } from "@/lib/format";
import type { ApprovalRequest, ToolExecution } from "@/types/api";

function getApprovalForExecution(
  approvals: ApprovalRequest[],
  executionId: string
) {
  return approvals.find((approval) => approval.tool_execution_id === executionId);
}

function hasOutput(tool: ToolExecution) {
  return tool.output_json && Object.keys(tool.output_json).length > 0;
}

export function ToolExecutionPanel({
  tools,
  approvals,
  onRequestApproval,
}: {
  tools: ToolExecution[];
  approvals: ApprovalRequest[];
  onRequestApproval: (executionId: string) => Promise<void>;
}) {
  return (
    <Section title="Tool Executions">
      <div className="list">
        {tools.map((tool) => {
          const approval = getApprovalForExecution(approvals, tool.id);

          const canRequestApproval =
            tool.status === "BLOCKED_APPROVAL_REQUIRED" &&
            tool.approval_status === "PENDING" &&
            !approval;

          return (
            <div key={tool.id} className="list-item">
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{tool.tool_name}</strong>
                <Badge tone={statusTone(tool.status) as any}>{tool.status}</Badge>
              </div>

              <div className="muted" style={{ marginTop: 6 }}>
                Risk: {tool.risk_level} · approval: {tool.approval_status}
              </div>

              {approval ? (
                <div className="success" style={{ marginTop: 10 }}>
                  Approval request exists:{" "}
                  <strong>{approval.status}</strong>
                </div>
              ) : null}

              {approval ? (
                <div style={{ marginTop: 10 }}>
                  <Link href="/approvals" className="btn btn-secondary">
                    Open Approval Inbox
                  </Link>
                </div>
              ) : null}

              {canRequestApproval ? (
                <button
                  className="btn"
                  style={{ marginTop: 10 }}
                  onClick={() => onRequestApproval(tool.id)}
                >
                  Request Approval
                </button>
              ) : null}

              {tool.input_args ? (
                <div style={{ marginTop: 12 }}>
                  <div className="muted">Input Args</div>
                  <pre className="code">
                    {JSON.stringify(tool.input_args, null, 2)}
                  </pre>
                </div>
              ) : null}

              {hasOutput(tool) ? (
                <div style={{ marginTop: 12 }}>
                  <div className="muted">Output</div>
                  <pre className="code">
                    {JSON.stringify(tool.output_json, null, 2)}
                  </pre>
                </div>
              ) : null}

              {tool.error_message ? (
                <div className="error" style={{ marginTop: 10 }}>
                  {tool.error_message}
                </div>
              ) : null}
            </div>
          );
        })}

        {tools.length === 0 ? (
          <EmptyState message="No tool executions yet." />
        ) : null}
      </div>
    </Section>
  );
}