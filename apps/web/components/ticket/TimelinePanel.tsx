import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";
import { formatDate } from "@/lib/format";
import type { TimelineEvent } from "@/types/api";

export function TimelinePanel({ timeline }: { timeline: TimelineEvent[] }) {
  return (
    <Section title="Live Timeline">
      <div className="timeline">
        {timeline.map((event) => (
          <div key={event.id} className="timeline-item">
            <Badge tone="blue">{event.event_type}</Badge>
            <div style={{ marginTop: 6 }}>
              <strong>{event.title}</strong>
            </div>
            {event.description ? (
              <div className="muted">{event.description}</div>
            ) : null}
            <div className="muted">{formatDate(event.created_at)}</div>
          </div>
        ))}

        {timeline.length === 0 ? <EmptyState message="No timeline events yet." /> : null}
      </div>
    </Section>
  );
}