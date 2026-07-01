import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { statusTone } from "@/lib/format";
import type { ApprovalRequest } from "@/types/api";

function getApprovalDescription(approval: ApprovalRequest) {
  if (approval.tool_name) {
    return `${approval.tool_name} · ${approval.risk_level}`;
  }

  return `Customer reply · ${approval.risk_level}`;
}

export function ApprovalPanel({
  approvals,
  onApprove,
  onReject,
}: {
  approvals: ApprovalRequest[];
  onApprove: (approvalId: string) => Promise<void>;
  onReject: (approvalId: string) => Promise<void>;
}) {
  const pendingCount = approvals.filter((approval) => approval.status === "PENDING").length;

  return (
    <Section
      title="Approvals"
      action={pendingCount > 0 ? <Badge tone="yellow">{pendingCount} pending</Badge> : null}
    >
      <div className="list">
        {approvals.map((approval) => (
          <div key={approval.id} className="list-item">
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <div>
                <strong>{approval.title}</strong>
                <div className="muted" style={{ marginTop: 6 }}>
                  {getApprovalDescription(approval)}
                </div>
              </div>

              <Badge tone={statusTone(approval.status) as any}>
                {approval.status}
              </Badge>
            </div>

            {approval.description ? (
              <div style={{ marginTop: 10 }}>{approval.description}</div>
            ) : null}

            {approval.request_reason ? (
              <div className="warning" style={{ marginTop: 10 }}>
                Reason: {approval.request_reason}
              </div>
            ) : null}

            {approval.decision_reason ? (
              <div className="success" style={{ marginTop: 10 }}>
                Decision: {approval.decision_reason}
              </div>
            ) : null}

            {approval.status === "PENDING" ? (
              <div className="btn-row" style={{ marginTop: 12 }}>
                <button
                  className="btn btn-success"
                  onClick={() => onApprove(approval.id)}
                >
                  Approve
                </button>

                <button
                  className="btn btn-danger"
                  onClick={() => onReject(approval.id)}
                >
                  Reject
                </button>
              </div>
            ) : null}
          </div>
        ))}

        {approvals.length === 0 ? (
          <EmptyState message="No approval requests yet." />
        ) : null}
      </div>
    </Section>
  );
}