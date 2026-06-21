"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "@/lib/api";
import type {
  IntegrationConnection,
  UrbanKartHealthResponse,
} from "@/types/api";

export function UrbanKartConnectionCard({
  connection,
  getToken,
  onChanged,
}: {
  connection: IntegrationConnection | null;
  getToken?: () => Promise<string | null>;
  onChanged: () => void;
}) {
  const [baseUrl, setBaseUrl] = useState(
    connection?.base_url || "http://urbankart-mock-api:8001"
  );
  const [apiKey, setApiKey] = useState("dev_urbankart_key");
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [deactivating, setDeactivating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [health, setHealth] = useState<UrbanKartHealthResponse | null>(null);

  useEffect(() => {
    if (connection?.base_url) {
      setBaseUrl(connection.base_url);
    }
  }, [connection]);

  async function saveConnection() {
    if (!getToken) return;

    setSaving(true);
    setMessage(null);

    try {
      await apiFetch<IntegrationConnection>("/integrations/urbankart", {
        method: "PUT",
        getToken,
        body: JSON.stringify({
          base_url: baseUrl,
          api_key: apiKey,
        }),
      });

      setMessage("UrbanKart connection saved.");
      await onChanged();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  async function testConnection() {
    if (!getToken) return;

    setTesting(true);
    setMessage(null);
    setHealth(null);

    try {
      const response = await apiFetch<UrbanKartHealthResponse>(
        "/integrations/urbankart/test-connection",
        {
          method: "POST",
          getToken,
        }
      );

      setHealth(response);
      setMessage("Connection test completed.");
      await onChanged();
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Connection test failed."
      );
    } finally {
      setTesting(false);
    }
  }

  async function deactivateConnection() {
    if (!getToken) return;

    const ok = window.confirm("Deactivate UrbanKart integration?");
    if (!ok) return;

    setDeactivating(true);
    setMessage(null);

    try {
      await apiFetch<IntegrationConnection>(
        "/integrations/urbankart/deactivate",
        {
          method: "PATCH",
          getToken,
        }
      );

      setMessage("UrbanKart integration deactivated.");
      await onChanged();
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Failed to deactivate."
      );
    } finally {
      setDeactivating(false);
    }
  }

  return (
    <div className="stack">
      <div className="grid-two">
        <div>
          <label className="label">Provider</label>
          <input className="input" value="UrbanKart" disabled />
        </div>

        <div>
          <label className="label">Status</label>
          <input
            className="input"
            value={connection?.status || "NOT_CONNECTED"}
            disabled
          />
        </div>

        <div>
          <label className="label">Base URL</label>
          <input
            className="input"
            value={baseUrl}
            onChange={(event) => setBaseUrl(event.target.value)}
            placeholder="http://urbankart-mock-api:8001"
          />
        </div>

        <div>
          <label className="label">API Key</label>
          <input
            className="input"
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="dev_urbankart_key"
            type="password"
          />
        </div>

        <div>
          <label className="label">Last Health Status</label>
          <input
            className="input"
            value={connection?.last_health_status || "-"}
            disabled
          />
        </div>

        <div>
          <label className="label">Last Checked At</label>
          <input
            className="input"
            value={
              connection?.last_checked_at
                ? new Date(connection.last_checked_at).toLocaleString()
                : "-"
            }
            disabled
          />
        </div>
      </div>

      {connection?.last_health_message ? (
        <p className="muted">{connection.last_health_message}</p>
      ) : null}

      {health ? (
        <pre className="code-block">{JSON.stringify(health, null, 2)}</pre>
      ) : null}

      {message ? <p className="muted">{message}</p> : null}

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button className="button" onClick={saveConnection} disabled={saving}>
          {saving ? "Saving..." : "Save Connection"}
        </button>

        <button
          className="button secondary"
          onClick={testConnection}
          disabled={testing}
        >
          {testing ? "Testing..." : "Test Connection"}
        </button>

        {connection ? (
          <button
            className="button danger"
            onClick={deactivateConnection}
            disabled={deactivating}
          >
            {deactivating ? "Deactivating..." : "Deactivate"}
          </button>
        ) : null}
      </div>
    </div>
  );
}