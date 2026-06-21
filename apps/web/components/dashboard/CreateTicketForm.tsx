import { useAuth } from "@clerk/nextjs";
import { useState } from "react";

import { Section } from "@/components/ui/Section";
import { apiFetch } from "@/lib/api";
import type { Ticket } from "@/types/api";

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

export function CreateTicketForm({
  orgId,
  onCreated,
}: {
  orgId: string | null;
  onCreated: (ticket: Ticket) => void;
}) {
  const { getToken, isSignedIn } = useAuth();
  const [form, setForm] = useState(defaultTicket);
  const [creating, setCreating] = useState(false);

  async function createTicket() {
    if (!orgId) return;

    setCreating(true);

    try {
      const ticket = await apiFetch<Ticket>("/tickets", {
        method: "POST",
        orgId,
        getToken: isSignedIn ? getToken : undefined,
        body: JSON.stringify(form),
      });

      onCreated(ticket);
    } finally {
      setCreating(false);
    }
  }

  return (
    <Section title="Create Ticket">
      <div className="form-row">
        <label className="label">Subject</label>
        <input
          className="input"
          value={form.subject}
          onChange={(e) => setForm((prev) => ({ ...prev, subject: e.target.value }))}
        />
      </div>

      <div className="form-row">
        <label className="label">Description</label>
        <textarea
          className="textarea"
          value={form.description}
          onChange={(e) =>
            setForm((prev) => ({ ...prev, description: e.target.value }))
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
              setForm((prev) => ({ ...prev, customer_name: e.target.value }))
            }
          />
        </div>

        <div className="form-row">
          <label className="label">Customer Email</label>
          <input
            className="input"
            value={form.customer_email}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, customer_email: e.target.value }))
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
              setForm((prev) => ({ ...prev, external_order_id: e.target.value }))
            }
          />
        </div>

        <div className="form-row">
          <label className="label">Priority</label>
          <select
            className="select"
            value={form.priority}
            onChange={(e) => setForm((prev) => ({ ...prev, priority: e.target.value }))}
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
            onChange={(e) => setForm((prev) => ({ ...prev, category: e.target.value }))}
          >
            <option>ORDER_STATUS</option>
            <option>PAYMENT_ISSUE</option>
            <option>REFUND_REQUEST</option>
            <option>RETURN_REPLACEMENT</option>
            <option>PRODUCT_QUESTION</option>
            <option>DELIVERY_ISSUE</option>
            <option>ACCOUNT_ISSUE</option>
            <option>COMPLAINT</option>
            <option>LEGAL_RISK</option>
            <option>OTHER</option>
          </select>
        </div>
      </div>

      <button className="btn" disabled={creating || !orgId} onClick={createTicket}>
        {creating ? "Creating..." : "Create Ticket"}
      </button>
    </Section>
  );
}