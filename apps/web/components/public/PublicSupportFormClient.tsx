"use client";

import { useEffect, useState } from "react";

import { API_URL } from "@/lib/api";
import type {
  PublicOrganization,
  PublicTicketCreatePayload,
  PublicTicketCreateResponse,
} from "@/types/api";

export function PublicSupportFormClient({
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
  const [customerPhone, setCustomerPhone] = useState("");
  const [externalOrderId, setExternalOrderId] = useState("");

  const [loadingOrg, setLoadingOrg] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [createdTicket, setCreatedTicket] =
    useState<PublicTicketCreateResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadOrganization() {
    try {
      setLoadingOrg(true);
      setError(null);

      const response = await fetch(
        `${API_URL}/public/organizations/${organizationSlug}`,
        {
          method: "GET",
        }
      );

      if (!response.ok) {
        throw new Error("Support portal not found.");
      }

      const data = (await response.json()) as PublicOrganization;
      setOrganization(data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load support portal."
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
        customer_phone: customerPhone || null,
        external_order_id: externalOrderId || null,
        metadata_json: {
          frontend_path: `/support/${organizationSlug}`,
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

      setSubject("");
      setDescription("");
      setCustomerName("");
      setCustomerEmail("");
      setCustomerPhone("");
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
      <main className="public-page">
        <div className="public-card">
          <p className="muted">Loading support portal...</p>
        </div>
      </main>
    );
  }

  if (error && !organization) {
    return (
      <main className="public-page">
        <div className="public-card">
          <h1>Support Portal</h1>
          <p className="error-text">{error}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="public-page">
      <div className="public-card">
        <div className="public-header">
          <p className="eyebrow">Customer Support</p>
          <h1>{organization?.name || "Support"}</h1>
          <p className="muted">
            Submit your issue and our support team will get back to you.
          </p>
        </div>

        {createdTicket ? (
          <div className="success-box">
            <h2>Ticket Created</h2>
            <p>{createdTicket.message}</p>
            <p>
              Ticket Number: <strong>{createdTicket.ticket_number}</strong>
            </p>
            <p>
              Status: <strong>{createdTicket.status}</strong>
            </p>

            <button
              className="button"
              onClick={() => setCreatedTicket(null)}
            >
              Submit Another Ticket
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
                className="input textarea"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Explain your issue clearly..."
                required
                minLength={3}
                maxLength={5000}
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

              <div>
                <label className="label">Phone</label>
                <input
                  className="input"
                  value={customerPhone}
                  onChange={(event) => setCustomerPhone(event.target.value)}
                  placeholder="+91..."
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

            <button className="button" disabled={submitting}>
              {submitting ? "Submitting..." : "Submit Ticket"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}