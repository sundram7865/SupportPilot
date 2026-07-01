import { Badge } from "@/components/ui/Badge";
import { Section } from "@/components/ui/Section";
import { statusTone } from "@/lib/format";
import type { Ticket } from "@/types/api";

function formatDateTime(value?: string | null) {
  if (!value) return "Not set";

  try {
    return new Intl.DateTimeFormat("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

function slaTone(status?: string | null): "green" | "red" | "yellow" | "blue" | "default" {
  if (status === "BREACHED") return "red";
  if (status === "NEAR_BREACH") return "yellow";
  if (status === "OK") return "green";
  return "default";
}

function getSlaHelper(ticket: Ticket) {
  if (ticket.sla_status === "BREACHED") {
    return "This ticket has crossed its SLA deadline.";
  }

  if (ticket.sla_status === "NEAR_BREACH") {
    return "This ticket is close to breaching SLA.";
  }

  if (ticket.sla_status === "OK") {
    return "SLA is currently healthy.";
  }

  return "SLA status is not available.";
}

function InfoItem({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div>
      <div className="muted">{label}</div>
      <div style={{ marginTop: 5, fontWeight: 700 }}>{value}</div>
    </div>
  );
}

export function TicketSummary({ ticket }: { ticket: Ticket | null }) {
  if (!ticket) {
    return (
      <Section title="Ticket Summary">
        <div className="muted">Loading ticket summary...</div>
      </Section>
    );
  }

  return (
    <Section
      title="Ticket Summary"
      action={
        <Badge tone={slaTone(ticket.sla_status)}>
          SLA: {ticket.sla_status || "UNKNOWN"}
        </Badge>
      }
    >
      <div
        className="list-item"
        style={{
          marginBottom: 16,
          borderLeft:
            ticket.sla_status === "BREACHED"
              ? "4px solid #dc2626"
              : ticket.sla_status === "NEAR_BREACH"
              ? "4px solid #ca8a04"
              : "4px solid #16a34a",
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
          <div>
            <div className="muted">Subject</div>
            <h2 style={{ margin: "6px 0 0", fontSize: 20 }}>{ticket.subject}</h2>
          </div>

          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "start" }}>
            <Badge tone={statusTone(ticket.status) as any}>{ticket.status}</Badge>
            <Badge tone={statusTone(ticket.priority) as any}>{ticket.priority}</Badge>
          </div>
        </div>

        <div className="muted" style={{ marginTop: 10 }}>
          {getSlaHelper(ticket)}
        </div>
      </div>

      <div className="grid grid-3">
        <InfoItem
          label="Ticket Number"
          value={ticket.ticket_number || ticket.id.slice(0, 8)}
        />

        <InfoItem label="Category" value={ticket.category} />

        <InfoItem label="Source" value={ticket.source} />
      </div>

      <div className="grid grid-3" style={{ marginTop: 16 }}>
        <InfoItem
          label="First Response Due"
          value={formatDateTime(ticket.first_response_due_at)}
        />

        <InfoItem
          label="Resolution Due"
          value={formatDateTime(ticket.resolution_due_at)}
        />

        <InfoItem
          label="SLA Breached At"
          value={formatDateTime(ticket.sla_breached_at)}
        />
      </div>

      <div className="grid grid-3" style={{ marginTop: 16 }}>
        <InfoItem
          label="First Response At"
          value={formatDateTime(ticket.first_response_at)}
        />

        <InfoItem label="Resolved At" value={formatDateTime(ticket.resolved_at)} />

        <InfoItem label="Closed At" value={formatDateTime(ticket.closed_at)} />
      </div>

      <div className="grid grid-2" style={{ marginTop: 16 }}>
        <div className="list-item">
          <div className="muted">Customer</div>
          <div style={{ marginTop: 6 }}>
            <strong>{ticket.customer_name || "Unknown customer"}</strong>
          </div>
          <div className="muted" style={{ marginTop: 4 }}>
            {ticket.customer_email || "No email"}{" "}
            {ticket.customer_phone ? `· ${ticket.customer_phone}` : ""}
          </div>
        </div>

        <div className="list-item">
          <div className="muted">Linked Order</div>
          <div style={{ marginTop: 6 }}>
            <strong>{ticket.external_order_id || "No order linked"}</strong>
          </div>
          <div className="muted" style={{ marginTop: 4 }}>
            Used by UrbanKart order/payment/shipment tools.
          </div>
        </div>
      </div>

      {ticket.description ? (
        <div className="list-item" style={{ marginTop: 16 }}>
          <div className="muted">Customer Issue</div>
          <p style={{ marginBottom: 0, whiteSpace: "pre-wrap" }}>
            {ticket.description}
          </p>
        </div>
      ) : null}
    </Section>
  );
}