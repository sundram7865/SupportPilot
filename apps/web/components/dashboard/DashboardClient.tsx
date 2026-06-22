"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { CreateTicketForm } from "@/components/dashboard/CreateTicketForm";
import { DashboardStats } from "@/components/dashboard/DashboardStats";
import { TicketList } from "@/components/dashboard/TicketList";
import { AppShell } from "@/components/layout/AppShell";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { useTickets, type TicketListFilters } from "@/hooks/useTicketQueries";
import { bootstrapAuth } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import type { AuthMeResponse } from "@/types/api";

export function DashboardClient() {
  const { getToken, isSignedIn } = useAuth();
  const queryClient = useQueryClient();

  const [me, setMe] = useState<AuthMeResponse | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [bootLoading, setBootLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filters, setFilters] = useState<TicketListFilters>({
    status: "",
    priority: "",
    category: "",
    search: "",
  });

  const tokenGetter = isSignedIn ? getToken : undefined;

  const ticketsQuery = useTickets({
    orgId,
    getToken: tokenGetter,
    enabled: Boolean(isSignedIn && orgId && tokenGetter),
    filters,
  });

  const tickets = useMemo(() => ticketsQuery.data || [], [ticketsQuery.data]);

  async function loadBootstrap() {
    if (!isSignedIn || !tokenGetter) {
      setBootLoading(false);
      return;
    }

    try {
      setBootLoading(true);
      setError(null);

      const boot = await bootstrapAuth(tokenGetter);

      setMe(boot.me);
      setOrgId(boot.orgId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard.");
    } finally {
      setBootLoading(false);
    }
  }

  async function refreshTickets() {
    await queryClient.invalidateQueries({
      queryKey: queryKeys.tickets.all,
    });
  }

  useEffect(() => {
    loadBootstrap();
  }, [isSignedIn]);

  const combinedError =
    error ||
    (ticketsQuery.error instanceof Error ? ticketsQuery.error.message : null);

  return (
    <AppShell
      title="Dashboard"
      subtitle="Monitor tickets from admin form, public form, widget, and external API."
      right={
        <div className="section">
          <div className="muted">Current org</div>
          <strong>{orgId || "Loading..."}</strong>

          <div style={{ marginTop: 10 }}>
            <button
              className="btn btn-secondary"
              onClick={refreshTickets}
              disabled={ticketsQuery.isFetching || !orgId}
            >
              {ticketsQuery.isFetching ? "Refreshing..." : "Refresh Tickets"}
            </button>
          </div>
        </div>
      }
    >
      <ErrorBanner message={combinedError} />

      {bootLoading ? (
        <div className="section">Loading dashboard...</div>
      ) : (
        <>
          <DashboardStats tickets={tickets} />

          <div className="section" style={{ marginTop: 16 }}>
            <div className="section-title">Ticket Filters</div>

            <div className="grid grid-4">
              <div className="form-row">
                <label className="label">Search</label>
                <input
                  className="input"
                  value={filters.search || ""}
                  placeholder="ticket, email, subject..."
                  onChange={(event) =>
                    setFilters((prev) => ({
                      ...prev,
                      search: event.target.value,
                    }))
                  }
                />
              </div>

              <div className="form-row">
                <label className="label">Status</label>
                <select
                  className="select"
                  value={filters.status || ""}
                  onChange={(event) =>
                    setFilters((prev) => ({
                      ...prev,
                      status: event.target.value,
                    }))
                  }
                >
                  <option value="">All</option>
                  <option value="OPEN">OPEN</option>
                  <option value="IN_PROGRESS">IN_PROGRESS</option>
                  <option value="WAITING_FOR_CUSTOMER">
                    WAITING_FOR_CUSTOMER
                  </option>
                  <option value="WAITING_FOR_INTERNAL_REVIEW">
                    WAITING_FOR_INTERNAL_REVIEW
                  </option>
                  <option value="RESOLVED">RESOLVED</option>
                  <option value="CLOSED">CLOSED</option>
                </select>
              </div>

              <div className="form-row">
                <label className="label">Priority</label>
                <select
                  className="select"
                  value={filters.priority || ""}
                  onChange={(event) =>
                    setFilters((prev) => ({
                      ...prev,
                      priority: event.target.value,
                    }))
                  }
                >
                  <option value="">All</option>
                  <option value="LOW">LOW</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="HIGH">HIGH</option>
                  <option value="URGENT">URGENT</option>
                </select>
              </div>

              <div className="form-row">
                <label className="label">Category</label>
                <select
                  className="select"
                  value={filters.category || ""}
                  onChange={(event) =>
                    setFilters((prev) => ({
                      ...prev,
                      category: event.target.value,
                    }))
                  }
                >
                  <option value="">All</option>
                  <option value="ORDER_STATUS">ORDER_STATUS</option>
                  <option value="PAYMENT_ISSUE">PAYMENT_ISSUE</option>
                  <option value="REFUND_REQUEST">REFUND_REQUEST</option>
                  <option value="RETURN_REQUEST">RETURN_REQUEST</option>
                  <option value="DAMAGED_PRODUCT">DAMAGED_PRODUCT</option>
                  <option value="CANCEL_ORDER">CANCEL_ORDER</option>
                  <option value="INVOICE_REQUEST">INVOICE_REQUEST</option>
                  <option value="WARRANTY_REQUEST">WARRANTY_REQUEST</option>
                  <option value="GENERAL_FAQ">GENERAL_FAQ</option>
                  <option value="LEGAL_RISK">LEGAL_RISK</option>
                  <option value="OTHER">OTHER</option>
                </select>
              </div>
            </div>
          </div>

          <div className="grid grid-main" style={{ marginTop: 16 }}>
            <CreateTicketForm orgId={orgId} />

            <TicketList
              tickets={tickets}
              loading={ticketsQuery.isLoading || ticketsQuery.isFetching}
            />
          </div>

          {me ? (
            <div className="section" style={{ marginTop: 16 }}>
              <div className="section-title">Current User</div>
              <pre className="code">{JSON.stringify(me.user, null, 2)}</pre>
            </div>
          ) : null}
        </>
      )}
    </AppShell>
  );
}