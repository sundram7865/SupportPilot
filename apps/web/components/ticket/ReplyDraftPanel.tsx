import { useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { statusTone } from "@/lib/format";
import type { ReplyDraft } from "@/types/api";

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
              {draft.source}
            </div>

            <div style={{ marginTop: 8 }}>{draft.body}</div>

            <div className="btn-row" style={{ marginTop: 10 }}>
              {draft.status === "DRAFT" ? (
                <>
                  <button
                    className="btn btn-secondary"
                    onClick={() => onSubmit(draft.id)}
                  >
                    Submit Approval
                  </button>
                  <button className="btn" onClick={() => onSend(draft.id)}>
                    Send Direct
                  </button>
                </>
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
                  Send
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