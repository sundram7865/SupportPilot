import { Badge } from "@/components/ui/Badge";
import { Section } from "@/components/ui/Section";
import { statusTone } from "@/lib/format";
import type { Ticket } from "@/types/api";

export function TicketSummary({ ticket }: { ticket: Ticket | null }) {
  if (!ticket) return null;

  return (
    <Section title="Ticket Summary">
      <div className="grid grid-3">
        <div>
          <div className="muted">Status</div>
          <Badge tone={statusTone(ticket.status) as any}>{ticket.status}</Badge>
        </div>

        <div>
          <div className="muted">Priority</div>
          <Badge tone={statusTone(ticket.priority) as any}>{ticket.priority}</Badge>
        </div>

        <div>
          <div className="muted">Category</div>
          <strong>{ticket.category}</strong>
        </div>
      </div>

      <div style={{ marginTop: 14 }}>
        <div className="muted">Customer</div>
        <strong>{ticket.customer_name || "Unknown"}</strong>{" "}
        <span className="muted">{ticket.customer_email}</span>
      </div>

      <div style={{ marginTop: 14 }}>
        <div className="muted">Order</div>
        <strong>{ticket.external_order_id || "ORD-1001"}</strong>
      </div>
    </Section>
  );
}