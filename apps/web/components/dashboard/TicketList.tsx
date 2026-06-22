import Link from "next/link";

import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { statusTone } from "@/lib/format";
import type { Ticket } from "@/types/api";

export function TicketList({
  tickets,
  loading,
}: {
  tickets: Ticket[];
  loading?: boolean;
}) {
  return (
    <Section title="Tickets">
      {loading ? <p className="muted">Loading tickets...</p> : null}

      <div className="list">
        {tickets.map((ticket) => (
          <Link
            key={ticket.id}
            className="list-item"
            href={`/tickets/${ticket.id}`}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <strong>{ticket.ticket_number || "Ticket"}</strong>
              <Badge tone={statusTone(ticket.status) as any}>
                {ticket.status}
              </Badge>
            </div>

            <div style={{ marginTop: 8 }}>{ticket.subject}</div>

            <div className="muted" style={{ marginTop: 6 }}>
              {ticket.customer_email || "No email"} · {ticket.priority} ·{" "}
              {ticket.category} · {ticket.source}
            </div>
          </Link>
        ))}

        {!loading && tickets.length === 0 ? (
          <EmptyState message="No tickets yet." />
        ) : null}
      </div>
    </Section>
  );
}