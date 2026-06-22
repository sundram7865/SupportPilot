"use client";

import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useCallback, useEffect, useMemo, useState } from "react";

import { AgentRunSummaryPanel } from "@/components/ticket/AgentRunSummaryPanel";
import { ApprovalPanel } from "@/components/ticket/ApprovalPanel";
import { CustomerMessagePanel } from "@/components/ticket/CustomerMessagePanel";
import { KnowledgeContextPanel } from "@/components/ticket/KnowledgeContextPanel";
import { PlannedToolsPanel } from "@/components/ticket/PlannedToolsPanel";
import { ReplyDraftPanel } from "@/components/ticket/ReplyDraftPanel";
import { TicketActionsPanel } from "@/components/ticket/TicketActionsPanel";
import { TicketSummary } from "@/components/ticket/TicketSummary";
import { TimelinePanel } from "@/components/ticket/TimelinePanel";
import { ToolExecutionPanel } from "@/components/ticket/ToolExecutionPanel";
import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { apiFetch } from "@/lib/api";
import { unwrapItems } from "@/lib/collections";
import { streamTicketTimeline } from "@/lib/sse";
import type {
  AgentRun,
  ApprovalRequest,
  ReplyDraft,
  Ticket,
  TimelineEvent,
  ToolExecution,
} from "@/types/api";

export function TicketWorkspace({ ticketId }: { ticketId: string }) {
  const { getToken, isSignedIn } = useAuth();

  const [ticket, setTicket] = useState<Ticket | null>(null);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [tools, setTools] = useState<ToolExecution[]>([]);
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [drafts, setDrafts] = useState<ReplyDraft[]>([]);
  const [latestAgentRun, setLatestAgentRun] = useState<AgentRun | null>(null);

  const [sseStatus, setSseStatus] = useState("connecting");
  const [error, setError] = useState<string | null>(null);
  const [working, setWorking] = useState<string | null>(null);

  const tokenGetter = isSignedIn ? getToken : undefined;

  const orderId = useMemo(() => {
    return ticket?.external_order_id || "ORD-1001";
  }, [ticket]);

  const plannedTools = useMemo(() => {
    return latestAgentRun?.planned_tools || [];
  }, [latestAgentRun]);

  const retrievedContext = useMemo(() => {
    return latestAgentRun?.retrieved_context || [];
  }, [latestAgentRun]);

  const loadAll = useCallback(async () => {
    if (!tokenGetter) {
      return;
    }

    const [
      ticketData,
      timelineData,
      toolData,
      approvalData,
      draftData,
      agentRunsData,
    ] = await Promise.all([
      apiFetch<Ticket>(`/tickets/${ticketId}`, {
        getToken: tokenGetter,
      }),

      apiFetch<TimelineEvent[] | { items?: TimelineEvent[] }>(
        `/tickets/${ticketId}/timeline`,
        {
          getToken: tokenGetter,
        }
      ),

      apiFetch<{ items?: ToolExecution[] }>(
        `/tools/tickets/${ticketId}/executions`,
        {
          getToken: tokenGetter,
        }
      ),

      apiFetch<{ items?: ApprovalRequest[] }>(
        `/approvals/tickets/${ticketId}`,
        {
          getToken: tokenGetter,
        }
      ),

      apiFetch<{ items?: ReplyDraft[] }>(
        `/replies/tickets/${ticketId}/drafts`,
        {
          getToken: tokenGetter,
        }
      ),

      apiFetch<{ items?: AgentRun[] }>(`/agent/tickets/${ticketId}/runs`, {
        getToken: tokenGetter,
      }),
    ]);

    setTicket(ticketData);
    setTimeline(unwrapItems(timelineData));
    setTools(unwrapItems(toolData));
    setApprovals(unwrapItems(approvalData));
    setDrafts(unwrapItems(draftData));

    const latestRunItem = unwrapItems(agentRunsData)[0];

    if (latestRunItem?.id) {
      const fullRun = await apiFetch<AgentRun>(`/agent/runs/${latestRunItem.id}`, {
        getToken: tokenGetter,
      });

      setLatestAgentRun(fullRun);
    } else {
      setLatestAgentRun(null);
    }
  }, [ticketId, tokenGetter]);

  async function runAction(label: string, fn: () => Promise<void>) {
    if (!tokenGetter) {
      setError("Missing Clerk token. Please refresh and sign in again.");
      return;
    }

    try {
      setWorking(label);
      setError(null);
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed.");
    } finally {
      setWorking(null);
    }
  }

  useEffect(() => {
    if (!tokenGetter) return;

    runAction("Loading ticket...", loadAll);
  }, [tokenGetter, loadAll]);

  useEffect(() => {
    if (!tokenGetter) return;

    const controller = new AbortController();

    streamTicketTimeline({
      ticketId,
      getToken: tokenGetter,
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

          loadAll();
        }
      },
      onError() {
        setSseStatus("error");
      },
    });

    return () => controller.abort();
  }, [ticketId, tokenGetter, loadAll]);

  return (
    <AppShell
      title={ticket?.ticket_number || "Ticket Workspace"}
      subtitle={ticket?.subject || "Live support workflow"}
      right={
        <div className="section">
          <Link href="/dashboard" className="muted">
            ← Dashboard
          </Link>

          <div style={{ marginTop: 10 }}>
            <Badge tone={sseStatus === "connected" ? "green" : "yellow"}>
              Realtime: {sseStatus}
            </Badge>
          </div>

          <div style={{ marginTop: 10 }}>
            <button
              className="btn btn-secondary"
              onClick={() => runAction("Refreshing...", loadAll)}
              disabled={Boolean(working)}
            >
              Refresh
            </button>
          </div>
        </div>
      }
    >
      <ErrorBanner message={error} />
      {working ? <div className="success">{working}</div> : null}

      <TicketSummary ticket={ticket} />

      <div className="grid grid-main" style={{ marginTop: 16 }}>
        <div className="grid">
          <TicketActionsPanel
            ticket={ticket}
            latestAgentRun={latestAgentRun}
            onRunAgent={() =>
              runAction("Running agent...", async () => {
                const run = await apiFetch<AgentRun>(
                  `/agent/tickets/${ticketId}/run`,
                  {
                    method: "POST",
                    getToken: tokenGetter,
                    body: JSON.stringify({
                      force: true,
                      notes: "Run from SupportPilot ticket workspace.",
                    }),
                  }
                );

                setLatestAgentRun(run);
                await loadAll();
              })
            }
            onExecuteAgentTools={() =>
              runAction("Executing agent tools...", async () => {
                if (!latestAgentRun?.id) {
                  throw new Error("Run agent first.");
                }

                await apiFetch(`/tools/agent-runs/${latestAgentRun.id}/execute-safe`, {
                  method: "POST",
                  getToken: tokenGetter,
                  body: JSON.stringify({
                    execute_read_only_only: true,
                  }),
                });

                await loadAll();
              })
            }
            onOrderTool={() =>
              runAction("Getting order context...", async () => {
                await apiFetch("/tools/execute", {
                  method: "POST",
                  getToken: tokenGetter,
                  body: JSON.stringify({
                    tool_name: "urbankart_get_order_context",
                    ticket_id: ticketId,
                    agent_run_id: latestAgentRun?.id || null,
                    args: {
                      order_id: orderId,
                    },
                    idempotency_key: `frontend-order-${ticketId}-${Date.now()}`,
                  }),
                });

                await loadAll();
              })
            }
            onRefundTool={() =>
              runAction("Creating refund approval...", async () => {
                await apiFetch("/tools/execute", {
                  method: "POST",
                  getToken: tokenGetter,
                  body: JSON.stringify({
                    tool_name: "urbankart_request_refund",
                    ticket_id: ticketId,
                    agent_run_id: latestAgentRun?.id || null,
                    args: {
                      order_id: orderId,
                      amount: 1499,
                      reason: "Frontend refund approval test.",
                    },
                    idempotency_key: `frontend-refund-${ticketId}-${Date.now()}`,
                  }),
                });

                await loadAll();
              })
            }
          />

          <AgentRunSummaryPanel latestAgentRun={latestAgentRun} />

          <PlannedToolsPanel plannedTools={plannedTools} />

          <KnowledgeContextPanel retrievedContext={retrievedContext} />

          <TimelinePanel timeline={timeline} />
        </div>

        <div className="grid">
          <CustomerMessagePanel
            onAdd={(body) =>
              runAction("Adding message...", async () => {
                await apiFetch(`/tickets/${ticketId}/messages`, {
                  method: "POST",
                  getToken: tokenGetter,
                  body: JSON.stringify({
                    body,
                    sender_type: "CUSTOMER",
                  }),
                });

                await loadAll();
              })
            }
          />

          <ToolExecutionPanel
            tools={tools}
            onRequestApproval={(executionId) =>
              runAction("Requesting approval...", async () => {
                await apiFetch(`/approvals/tool-executions/${executionId}/request`, {
                  method: "POST",
                  getToken: tokenGetter,
                  body: JSON.stringify({
                    request_reason: "Requested from ticket workspace.",
                  }),
                });

                await loadAll();
              })
            }
          />

          <ApprovalPanel
            approvals={approvals}
            onApprove={(approvalId) =>
              runAction("Approving...", async () => {
                await apiFetch(`/approvals/${approvalId}/approve`, {
                  method: "POST",
                  getToken: tokenGetter,
                  body: JSON.stringify({
                    decision_reason: "Approved from ticket workspace.",
                  }),
                });

                await loadAll();
              })
            }
            onReject={(approvalId) =>
              runAction("Rejecting...", async () => {
                await apiFetch(`/approvals/${approvalId}/reject`, {
                  method: "POST",
                  getToken: tokenGetter,
                  body: JSON.stringify({
                    decision_reason: "Rejected from ticket workspace.",
                  }),
                });

                await loadAll();
              })
            }
          />

          <ReplyDraftPanel
            drafts={drafts}
            onCreate={(body) =>
              runAction("Creating draft...", async () => {
                await apiFetch("/replies/drafts", {
                  method: "POST",
                  getToken: tokenGetter,
                  body: JSON.stringify({
                    ticket_id: ticketId,
                    subject: "Support update",
                    body,
                    source: "AGENT",
                  }),
                });

                await loadAll();
              })
            }
            onCreateFromAgent={() =>
              runAction("Creating AI draft...", async () => {
                if (!latestAgentRun?.id) {
                  throw new Error("Run agent first.");
                }

                await apiFetch(
                  `/replies/tickets/${ticketId}/draft-from-agent-run/${latestAgentRun.id}`,
                  {
                    method: "POST",
                    getToken: tokenGetter,
                  }
                );

                await loadAll();
              })
            }
            onSubmit={(draftId) =>
              runAction("Submitting draft...", async () => {
                await apiFetch(`/replies/drafts/${draftId}/submit-approval`, {
                  method: "POST",
                  getToken: tokenGetter,
                  body: JSON.stringify({
                    request_reason: "Please review this customer reply.",
                  }),
                });

                await loadAll();
              })
            }
            onApprove={(draftId) =>
              runAction("Approving draft...", async () => {
                await apiFetch(`/replies/drafts/${draftId}/approve`, {
                  method: "POST",
                  getToken: tokenGetter,
                  body: JSON.stringify({
                    reason: "Reply approved.",
                  }),
                });

                await loadAll();
              })
            }
            onSend={(draftId) =>
              runAction("Sending draft...", async () => {
                await apiFetch(`/replies/drafts/${draftId}/send`, {
                  method: "POST",
                  getToken: tokenGetter,
                  body: JSON.stringify({
                    send_notes: "Sent from ticket workspace.",
                  }),
                });

                await loadAll();
              })
            }
          />
        </div>
      </div>
    </AppShell>
  );
}