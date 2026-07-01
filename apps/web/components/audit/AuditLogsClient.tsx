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
import type { AuditLog, AuditLogListResponse } from "@/types/api";

type AuditFilters = {
  action: string;
  resource_type: string;
  ticket_id: string;
};

const ACTION_OPTIONS = [
  "TICKET_CREATED",
  "TICKET_UPDATED",
  "TICKET_MESSAGE_ADDED",
  "TICKET_INTERNAL_NOTE_ADDED",
  "TICKET_STATUS_CHANGED",
  "AGENT_RUN_STARTED",
  "AGENT_RUN_COMPLETED",
  "AGENT_RUN_FAILED",
  "TOOL_EXECUTION_STARTED",
  "TOOL_EXECUTION_BLOCKED",
  "TOOL_EXECUTION_COMPLETED",
  "TOOL_EXECUTION_FAILED",
  "APPROVED_TOOL_EXECUTION_STARTED",
  "APPROVED_TOOL_EXECUTION_COMPLETED",
  "APPROVED_TOOL_EXECUTION_FAILED",
  "APPROVAL_REQUEST_CREATED",
  "APPROVAL_REQUEST_APPROVED",
  "APPROVAL_REQUEST_REJECTED",
  "REPLY_DRAFT_CREATED",
  "REPLY_DRAFT_UPDATED",
  "REPLY_DRAFT_SUBMITTED_FOR_APPROVAL",
  "REPLY_DRAFT_APPROVED",
  "REPLY_DRAFT_REJECTED",
  "CUSTOMER_REPLY_SENT",
  "SLA_NEAR_BREACH",
  "SLA_BREACHED",
];

const RESOURCE_OPTIONS = [
  "TICKET",
  "TICKET_MESSAGE",
  "TICKET_INTERNAL_NOTE",
  "AGENT_RUN",
  "TOOL_EXECUTION",
  "APPROVAL_REQUEST",
  "REPLY_DRAFT",
  "ORGANIZATION",
  "INTEGRATION",
  "SLA",
];

function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";

  try {
    return new Intl.DateTimeFormat("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function getActionTone(action: string): "green" | "red" | "yellow" | "blue" | "default" {
  if (action.includes("FAILED") || action.includes("REJECTED") || action.includes("BREACHED")) {
    return "red";
  }

  if (action.includes("BLOCKED") || action.includes("PENDING") || action.includes("APPROVAL")) {
    return "yellow";
  }

  if (action.includes("COMPLETED") || action.includes("APPROVED") || action.includes("SENT")) {
    return "green";
  }

  if (action.includes("STARTED") || action.includes("CREATED") || action.includes("UPDATED")) {
    return "blue";
  }

  return "default";
}

function shortId(value: string | null | undefined) {
  if (!value) return "—";
  return value.length > 12 ? `${value.slice(0, 8)}...` : value;
}

function isValidUuidLike(value: string) {
  return /^[0-9a-fA-F-]{36}$/.test(value.trim());
}

function metadataPreview(value: Record<string, unknown> | null) {
  if (!value) return "—";

  try {
    const text = JSON.stringify(value, null, 2);
    return text.length > 260 ? `${text.slice(0, 260)}...` : text;
  } catch {
    return "Unable to render metadata.";
  }
}

function buildAuditQuery(filters: AuditFilters) {
  const params = new URLSearchParams();

  params.set("limit", "50");
  params.set("offset", "0");

  if (filters.action) {
    params.set("action", filters.action);
  }

  if (filters.resource_type) {
    params.set("resource_type", filters.resource_type);
  }

  if (filters.ticket_id && isValidUuidLike(filters.ticket_id)) {
    params.set("ticket_id", filters.ticket_id.trim());
  }

  return `/audit-logs?${params.toString()}`;
}

function AuditLogCard({ log }: { log: AuditLog }) {
  return (
    <div className="list-item">
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 16,
          alignItems: "flex-start",
        }}
      >
        <div>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Badge tone={getActionTone(log.action)}>{log.action}</Badge>
            <Badge tone="blue">{log.resource_type}</Badge>
          </div>

          <div style={{ marginTop: 10, fontWeight: 700 }}>
            {log.description || "Audit event recorded"}
          </div>

          <div className="muted" style={{ marginTop: 6 }}>
            {formatDateTime(log.created_at)}
          </div>
        </div>

        {log.ticket_id ? (
          <Link className="btn btn-secondary" href={`/tickets/${log.ticket_id}`}>
            Open Ticket
          </Link>
        ) : null}
      </div>

      <div className="grid grid-4" style={{ marginTop: 14 }}>
        <div>
          <div className="muted">Actor</div>
          <strong>{shortId(log.actor_user_id)}</strong>
        </div>

        <div>
          <div className="muted">Resource</div>
          <strong>{shortId(log.resource_id)}</strong>
        </div>

        <div>
          <div className="muted">Ticket</div>
          <strong>{shortId(log.ticket_id)}</strong>
        </div>

        <div>
          <div className="muted">Tool / Approval</div>
          <strong>
            {shortId(log.tool_execution_id || log.approval_request_id || log.reply_draft_id)}
          </strong>
        </div>
      </div>

      <details style={{ marginTop: 14 }}>
        <summary className="muted" style={{ cursor: "pointer" }}>
          Metadata
        </summary>

        <pre className="code" style={{ marginTop: 10 }}>
          {metadataPreview(log.metadata_json)}
        </pre>
      </details>
    </div>
  );
}

export function AuditLogsClient() {
  const { getToken, isSignedIn } = useAuth();

  const [orgId, setOrgId] = useState<string | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [bootLoading, setBootLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState<AuditFilters>({
    action: "",
    resource_type: "",
    ticket_id: "",
  });

  const tokenGetter = isSignedIn ? getToken : undefined;

  const ticketFilterWarning = useMemo(() => {
    if (!filters.ticket_id) return null;

    if (!isValidUuidLike(filters.ticket_id)) {
      return "Ticket ID filter must be a UUID. The filter will be ignored until it is valid.";
    }

    return null;
  }, [filters.ticket_id]);

  async function loadAuditLogs(currentOrgId: string) {
    if (!tokenGetter) return;

    try {
      setLoading(true);
      setError(null);

      const data = await apiFetch<AuditLogListResponse>(
        buildAuditQuery(filters),
        {
          method: "GET",
          orgId: currentOrgId,
          getToken: tokenGetter,
        }
      );

      setLogs(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  }

  async function loadBootstrap() {
    if (!isSignedIn || !tokenGetter) {
      setBootLoading(false);
      setLoading(false);
      return;
    }

    try {
      setBootLoading(true);
      setError(null);

      const boot = await bootstrapAuth(tokenGetter);
      setOrgId(boot.orgId);

      await loadAuditLogs(boot.orgId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit logs.");
    } finally {
      setBootLoading(false);
    }
  }

  useEffect(() => {
    loadBootstrap();
  }, [isSignedIn]);

  useEffect(() => {
    if (!orgId) return;
    loadAuditLogs(orgId);
  }, [filters.action, filters.resource_type]);

  return (
    <AppShell
      title="Audit Logs"
      subtitle="Organization-wide compliance trail for tickets, approvals, tools, replies, SLA, and agent actions."
      right={
        <div className="section">
          <div className="muted">Events</div>
          <strong>{total}</strong>

          <div style={{ marginTop: 10 }}>
            <button
              className="btn btn-secondary"
              disabled={loading || !orgId}
              onClick={() => orgId && loadAuditLogs(orgId)}
            >
              {loading ? "Refreshing..." : "Refresh Logs"}
            </button>
          </div>
        </div>
      }
    >
      <ErrorBanner message={error || ticketFilterWarning} />

      {bootLoading ? (
        <div className="section">Loading audit logs...</div>
      ) : (
        <>
          <Section
            title="Audit Filters"
            action={
              <button
                className="btn btn-secondary"
                onClick={() =>
                  setFilters({
                    action: "",
                    resource_type: "",
                    ticket_id: "",
                  })
                }
              >
                Clear Filters
              </button>
            }
          >
            <div className="grid grid-3">
              <div className="form-row">
                <label className="label">Action</label>
                <select
                  className="select"
                  value={filters.action}
                  onChange={(event) =>
                    setFilters((prev) => ({
                      ...prev,
                      action: event.target.value,
                    }))
                  }
                >
                  <option value="">All actions</option>
                  {ACTION_OPTIONS.map((action) => (
                    <option key={action} value={action}>
                      {action}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-row">
                <label className="label">Resource Type</label>
                <select
                  className="select"
                  value={filters.resource_type}
                  onChange={(event) =>
                    setFilters((prev) => ({
                      ...prev,
                      resource_type: event.target.value,
                    }))
                  }
                >
                  <option value="">All resources</option>
                  {RESOURCE_OPTIONS.map((resource) => (
                    <option key={resource} value={resource}>
                      {resource}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-row">
                <label className="label">Ticket ID</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <input
                    className="input"
                    value={filters.ticket_id}
                    placeholder="UUID only"
                    onChange={(event) =>
                      setFilters((prev) => ({
                        ...prev,
                        ticket_id: event.target.value,
                      }))
                    }
                  />

                  <button
                    className="btn btn-secondary"
                    disabled={loading || !orgId}
                    onClick={() => orgId && loadAuditLogs(orgId)}
                  >
                    Apply
                  </button>
                </div>
              </div>
            </div>
          </Section>

          <div style={{ marginTop: 16 }}>
            <Section title="Recent Audit Events">
              {loading ? <p className="muted">Loading events...</p> : null}

              <div className="list">
                {logs.map((log) => (
                  <AuditLogCard key={log.id} log={log} />
                ))}

                {!loading && logs.length === 0 ? (
                  <EmptyState message="No audit events found." />
                ) : null}
              </div>
            </Section>
          </div>
        </>
      )}
    </AppShell>
  );
}