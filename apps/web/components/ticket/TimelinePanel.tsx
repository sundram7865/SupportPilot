import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { formatDate } from "@/lib/format";
import type { TimelineEvent } from "@/types/api";

function eventTone(eventType: string): "green" | "red" | "yellow" | "blue" | "default" {
  if (eventType.includes("FAILED") || eventType.includes("REJECTED") || eventType.includes("BREACHED")) {
    return "red";
  }

  if (eventType.includes("APPROVAL") || eventType.includes("BLOCKED") || eventType.includes("WAITING")) {
    return "yellow";
  }

  if (eventType.includes("COMPLETED") || eventType.includes("APPROVED") || eventType.includes("SENT")) {
    return "green";
  }

  if (eventType.includes("STARTED") || eventType.includes("CREATED") || eventType.includes("UPDATED")) {
    return "blue";
  }

  return "default";
}

export function TimelinePanel({ timeline }: { timeline: TimelineEvent[] }) {
  return (
    <Section title="Live Timeline">
      <div className="timeline">
        {timeline.map((event) => (
          <div key={event.id} className="timeline-item">
            <Badge tone={eventTone(event.event_type)}>{event.event_type}</Badge>

            <div style={{ marginTop: 8 }}>
              <strong>{event.title}</strong>
            </div>

            {event.description ? (
              <div className="muted" style={{ marginTop: 4 }}>
                {event.description}
              </div>
            ) : null}

            {(event.old_value || event.new_value) ? (
              <div className="muted" style={{ marginTop: 4 }}>
                {event.old_value || "—"} → {event.new_value || "—"}
              </div>
            ) : null}

            <div className="muted" style={{ marginTop: 4 }}>
              {formatDate(event.created_at)}
            </div>
          </div>
        ))}

        {timeline.length === 0 ? (
          <EmptyState message="No timeline events yet." />
        ) : null}
      </div>
    </Section>
  );
}