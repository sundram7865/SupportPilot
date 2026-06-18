"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { CreateTicketForm } from "@/components/dashboard/CreateTicketForm";
import { DashboardStats } from "@/components/dashboard/DashboardStats";
import { TicketList } from "@/components/dashboard/TicketList";
import { apiFetch, bootstrapAuth } from "@/lib/api";
import { unwrapItems } from "@/lib/collections";
import type { AuthMeResponse, Ticket } from "@/types/api";

export function DashboardClient() {
  const [me, setMe] = useState<AuthMeResponse | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      setError(null);

      const boot = await bootstrapAuth();
      setMe(boot.me);
      setOrgId(boot.orgId);

      const data = await apiFetch<Ticket[] | { items?: Ticket[] }>("/tickets", {
        method: "GET",
        orgId: boot.orgId,
      });

      setTickets(unwrapItems(data));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <AppShell
      title="Dashboard"
      subtitle="Monitor tickets, create test cases, and open live support workspaces."
      right={
        <div className="section">
          <div className="muted">Current org</div>
          <strong>{orgId || "Loading..."}</strong>
        </div>
      }
    >
      <ErrorBanner message={error} />

      <DashboardStats tickets={tickets} />

      <div className="grid grid-main" style={{ marginTop: 16 }}>
        <CreateTicketForm
          orgId={orgId}
          onCreated={(ticket) => setTickets((current) => [ticket, ...current])}
        />

        <TicketList tickets={tickets} />
      </div>

      {me ? (
        <div className="section" style={{ marginTop: 16 }}>
          <div className="section-title">Dev User</div>
          <pre className="code">{JSON.stringify(me.user, null, 2)}</pre>
        </div>
      ) : null}
    </AppShell>
  );
}