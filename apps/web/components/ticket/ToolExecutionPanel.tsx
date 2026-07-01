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

function approvalTone(status: string): "green" | "red" | "yellow" | "blue" | "default" {
  if (status === "APPROVED") return "green";
  if (status === "REJECTED") return "red";
  if (status === "PENDING" || status === "REQUIRED") return "yellow";
  return "default";
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
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <div>
                  <strong>{tool.tool_name}</strong>
                  <div className="muted" style={{ marginTop: 6 }}>
                    Risk: {tool.risk_level}
                  </div>
                </div>

                <Badge tone={statusTone(tool.status) as any}>{tool.status}</Badge>
              </div>

              <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
                <Badge tone={approvalTone(tool.approval_status)}>
                  Approval: {tool.approval_status}
                </Badge>

                {approval ? (
                  <Badge tone={approvalTone(approval.status)}>
                    Request: {approval.status}
                  </Badge>
                ) : null}
              </div>

              {approval ? (
                <div className="success" style={{ marginTop: 10 }}>
                  Approval request exists for this execution.
                </div>
              ) : null}

              <div className="btn-row" style={{ marginTop: 10 }}>
                {approval ? (
                  <Link href="/approvals" className="btn btn-secondary">
                    Open Approval Inbox
                  </Link>
                ) : null}

                {canRequestApproval ? (
                  <button className="btn" onClick={() => onRequestApproval(tool.id)}>
                    Request Approval
                  </button>
                ) : null}
              </div>

              {tool.input_args ? (
                <details style={{ marginTop: 12 }}>
                  <summary className="muted" style={{ cursor: "pointer" }}>
                    Input Args
                  </summary>
                  <pre className="code" style={{ marginTop: 10 }}>
                    {JSON.stringify(tool.input_args, null, 2)}
                  </pre>
                </details>
              ) : null}

              {hasOutput(tool) ? (
                <details style={{ marginTop: 12 }}>
                  <summary className="muted" style={{ cursor: "pointer" }}>
                    Tool Output
                  </summary>
                  <pre className="code" style={{ marginTop: 10 }}>
                    {JSON.stringify(tool.output_json, null, 2)}
                  </pre>
                </details>
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
          <EmptyState message="No tool executions yet. Execute agent tools or run manual tool tests." />
        ) : null}
      </div>
    </Section>
  );
}