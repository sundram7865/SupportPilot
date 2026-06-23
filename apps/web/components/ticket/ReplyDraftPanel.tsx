import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { statusTone } from "@/lib/format";
import type { ReplyDraft } from "@/types/api";

function getDraftHint(status: string) {
  if (status === "DRAFT") {
    return "Submit this draft for approval before sending.";
  }

  if (status === "PENDING_APPROVAL") {
    return "Waiting for approval before it can be sent.";
  }

  if (status === "APPROVED") {
    return "Approved and ready to send to the customer.";
  }

  if (status === "SENT") {
    return "This reply was sent to the customer.";
  }

  if (status === "REJECTED") {
    return "This draft was rejected. Edit it before submitting again.";
  }

  return "";
}

export function ReplyDraftPanel({
  drafts,
  onCreate,
  onCreateFromAgent,
  onSubmit,
  onApprove,
  onSend,
}: {
  drafts: ReplyDraft[];
  onCreate: (body: string) => Promise<void>;
  onCreateFromAgent: () => Promise<void>;
  onSubmit: (draftId: string) => Promise<void>;
  onApprove: (draftId: string) => Promise<void>;
  onSend: (draftId: string) => Promise<void>;
}) {
  const [body, setBody] = useState(
    "Hi, thanks for contacting UrbanKart support. We are checking your request and will update you shortly."
  );

  return (
    <Section title="Reply Drafts">
      <div className="form-row">
        <label className="label">New draft body</label>
        <textarea
          className="textarea"
          value={body}
          onChange={(event) => setBody(event.target.value)}
        />
      </div>

      <div className="btn-row">
        <button className="btn" onClick={() => onCreate(body)}>
          Create Draft
        </button>

        <button className="btn btn-secondary" onClick={onCreateFromAgent}>
          Create AI Draft
        </button>
      </div>

      <div className="list" style={{ marginTop: 16 }}>
        {drafts.map((draft) => (
          <div key={draft.id} className="list-item">
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>{draft.subject || "Reply draft"}</strong>
              <Badge tone={statusTone(draft.status) as any}>{draft.status}</Badge>
            </div>

            <div className="muted" style={{ marginTop: 6 }}>
              Source: {draft.source}
            </div>

            <div className="muted" style={{ marginTop: 6 }}>
              {getDraftHint(draft.status)}
            </div>

            <div style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>
              {draft.body}
            </div>

            {draft.rejection_reason ? (
              <div className="error" style={{ marginTop: 8 }}>
                Rejection reason: {draft.rejection_reason}
              </div>
            ) : null}

            {draft.approval_reason ? (
              <div className="success" style={{ marginTop: 8 }}>
                Approval reason: {draft.approval_reason}
              </div>
            ) : null}

            {draft.sent_message_id ? (
              <div className="success" style={{ marginTop: 8 }}>
                Sent message ID: {draft.sent_message_id}
              </div>
            ) : null}

            <div className="btn-row" style={{ marginTop: 10 }}>
              {draft.status === "DRAFT" || draft.status === "REJECTED" ? (
                <button
                  className="btn btn-secondary"
                  onClick={() => onSubmit(draft.id)}
                >
                  Submit Approval
                </button>
              ) : null}

              {draft.status === "PENDING_APPROVAL" ? (
                <button
                  className="btn btn-success"
                  onClick={() => onApprove(draft.id)}
                >
                  Approve Draft
                </button>
              ) : null}

              {draft.status === "APPROVED" ? (
                <button className="btn" onClick={() => onSend(draft.id)}>
                  Send to Customer
                </button>
              ) : null}

              {draft.status === "SENT" ? (
                <button className="btn btn-secondary" disabled>
                  Already Sent
                </button>
              ) : null}
            </div>
          </div>
        ))}

        {drafts.length === 0 ? <EmptyState message="No reply drafts yet." /> : null}
      </div>
    </Section>
  );
}