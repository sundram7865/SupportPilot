import { Badge } from "@/components/ui/Badge";
import { Section } from "@/components/ui/Section";
import { statusTone } from "@/lib/format";
import type { Ticket } from "@/types/api";

function formatDateTime(value?: string | null) {
  if (!value) return "Not set";

  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function slaTone(status?: string | null) {
  if (status === "BREACHED") return "red";
  if (status === "NEAR_BREACH") return "yellow";
  if (status === "OK") return "green";
  return "gray";
}

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

      <div className="grid grid-3" style={{ marginTop: 16 }}>
        <div>
          <div className="muted">SLA Status</div>
          <Badge tone={slaTone(ticket.sla_status) as any}>
            {ticket.sla_status || "UNKNOWN"}
          </Badge>
        </div>

        <div>
          <div className="muted">First Response Due</div>
          <strong>{formatDateTime(ticket.first_response_due_at)}</strong>
        </div>

        <div>
          <div className="muted">Resolution Due</div>
          <strong>{formatDateTime(ticket.resolution_due_at)}</strong>
        </div>
      </div>

      <div className="grid grid-3" style={{ marginTop: 16 }}>
        <div>
          <div className="muted">First Response At</div>
          <strong>{formatDateTime(ticket.first_response_at)}</strong>
        </div>

        <div>
          <div className="muted">Resolved At</div>
          <strong>{formatDateTime(ticket.resolved_at)}</strong>
        </div>

        <div>
          <div className="muted">SLA Breached At</div>
          <strong>{formatDateTime(ticket.sla_breached_at)}</strong>
        </div>
      </div>

      <div style={{ marginTop: 14 }}>
        <div className="muted">Customer</div>
        <strong>{ticket.customer_name || "Unknown"}</strong>{" "}
        <span className="muted">{ticket.customer_email}</span>
      </div>

      <div style={{ marginTop: 14 }}>
        <div className="muted">Order</div>
        <strong>{ticket.external_order_id || "No order linked"}</strong>
      </div>
    </Section>
  );
}