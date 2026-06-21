"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";

import { ExternalApiLogsTable } from "@/components/integrations/ExternalApiLogsTable";
import { UrbanKartConnectionCard } from "@/components/integrations/UrbanKartConnectionCard";
import { AppShell } from "@/components/layout/AppShell";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingState } from "@/components/ui/LoadingState";
import { Section } from "@/components/ui/Section";
import { apiFetch, bootstrapAuth } from "@/lib/api";
import type {
  AuthMeResponse,
  ExternalApiLog,
  IntegrationConnection,
} from "@/types/api";

export function IntegrationSettingsClient() {
  const { getToken, isSignedIn } = useAuth();

  const [me, setMe] = useState<AuthMeResponse | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [connection, setConnection] = useState<IntegrationConnection | null>(
    null
  );
  const [logs, setLogs] = useState<ExternalApiLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const tokenGetter = isSignedIn ? getToken : undefined;

  async function load() {
    if (!tokenGetter) return;

    try {
      setLoading(true);
      setError(null);

      const boot = await bootstrapAuth(tokenGetter);
      setMe(boot.me);
      setOrgId(boot.orgId);

      const [connectionResponse, logsResponse] = await Promise.allSettled([
        apiFetch<IntegrationConnection>("/integrations/urbankart", {
          method: "GET",
          getToken: tokenGetter,
        }),
        apiFetch<ExternalApiLog[]>("/integrations/logs", {
          method: "GET",
          getToken: tokenGetter,
        }),
      ]);

      if (connectionResponse.status === "fulfilled") {
        setConnection(connectionResponse.value);
      } else {
        setConnection(null);
      }

      if (logsResponse.status === "fulfilled") {
        setLogs(logsResponse.value);
      } else {
        setLogs([]);
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load integrations."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [isSignedIn]);

  return (
    <AppShell
      title="Integration Settings"
      subtitle="Connect store APIs, test health, and inspect external API logs."
    >
      {error ? <ErrorBanner message={error} /> : null}

      {loading ? (
        <LoadingState label="Loading integration settings..." />
      ) : (
        <div className="stack">
          <Section title="UrbanKart Connection">
            <UrbanKartConnectionCard
              connection={connection}
              getToken={tokenGetter}
              onChanged={load}
            />
          </Section>

          <Section title="External API Logs">
            <ExternalApiLogsTable logs={logs} />
          </Section>
        </div>
      )}
    </AppShell>
  );
}