"use client";

import { useAuth } from "@clerk/nextjs";
import { useState } from "react";

import { Section } from "@/components/ui/Section";
import { useCreateTicket, type CreateTicketPayload } from "@/hooks/useTicketQueries";

const defaultTicket: CreateTicketPayload = {
  subject: "Where is my order?",
  description: "I placed order ORD-1001 and want to know the delivery status.",
  customer_name: "Rahul Sharma",
  customer_email: "rahul@example.com",
  customer_phone: "9999999999",
  external_order_id: "ORD-1001",
  priority: "MEDIUM",
  category: "ORDER_STATUS",
  source: "SUPPORT_FORM",
  metadata_json: {
    created_from: "admin_dashboard",
  },
};

export function CreateTicketForm({ orgId }: { orgId: string | null }) {
  const { getToken, isSignedIn } = useAuth();

  const [form, setForm] = useState<CreateTicketPayload>(defaultTicket);
  const [message, setMessage] = useState<string | null>(null);

  const createTicketMutation = useCreateTicket({
    orgId,
    getToken: isSignedIn ? getToken : undefined,
  });

  async function createTicket() {
    setMessage(null);

    try {
      const ticket = await createTicketMutation.mutateAsync(form);

      setMessage(`Created ${ticket.ticket_number || "ticket"}.`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to create ticket.");
    }
  }

  return (
    <Section title="Create Ticket">
      <div className="form-row">
        <label className="label">Subject</label>
        <input
          className="input"
          value={form.subject}
          onChange={(event) =>
            setForm((prev) => ({ ...prev, subject: event.target.value }))
          }
        />
      </div>

      <div className="form-row">
        <label className="label">Description</label>
        <textarea
          className="textarea"
          value={form.description}
          onChange={(event) =>
            setForm((prev) => ({ ...prev, description: event.target.value }))
          }
        />
      </div>

      <div className="grid grid-2">
        <div className="form-row">
          <label className="label">Customer Name</label>
          <input
            className="input"
            value={form.customer_name || ""}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                customer_name: event.target.value,
              }))
            }
          />
        </div>

        <div className="form-row">
          <label className="label">Customer Email</label>
          <input
            className="input"
            type="email"
            value={form.customer_email}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                customer_email: event.target.value,
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
            value={form.external_order_id || ""}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                external_order_id: event.target.value,
              }))
            }
          />
        </div>

        <div className="form-row">
          <label className="label">Priority</label>
          <select
            className="select"
            value={form.priority}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, priority: event.target.value }))
            }
          >
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
            value={form.category}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, category: event.target.value }))
            }
          >
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

      {message ? <p className="muted">{message}</p> : null}

      <button
        className="btn"
        disabled={createTicketMutation.isPending || !orgId}
        onClick={createTicket}
      >
        {createTicketMutation.isPending ? "Creating..." : "Create Ticket"}
      </button>
    </Section>
  );
}