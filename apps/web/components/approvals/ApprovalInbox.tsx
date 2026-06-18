"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Section } from "@/components/ui/Section";
import { apiFetch, bootstrapAuth } from "@/lib/api";
import { unwrapItems } from "@/lib/collections";
import { statusTone } from "@/lib/format";
import type { ApprovalRequest } from "@/types/api";

export function ApprovalInbox() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setError(null);
      await bootstrapAuth();

      const data = await apiFetch<ApprovalRequest[] | { items?: ApprovalRequest[] }>(
        "/approvals",
        { method: "GET" }
      );

      setApprovals(unwrapItems(data));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load approvals");
    }
  }

  async function decide(id: string, action: "approve" | "reject") {
    await apiFetch(`/approvals/${id}/${action}`, {
      method: "POST",
      body: JSON.stringify({
        decision_reason: `${action}d from approval inbox.`,
      }),
    });

    await load();
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <AppShell
      title="Approval Inbox"
      subtitle="Review risky tool executions and customer reply approvals."
    >
      <ErrorBanner message={error} />

      <Section title="Pending and Recent Approvals">
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

              {approval.description ? (
                <div style={{ marginTop: 8 }}>{approval.description}</div>
              ) : null}

              {approval.status === "PENDING" ? (
                <div className="btn-row" style={{ marginTop: 12 }}>
                  <button
                    className="btn btn-success"
                    onClick={() => decide(approval.id, "approve")}
                  >
                    Approve
                  </button>

                  <button
                    className="btn btn-danger"
                    onClick={() => decide(approval.id, "reject")}
                  >
                    Reject
                  </button>
                </div>
              ) : null}
            </div>
          ))}

          {approvals.length === 0 ? (
            <EmptyState message="No approvals found." />
          ) : null}
        </div>
      </Section>
    </AppShell>
  );
}