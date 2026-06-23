"use client";

import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Section } from "@/components/ui/Section";
import { apiFetch, bootstrapAuth } from "@/lib/api";
import { unwrapItems } from "@/lib/collections";
import { formatDate, statusTone } from "@/lib/format";
import type { ApprovalRequest } from "@/types/api";

type ApprovalStatusFilter = "ALL" | "PENDING" | "APPROVED" | "REJECTED";

function getToolError(approval: ApprovalRequest | null) {
  if (!approval?.result_json) return null;

  const result = approval.result_json as Record<string, unknown>;
  const toolError = result.tool_error;

  return typeof toolError === "string" && toolError.length > 0
    ? toolError
    : null;
}

function getToolStatus(approval: ApprovalRequest | null) {
  if (!approval?.result_json) return null;

  const result = approval.result_json as Record<string, unknown>;
  const toolStatus = result.tool_status;

  return typeof toolStatus === "string" && toolStatus.length > 0
    ? toolStatus
    : null;
}

export function ApprovalInbox() {
  const { getToken, isSignedIn } = useAuth();

  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [selectedApproval, setSelectedApproval] =
    useState<ApprovalRequest | null>(null);

  const [statusFilter, setStatusFilter] =
    useState<ApprovalStatusFilter>("PENDING");

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [workingId, setWorkingId] = useState<string | null>(null);

  const tokenGetter = isSignedIn ? getToken : undefined;

  const filteredTitle = useMemo(() => {
    if (statusFilter === "ALL") return "All Approvals";
    return `${statusFilter} Approvals`;
  }, [statusFilter]);

  async function load() {
    if (!isSignedIn || !tokenGetter) return;

    try {
      setLoading(true);
      setError(null);

      await bootstrapAuth(tokenGetter);

      const query =
        statusFilter === "ALL"
          ? "?limit=50&offset=0"
          : `?status=${statusFilter}&limit=50&offset=0`;

      const data = await apiFetch<{ items?: ApprovalRequest[] }>(
        `/approvals${query}`,
        {
          method: "GET",
          getToken: tokenGetter,
        }
      );

      const items = unwrapItems(data);

      setApprovals(items);

      if (!selectedApproval && items.length > 0) {
        await loadApprovalDetail(items[0].id);
      }

      if (
        selectedApproval &&
        !items.some((approval) => approval.id === selectedApproval.id)
      ) {
        setSelectedApproval(items[0] || null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load approvals.");
    } finally {
      setLoading(false);
    }
  }

  async function loadApprovalDetail(approvalId: string) {
    if (!tokenGetter) return;

    try {
      setError(null);

      const approval = await apiFetch<ApprovalRequest>(
        `/approvals/${approvalId}`,
        {
          method: "GET",
          getToken: tokenGetter,
        }
      );

      setSelectedApproval(approval);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load approval detail."
      );
    }
  }

  async function decide(id: string, action: "approve" | "reject") {
    if (!tokenGetter) return;

    try {
      setWorkingId(id);
      setError(null);

      const updated = await apiFetch<ApprovalRequest>(
        `/approvals/${id}/${action}`,
        {
          method: "POST",
          getToken: tokenGetter,
          body: JSON.stringify({
            decision_reason: `${action}d from approval inbox.`,
          }),
        }
      );

      setSelectedApproval(updated);
      await load();
      await loadApprovalDetail(id);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : `Failed to ${action} approval.`
      );
    } finally {
      setWorkingId(null);
    }
  }

  useEffect(() => {
    load();
  }, [isSignedIn, statusFilter]);

  const selectedToolError = getToolError(selectedApproval);
  const selectedToolStatus = getToolStatus(selectedApproval);

  return (
    <AppShell
      title="Approval Inbox"
      subtitle="Review risky tool executions and customer reply approvals."
      right={
        <div className="section">
          <div className="muted">Filter</div>

          <select
            className="select"
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(event.target.value as ApprovalStatusFilter)
            }
          >
            <option value="PENDING">PENDING</option>
            <option value="APPROVED">APPROVED</option>
            <option value="REJECTED">REJECTED</option>
            <option value="ALL">ALL</option>
          </select>

          <div style={{ marginTop: 10 }}>
            <button
              className="btn btn-secondary"
              onClick={load}
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>
      }
    >
      <ErrorBanner message={error} />

      <div className="grid grid-main">
        <Section title={filteredTitle}>
          {loading ? <p className="muted">Loading approvals...</p> : null}

          <div className="list">
            {approvals.map((approval) => {
              const selected = selectedApproval?.id === approval.id;

              return (
                <button
                  key={approval.id}
                  className="list-item"
                  style={{
                    width: "100%",
                    textAlign: "left",
                    cursor: "pointer",
                    borderColor: selected ? "#2563eb" : undefined,
                  }}
                  onClick={() => loadApprovalDetail(approval.id)}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 12,
                    }}
                  >
                    <strong>{approval.title}</strong>
                    <Badge tone={statusTone(approval.status) as any}>
                      {approval.status}
                    </Badge>
                  </div>

                  <div className="muted" style={{ marginTop: 6 }}>
                    {approval.tool_name || "Customer reply"} ·{" "}
                    {approval.risk_level}
                  </div>

                  {approval.request_reason ? (
                    <div className="muted" style={{ marginTop: 6 }}>
                      Reason: {approval.request_reason}
                    </div>
                  ) : null}

                  <div className="muted" style={{ marginTop: 6 }}>
                    {approval.created_at ? formatDate(approval.created_at) : "N/A"}
                  </div>
                </button>
              );
            })}

            {!loading && approvals.length === 0 ? (
              <EmptyState message="No approvals found." />
            ) : null}
          </div>
        </Section>

        <Section title="Approval Detail">
          {!selectedApproval ? (
            <EmptyState message="Select an approval to view details." />
          ) : (
            <div className="grid">
              <div className="list-item">
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <strong>{selectedApproval.title}</strong>
                  <Badge tone={statusTone(selectedApproval.status) as any}>
                    {selectedApproval.status}
                  </Badge>
                </div>

                {selectedApproval.description ? (
                  <p style={{ marginTop: 10 }}>{selectedApproval.description}</p>
                ) : null}

                <div className="muted" style={{ marginTop: 8 }}>
                  Tool: {selectedApproval.tool_name || "Customer reply"}
                </div>

                <div className="muted" style={{ marginTop: 6 }}>
                  Risk: {selectedApproval.risk_level}
                </div>

                {selectedApproval.ticket_id ? (
                  <div style={{ marginTop: 10 }}>
                    <Link
                      href={`/tickets/${selectedApproval.ticket_id}`}
                      className="btn btn-secondary"
                    >
                      Open Ticket
                    </Link>
                  </div>
                ) : null}
              </div>

              <div className="list-item">
                <div className="section-title">Input Args</div>
                <pre className="code">
                  {JSON.stringify(selectedApproval.input_args || {}, null, 2)}
                </pre>
              </div>

              {selectedApproval.request_reason ? (
                <div className="list-item">
                  <div className="section-title">Request Reason</div>
                  <p>{selectedApproval.request_reason}</p>
                </div>
              ) : null}

              {selectedApproval.decision_reason ? (
                <div className="list-item">
                  <div className="section-title">Decision Reason</div>
                  <p>{selectedApproval.decision_reason}</p>
                </div>
              ) : null}

              {selectedToolStatus ? (
                <div className="list-item">
                  <div className="section-title">Tool Result Status</div>
                  <Badge tone={statusTone(selectedToolStatus) as any}>
                    {selectedToolStatus}
                  </Badge>
                </div>
              ) : null}

              {selectedToolError ? (
                <div className="error">
                  Approved tool failed: {selectedToolError}
                </div>
              ) : null}

              {selectedApproval.result_json ? (
                <div className="list-item">
                  <div className="section-title">Result JSON</div>
                  <pre className="code">
                    {JSON.stringify(selectedApproval.result_json, null, 2)}
                  </pre>
                </div>
              ) : null}

              {selectedApproval.status === "PENDING" ? (
                <div className="btn-row">
                  <button
                    className="btn btn-success"
                    disabled={workingId === selectedApproval.id}
                    onClick={() => decide(selectedApproval.id, "approve")}
                  >
                    {workingId === selectedApproval.id
                      ? "Approving..."
                      : "Approve"}
                  </button>

                  <button
                    className="btn btn-danger"
                    disabled={workingId === selectedApproval.id}
                    onClick={() => decide(selectedApproval.id, "reject")}
                  >
                    {workingId === selectedApproval.id
                      ? "Rejecting..."
                      : "Reject"}
                  </button>
                </div>
              ) : (
                <div className="success">
                  This approval has already been decided.
                </div>
              )}
            </div>
          )}
        </Section>
      </div>
    </AppShell>
  );
}