"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { apiFetch, bootstrapAuth, getOrgId } from "@/lib/api";
import type { AuthMeResponse, Ticket } from "@/types/api";

type TicketListResponse = {
  items?: Ticket[];
  total?: number;
};

const defaultTicket = {
  subject: "Where is my order?",
  description: "I placed order ORD-1001 and want to know the delivery status.",
  customer_name: "Rahul Sharma",
  customer_email: "rahul@example.com",
  customer_phone: "9999999999",
  external_order_id: "ORD-1001",
  priority: "MEDIUM",
  category: "ORDER_STATUS",
  source: "SUPPORT_FORM",
};

export default function DashboardPage() {
  const [me, setMe] = useState<AuthMeResponse | null>(null);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [form, setForm] = useState(defaultTicket);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function load() {
    try {
      setError(null);

      const auth = await bootstrapAuth();
      setMe(auth);

      const data = await apiFetch<TicketListResponse | Ticket[]>("/tickets", {
        method: "GET",
      });

      const ticketItems = Array.isArray(data) ? data : data.items || [];
      setTickets(ticketItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  }

  async function createTicket() {
    try {
      setCreating(true);
      setError(null);
      setNotice(null);

      const ticket = await apiFetch<Ticket>("/tickets", {
        method: "POST",
        body: JSON.stringify(form),
      });

      setNotice(`Ticket created: ${ticket.ticket_number || ticket.id}`);
      setTickets((current) => [ticket, ...current]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create ticket");
    } finally {
      setCreating(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <main className="page">
      <div className="container">
        <div className="header">
          <div>
            <div className="logo">SupportPilot</div>
            <div className="muted">Phase 12 Dashboard Foundation</div>
          </div>

          <div className="card">
            <div className="muted">Current org</div>
            <strong>{getOrgId() || "Loading..."}</strong>
          </div>
        </div>

        {error ? <div className="error">{error}</div> : null}
        {notice ? <div className="success">{notice}</div> : null}

        <div className="grid grid-2" style={{ marginTop: 16 }}>
          <section className="card">
            <div className="card-title">Create Ticket</div>

            <div className="form-row">
              <label className="label">Subject</label>
              <input
                className="input"
                value={form.subject}
                onChange={(e) =>
                  setForm((prev) => ({ ...prev, subject: e.target.value }))
                }
              />
            </div>

            <div className="form-row">
              <label className="label">Description</label>
              <textarea
                className="textarea"
                value={form.description}
                onChange={(e) =>
                  setForm((prev) => ({
                    ...prev,
                    description: e.target.value,
                  }))
                }
              />
            </div>

            <div className="grid grid-2">
              <div className="form-row">
                <label className="label">Customer Name</label>
                <input
                  className="input"
                  value={form.customer_name}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      customer_name: e.target.value,
                    }))
                  }
                />
              </div>

              <div className="form-row">
                <label className="label">Customer Email</label>
                <input
                  className="input"
                  value={form.customer_email}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      customer_email: e.target.value,
                    }))
                  }
                />
              </div>
            </div>

            <div className="grid grid-3">
              <div className="form-row">
                <label className="label">Order ID</label>
                <input
                  className="input"
                  value={form.external_order_id}
                  onChange={(e) =>
                    setForm((prev) => ({
                      ...prev,
                      external_order_id: e.target.value,
                    }))
                  }
                />
              </div>

              <div className="form-row">
                <label className="label">Priority</label>
                <select
                  className="select"
                  value={form.priority}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, priority: e.target.value }))
                  }
                >
                  <option>LOW</option>
                  <option>MEDIUM</option>
                  <option>HIGH</option>
                  <option>URGENT</option>
                </select>
              </div>

              <div className="form-row">
                <label className="label">Category</label>
                <select
                  className="select"
                  value={form.category}
                  onChange={(e) =>
                    setForm((prev) => ({ ...prev, category: e.target.value }))
                  }
                >
                  <option>ORDER_STATUS</option>
                  <option>PAYMENT_ISSUE</option>
                  <option>REFUND_REQUEST</option>
                  <option>LEGAL_RISK</option>
                  <option>OTHER</option>
                </select>
              </div>
            </div>

            <button className="btn" disabled={creating} onClick={createTicket}>
              {creating ? "Creating..." : "Create Ticket"}
            </button>
          </section>

          <section className="card">
            <div className="card-title">Tickets</div>

            {loading ? <div className="muted">Loading...</div> : null}

            <div className="list">
              {tickets.map((ticket) => (
                <Link
                  key={ticket.id}
                  className="list-item"
                  href={`/tickets/${ticket.id}`}
                >
                  <div style={{ display: "flex", justifyContent: "space-between" }}>
                    <strong>{ticket.ticket_number || "Ticket"}</strong>
                    <span className="badge">{ticket.status}</span>
                  </div>

                  <div style={{ marginTop: 8 }}>{ticket.subject}</div>

                  <div className="muted" style={{ marginTop: 6 }}>
                    {ticket.customer_email || "No email"} · {ticket.priority} ·{" "}
                    {ticket.category}
                  </div>
                </Link>
              ))}

              {!loading && tickets.length === 0 ? (
                <div className="muted">No tickets yet.</div>
              ) : null}
            </div>
          </section>
        </div>

        {me ? (
          <section className="card" style={{ marginTop: 16 }}>
            <div className="card-title">Logged in dev user</div>
            <pre className="code">{JSON.stringify(me.user, null, 2)}</pre>
          </section>
        ) : null}
      </div>
    </main>
  );
}