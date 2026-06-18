import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { statusTone } from "@/lib/format";
import type { ApprovalRequest } from "@/types/api";

export function ApprovalPanel({
  approvals,
  onApprove,
  onReject,
}: {
  approvals: ApprovalRequest[];
  onApprove: (approvalId: string) => Promise<void>;
  onReject: (approvalId: string) => Promise<void>;
}) {
  return (
    <Section title="Approvals">
      <div className="list">
        {approvals.map((approval) => (
          <div key={approval.id} className="list-item">
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>{approval.title}</strong>
              <Badge tone={statusTone(approval.status) as any}>
                {approval.status}
              </Badge>
            </div>

            <div className="muted" style={{ marginTop: 6 }}>
              {approval.tool_name || "Customer reply"} · {approval.risk_level}
            </div>

            {approval.status === "PENDING" ? (
              <div className="btn-row" style={{ marginTop: 10 }}>
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

        {approvals.length === 0 ? <EmptyState message="No approvals yet." /> : null}
      </div>
    </Section>
  );
}