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
import { apiFetch, bootstrapAuth } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import type { AnalyticsOverview, AuthMeResponse } from "@/types/api";

export function DashboardClient() {
  const { getToken, isSignedIn } = useAuth();
  const queryClient = useQueryClient();

  const [me, setMe] = useState<AuthMeResponse | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [bootLoading, setBootLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);

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

  async function loadAnalytics(currentOrgId: string) {
    if (!tokenGetter) return;

    try {
      setAnalyticsLoading(true);
      setAnalyticsError(null);

      const data = await apiFetch<AnalyticsOverview>("/analytics/overview", {
        method: "GET",
        orgId: currentOrgId,
        getToken: tokenGetter,
      });

      setAnalytics(data);
    } catch (err) {
      setAnalyticsError(
        err instanceof Error ? err.message : "Failed to load analytics."
      );
    } finally {
      setAnalyticsLoading(false);
    }
  }

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

      await loadAnalytics(boot.orgId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard.");
    } finally {
      setBootLoading(false);
    }
  }

  async function refreshDashboard() {
    if (!orgId) return;

    await queryClient.invalidateQueries({
      queryKey: queryKeys.tickets.all,
    });

    await loadAnalytics(orgId);
  }

  useEffect(() => {
    loadBootstrap();
  }, [isSignedIn]);

  const combinedError =
    error ||
    analyticsError ||
    (ticketsQuery.error instanceof Error ? ticketsQuery.error.message : null);

  return (
    <AppShell
      title="Dashboard"
      subtitle="Live support operations, SLA health, AI automation, approvals, and customer reply delivery."
      right={
        <div className="section">
          <div className="muted">Current org</div>
          <strong>{orgId || "Loading..."}</strong>

          <div style={{ marginTop: 10 }}>
            <button
              className="btn btn-secondary"
              onClick={refreshDashboard}
              disabled={ticketsQuery.isFetching || analyticsLoading || !orgId}
            >
              {ticketsQuery.isFetching || analyticsLoading
                ? "Refreshing..."
                : "Refresh Dashboard"}
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
          <DashboardStats
            tickets={tickets}
            analytics={analytics}
            loading={analyticsLoading}
          />

          <div className="section" style={{ marginTop: 16 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 16,
                alignItems: "center",
                marginBottom: 12,
              }}
            >
              <div>
                <div className="section-title">Ticket Filters</div>
                <p className="muted" style={{ marginTop: 4 }}>
                  Filter the live ticket list without changing organization-wide
                  analytics above.
                </p>
              </div>

              <button
                className="btn btn-secondary"
                onClick={() =>
                  setFilters({
                    status: "",
                    priority: "",
                    category: "",
                    search: "",
                  })
                }
              >
                Clear Filters
              </button>
            </div>

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
                  <option value="RETURN_REPLACEMENT">RETURN_REPLACEMENT</option>
                  <option value="PRODUCT_QUESTION">PRODUCT_QUESTION</option>
                  <option value="DELIVERY_ISSUE">DELIVERY_ISSUE</option>
                  <option value="ACCOUNT_ISSUE">ACCOUNT_ISSUE</option>
                  <option value="COMPLAINT">COMPLAINT</option>
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