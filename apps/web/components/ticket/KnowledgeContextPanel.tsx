import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";

export function KnowledgeContextPanel({
  retrievedContext,
}: {
  retrievedContext: Array<Record<string, unknown>>;
}) {
  return (
    <Section title="Knowledge Used">
      <div className="list">
        {retrievedContext.map((item, index) => (
          <div key={index} className="list-item">
            <strong>{String(item.document_title || "Knowledge document")}</strong>

            <div className="muted" style={{ marginTop: 6 }}>
              Type: {String(item.document_type || "N/A")} · Score:{" "}
              {item.score != null ? String(item.score) : "N/A"}
            </div>

            {item.content ? (
              <div style={{ marginTop: 8 }}>{String(item.content)}</div>
            ) : null}
          </div>
        ))}

        {retrievedContext.length === 0 ? (
          <EmptyState message="No knowledge context retrieved yet." />
        ) : null}
      </div>
    </Section>
  );
}