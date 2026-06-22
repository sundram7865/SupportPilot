"use client";

import { useEffect, useState } from "react";

import { API_URL } from "@/lib/api";
import type {
  PublicOrganization,
  PublicTicketCreatePayload,
  PublicTicketCreateResponse,
} from "@/types/api";

export function EmbeddableSupportWidgetClient({
  organizationSlug,
}: {
  organizationSlug: string;
}) {
  const [organization, setOrganization] = useState<PublicOrganization | null>(
    null
  );

  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [customerName, setCustomerName] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [externalOrderId, setExternalOrderId] = useState("");

  const [loadingOrg, setLoadingOrg] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [createdTicket, setCreatedTicket] =
    useState<PublicTicketCreateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadOrganization() {
    if (!organizationSlug) {
      setError("Missing organization slug.");
      setLoadingOrg(false);
      return;
    }

    try {
      setLoadingOrg(true);
      setError(null);

      const response = await fetch(
        `${API_URL}/public/organizations/${organizationSlug}`,
        {
          method: "GET",
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Support portal not found.");
      }

      setOrganization(data as PublicOrganization);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load support widget."
      );
    } finally {
      setLoadingOrg(false);
    }
  }

  async function submitTicket(event: React.FormEvent) {
    event.preventDefault();

    try {
      setSubmitting(true);
      setError(null);
      setCreatedTicket(null);

      const payload: PublicTicketCreatePayload = {
        subject,
        description,
        customer_name: customerName || null,
        customer_email: customerEmail,
        customer_phone: null,
        external_order_id: externalOrderId || null,
        metadata_json: {
          intake_channel: "embeddable_widget",
          widget_org_slug: organizationSlug,
        },
      };

      const response = await fetch(
        `${API_URL}/public/organizations/${organizationSlug}/tickets`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Failed to create ticket.");
      }

      setCreatedTicket(data as PublicTicketCreateResponse);

      window.parent.postMessage(
        {
          type: "SUPPORTPILOT_TICKET_CREATED",
          ticketNumber: data.ticket_number,
        },
        "*"
      );

      setSubject("");
      setDescription("");
      setCustomerName("");
      setCustomerEmail("");
      setExternalOrderId("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit ticket.");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    loadOrganization();
  }, [organizationSlug]);

  if (loadingOrg) {
    return (
      <main className="widget-page">
        <div className="widget-card">
          <p className="muted">Loading support...</p>
        </div>
      </main>
    );
  }

  if (error && !organization) {
    return (
      <main className="widget-page">
        <div className="widget-card">
          <h1>Support</h1>
          <p className="error-text">{error}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="widget-page">
      <div className="widget-card">
        <div className="widget-header">
          <div>
            <p className="eyebrow">Support</p>
            <h1>{organization?.name || "Support"}</h1>
          </div>

          <button
            type="button"
            className="widget-close"
            onClick={() =>
              window.parent.postMessage(
                { type: "SUPPORTPILOT_CLOSE_WIDGET" },
                "*"
              )
            }
          >
            ×
          </button>
        </div>

        {createdTicket ? (
          <div className="success-box">
            <h2>Ticket Created</h2>
            <p>{createdTicket.message}</p>
            <p>
              Ticket: <strong>{createdTicket.ticket_number}</strong>
            </p>

            <button className="button" onClick={() => setCreatedTicket(null)}>
              Submit Another
            </button>
          </div>
        ) : (
          <form className="stack" onSubmit={submitTicket}>
            <div>
              <label className="label">Subject</label>
              <input
                className="input"
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                placeholder="Where is my order?"
                required
                minLength={3}
                maxLength={255}
              />
            </div>

            <div>
              <label className="label">Description</label>
              <textarea
                className="input widget-textarea"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Explain your issue..."
                required
                minLength={3}
                maxLength={5000}
              />
            </div>

            <div>
              <label className="label">Email</label>
              <input
                className="input"
                type="email"
                value={customerEmail}
                onChange={(event) => setCustomerEmail(event.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>

            <div className="grid-two">
              <div>
                <label className="label">Name</label>
                <input
                  className="input"
                  value={customerName}
                  onChange={(event) => setCustomerName(event.target.value)}
                  placeholder="Your name"
                />
              </div>

              <div>
                <label className="label">Order ID</label>
                <input
                  className="input"
                  value={externalOrderId}
                  onChange={(event) => setExternalOrderId(event.target.value)}
                  placeholder="ORD-1001"
                />
              </div>
            </div>

            {error ? <p className="error-text">{error}</p> : null}

            <button className="button widget-submit" disabled={submitting}>
              {submitting ? "Submitting..." : "Submit Ticket"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}