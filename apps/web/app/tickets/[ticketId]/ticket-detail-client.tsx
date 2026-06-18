"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { apiFetch } from "@/lib/api";
import { streamTicketTimeline } from "@/lib/sse";
import type {
  AgentRun,
  ApprovalRequest,
  ReplyDraft,
  Ticket,
  TimelineEvent,
  ToolExecution,
} from "@/types/api";

type TimelineResponse = TimelineEvent[] | { items: TimelineEvent[] };
type ToolListResponse = { items: ToolExecution[]; total: number };
type ApprovalListResponse = { items: ApprovalRequest[]; total: number };
type DraftListResponse = { items: ReplyDraft[]; total: number };

export default function TicketDetailClient({ ticketId }: { ticketId: string }) {
  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [tools, setTools] = useState<ToolExecution[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [drafts, setDrafts] = useState<ReplyDraft[]>([]);
  const [latestAgentRun, setLatestAgentRun] = useState<AgentRun | null>(null);

  const [messageBody, setMessageBody] = useState("Can you give me an update?");
  const [draftBody, setDraftBody] = useState(
    "Hi, thanks for contacting UrbanKart support. We are checking your request and will update you shortly."
  );

  const [sseStatus, setSseStatus] = useState("connecting");
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const orderId = useMemo(() => {
    return ticket?.external_order_id || "ORD-1001";
  }, [ticket]);

  async function loadAll() {
    try {
      setError(null);

      const [ticketData, timelineData, toolData, approvalData, draftData] =
        await Promise.all([
          apiFetch<Ticket>(`/tickets/${ticketId}`),
          apiFetch<TimelineResponse>(`/tickets/${ticketId}/timeline`),
          apiFetch<ToolListResponse>(`/tools/tickets/${ticketId}/executions`),
          apiFetch<ApprovalListResponse>(`/approvals/tickets/${ticketId}`),
          apiFetch<DraftListResponse>(`/replies/tickets/${ticketId}/drafts`),
        ]);

      setTicket(ticketData);

      const timelineItems = Array.isArray(timelineData)
        ? timelineData
        : timelineData.items || [];

      setTimeline(timelineItems);
      setTools(toolData.items || []);
      setApprovals(approvalData.items || []);
      setDrafts(draftData.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load ticket");
    } finally {
      setLoading(false);
    }
  }

  async function addCustomerMessage() {
    await runAction("Adding message...", async () => {
      await apiFetch(`/tickets/${ticketId}/messages`, {
        method: "POST",
        body: JSON.stringify({
          body: messageBody,
          sender_type: "CUSTOMER",
        }),
      });

      await loadAll();
    });
  }

  async function runAgent() {
    await runAction("Running agent...", async () => {
      const run = await apiFetch<AgentRun>(`/agent/tickets/${ticketId}/run`, {
        method: "POST",
        body: JSON.stringify({
          force: true,
          notes: "Run from Phase 12 frontend",
        }),
      });

      setLatestAgentRun(run);
      await loadAll();
    });
  }

  async function executeSafeTools() {
    if (!latestAgentRun?.id) {
      setError("Run agent first, then execute safe tools.");
      return;
    }

    await runAction("Executing safe tools...", async () => {
      await apiFetch(`/tools/agent-runs/${latestAgentRun.id}/execute-safe`, {
        method: "POST",
        body: JSON.stringify({
          execute_read_only_only: true,
        }),
      });

      await loadAll();
    });
  }

  async function executeOrderTool() {
    await runAction("Executing order context tool...", async () => {
      await apiFetch<ToolExecution>("/tools/execute", {
        method: "POST",
        body: JSON.stringify({
          tool_name: "urbankart_get_order_context",
          ticket_id: ticketId,
          agent_run_id: null,
          args: {
            order_id: orderId,
          },
          idempotency_key: `frontend-order-context-${orderId}-${Date.now()}`,
        }),
      });

      await loadAll();
    });
  }

  async function executeRefundTool() {
    await runAction("Creating blocked refund tool...", async () => {
      await apiFetch<ToolExecution>("/tools/execute", {
        method: "POST",
        body: JSON.stringify({
          tool_name: "urbankart_request_refund",
          ticket_id: ticketId,
          agent_run_id: null,
          args: {
            order_id: orderId,
            amount: 1499,
            reason: "Frontend refund approval test.",
          },
          idempotency_key: `frontend-refund-${orderId}-${Date.now()}`,
        }),
      });

      await loadAll();
    });
  }

  async function requestApproval(executionId: string) {
    await runAction("Requesting approval...", async () => {
      await apiFetch(`/approvals/tool-executions/${executionId}/request`, {
        method: "POST",
        body: JSON.stringify({
          request_reason: "Frontend requested approval for risky tool.",
          metadata_json: {
            source: "phase12-frontend",
          },
        }),
      });

      await loadAll();
    });
  }

  async function approveApproval(approvalId: string) {
    await runAction("Approving...", async () => {
      await apiFetch(`/approvals/${approvalId}/approve`, {
        method: "POST",
        body: JSON.stringify({
          decision_reason: "Approved from Phase 12 frontend.",
        }),
      });

      await loadAll();
    });
  }

  async function rejectApproval(approvalId: string) {
    await runAction("Rejecting...", async () => {
      await apiFetch(`/approvals/${approvalId}/reject`, {
        method: "POST",
        body: JSON.stringify({
          decision_reason: "Rejected from Phase 12 frontend.",
        }),
      });

      await loadAll();
    });
  }

  async function createDraft() {
    await runAction("Creating draft...", async () => {
      await apiFetch<ReplyDraft>("/replies/drafts", {
        method: "POST",
        body: JSON.stringify({
          ticket_id: ticketId,
          subject: "Support update",
          body: draftBody,
          source: "AGENT",
          metadata_json: {
            source: "phase12-frontend",
          },
        }),
      });

      await loadAll();
    });
  }

  async function createDraftFromAgent() {
    if (!latestAgentRun?.id) {
      setError("Run agent first, then create AI draft.");
      return;
    }

    await runAction("Creating AI draft...", async () => {
      await apiFetch(
        `/replies/tickets/${ticketId}/draft-from-agent-run/${latestAgentRun.id}`,
        {
          method: "POST",
        }
      );

      await loadAll();
    });
  }

  async function submitDraft(draftId: string) {
    await runAction("Submitting draft...", async () => {
      await apiFetch(`/replies/drafts/${draftId}/submit-approval`, {
        method: "POST",
        body: JSON.stringify({
          request_reason: "Please review this customer reply.",
        }),
      });

      await loadAll();
    });
  }

  async function approveDraft(draftId: string) {
    await runAction("Approving draft...", async () => {
      await apiFetch(`/replies/drafts/${draftId}/approve`, {
        method: "POST",
        body: JSON.stringify({
          reason: "Reply approved.",
        }),
      });

      await loadAll();
    });
  }

  async function sendDraft(draftId: string) {
    await runAction("Sending draft...", async () => {
      await apiFetch(`/replies/drafts/${draftId}/send`, {
        method: "POST",
        body: JSON.stringify({
          send_notes: "Sent from Phase 12 frontend.",
        }),
      });

      await loadAll();
    });
  }

  async function runAction(label: string, fn: () => Promise<void>) {
    try {
      setWorking(label);
      setError(null);
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setWorking(null);
    }
  }

  useEffect(() => {
    loadAll();
  }, [ticketId]);

  useEffect(() => {
    const controller = new AbortController();

    setSseStatus("connecting");

    streamTicketTimeline({
      ticketId,
      signal: controller.signal,
      onEvent(payload) {
        if (payload.type === "connected") {
          setSseStatus("connected");
          return;
        }

        if (payload.type === "timeline_event" && payload.event) {
          setTimeline((current) => {
            const exists = current.some((item) => item.id === payload.event.id);
            if (exists) return current;
            return [...current, payload.event];
          });

          if (
            [
              "TOOL_EXECUTION_COMPLETED",
              "TOOL_EXECUTION_BLOCKED",
              "APPROVAL_REQUEST_CREATED",
              "APPROVAL_REQUEST_APPROVED",
              "APPROVAL_REQUEST_REJECTED",
              "REPLY_DRAFT_CREATED",
              "CUSTOMER_REPLY_SENT",
            ].includes(payload.event.event_type)
          ) {
            loadAll();
          }
        }
      },
      onError() {
        setSseStatus("error");
      },
    });

    return () => {
      controller.abort();
    };
  }, [ticketId]);

  if (loading) {
    return (
      <main className="page">
        <div className="container">
          <div className="muted">Loading ticket...</div>
        </div>
      </main>
    );
  }

  return (
    <main className="page">
      <div className="container">
        <div className="header">
          <div>
            <Link href="/dashboard" className="muted">
              ← Back to dashboard
            </Link>
            <div className="logo">{ticket?.ticket_number || "Ticket"}</div>
            <div className="muted">{ticket?.subject}</div>
          </div>

          <div className="card">
            <div className="muted">Realtime</div>
            <span
              className={
                sseStatus === "connected"
                  ? "badge badge-green"
                  : sseStatus === "error"
                    ? "badge badge-red"
                    : "badge badge-yellow"
              }
            >
              {sseStatus}
            </span>
          </div>
        </div>

        {error ? <div className="error">{error}</div> : null}
        {working ? <div className="success">{working}</div> : null}

        <section className="card" style={{ marginTop: 16 }}>
          <div className="card-title">Ticket Summary</div>
          <div className="grid grid-3">
            <div>
              <div className="muted">Status</div>
              <strong>{ticket?.status}</strong>
            </div>
            <div>
              <div className="muted">Priority</div>
              <strong>{ticket?.priority}</strong>
            </div>
            <div>
              <div className="muted">Category</div>
              <strong>{ticket?.category}</strong>
            </div>
          </div>

          <div style={{ marginTop: 14 }}>
            <div className="muted">Customer</div>
            <strong>{ticket?.customer_name || "Unknown"}</strong>{" "}
            <span className="muted">{ticket?.customer_email}</span>
          </div>

          <div style={{ marginTop: 14 }}>
            <div className="muted">Order</div>
            <strong>{orderId}</strong>
          </div>
        </section>

        <div className="grid grid-2" style={{ marginTop: 16 }}>
          <section className="card">
            <div className="card-title">Actions</div>

            <div className="btn-row">
              <button className="btn" onClick={runAgent}>
                Run Agent
              </button>
              <button className="btn btn-secondary" onClick={executeSafeTools}>
                Execute Agent Tools
              </button>
              <button className="btn btn-secondary" onClick={executeOrderTool}>
                Get Order Context
              </button>
              <button className="btn btn-danger" onClick={executeRefundTool}>
                Request Refund
              </button>
            </div>

            {latestAgentRun ? (
              <div style={{ marginTop: 16 }}>
                <div className="card-title">Latest Agent Run</div>
                <pre className="code">
                  {JSON.stringify(latestAgentRun, null, 2)}
                </pre>
              </div>
            ) : null}
          </section>

          <section className="card">
            <div className="card-title">Add Customer Message</div>

            <div className="form-row">
              <textarea
                className="textarea"
                value={messageBody}
                onChange={(e) => setMessageBody(e.target.value)}
              />
            </div>

            <button className="btn" onClick={addCustomerMessage}>
              Add Message
            </button>
          </section>
        </div>

        <div className="grid grid-2" style={{ marginTop: 16 }}>
          <section className="card">
            <div className="card-title">Timeline</div>

            <div className="timeline">
              {timeline.map((event) => (
                <div key={event.id} className="timeline-item">
                  <strong>{event.event_type}</strong>
                  <div>{event.title}</div>
                  {event.description ? (
                    <div className="muted">{event.description}</div>
                  ) : null}
                  <div className="muted">
                    {new Date(event.created_at).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="card-title">Tool Executions</div>

            <div className="list">
              {tools.map((tool) => (
                <div key={tool.id} className="list-item">
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <strong>{tool.tool_name}</strong>
                    <span className="badge">{tool.status}</span>
                  </div>
                  <div className="muted">
                    {tool.risk_level} · approval: {tool.approval_status}
                  </div>

                  {tool.status === "BLOCKED_APPROVAL_REQUIRED" &&
                  tool.approval_status === "PENDING" ? (
                    <button
                      className="btn"
                      style={{ marginTop: 10 }}
                      onClick={() => requestApproval(tool.id)}
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

              {tools.length === 0 ? (
                <div className="muted">No tool executions yet.</div>
              ) : null}
            </div>
          </section>
        </div>

        <div className="grid grid-2" style={{ marginTop: 16 }}>
          <section className="card">
            <div className="card-title">Approvals</div>

            <div className="list">
              {approvals.map((approval) => (
                <div key={approval.id} className="list-item">
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <strong>{approval.title}</strong>
                    <span className="badge">{approval.status}</span>
                  </div>

                  <div className="muted">
                    {approval.tool_name || "Customer reply"} ·{" "}
                    {approval.risk_level}
                  </div>

                  {approval.status === "PENDING" ? (
                    <div className="btn-row" style={{ marginTop: 10 }}>
                      <button
                        className="btn btn-success"
                        onClick={() => approveApproval(approval.id)}
                      >
                        Approve
                      </button>
                      <button
                        className="btn btn-danger"
                        onClick={() => rejectApproval(approval.id)}
                      >
                        Reject
                      </button>
                    </div>
                  ) : null}
                </div>
              ))}

              {approvals.length === 0 ? (
                <div className="muted">No approvals yet.</div>
              ) : null}
            </div>
          </section>

          <section className="card">
            <div className="card-title">Reply Drafts</div>

            <div className="form-row">
              <label className="label">New draft body</label>
              <textarea
                className="textarea"
                value={draftBody}
                onChange={(e) => setDraftBody(e.target.value)}
              />
            </div>

            <div className="btn-row">
              <button className="btn" onClick={createDraft}>
                Create Draft
              </button>
              <button className="btn btn-secondary" onClick={createDraftFromAgent}>
                Create AI Draft
              </button>
            </div>

            <div className="list" style={{ marginTop: 16 }}>
              {drafts.map((draft) => (
                <div key={draft.id} className="list-item">
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <strong>{draft.subject || "Reply draft"}</strong>
                    <span className="badge">{draft.status}</span>
                  </div>

                  <div className="muted">{draft.source}</div>
                  <div style={{ marginTop: 8 }}>{draft.body}</div>

                  <div className="btn-row" style={{ marginTop: 10 }}>
                    {draft.status === "DRAFT" ? (
                      <>
                        <button
                          className="btn btn-secondary"
                          onClick={() => submitDraft(draft.id)}
                        >
                          Submit Approval
                        </button>
                        <button
                          className="btn"
                          onClick={() => sendDraft(draft.id)}
                        >
                          Send Direct
                        </button>
                      </>
                    ) : null}

                    {draft.status === "PENDING_APPROVAL" ? (
                      <button
                        className="btn btn-success"
                        onClick={() => approveDraft(draft.id)}
                      >
                        Approve Draft
                      </button>
                    ) : null}

                    {draft.status === "APPROVED" ? (
                      <button className="btn" onClick={() => sendDraft(draft.id)}>
                        Send
                      </button>
                    ) : null}
                  </div>
                </div>
              ))}

              {drafts.length === 0 ? (
                <div className="muted">No reply drafts yet.</div>
              ) : null}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}