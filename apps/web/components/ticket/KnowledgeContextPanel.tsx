import { EmptyState } from "@/components/ui/EmptyState";
import { Section } from "@/components/ui/Section";

function formatScore(score: unknown) {
  if (typeof score === "number") {
    return score.toFixed(3);
  }

  if (score == null) return "N/A";

  return String(score);
}

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
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <strong>{String(item.document_title || "Knowledge document")}</strong>
              <span className="muted">Score: {formatScore(item.score)}</span>
            </div>

            <div className="muted" style={{ marginTop: 6 }}>
              Type: {String(item.document_type || "N/A")} · Chunk:{" "}
              {String(item.chunk_index ?? "N/A")}
            </div>

            {item.content ? (
              <div style={{ marginTop: 10, whiteSpace: "pre-wrap" }}>
                {String(item.content)}
              </div>
            ) : null}
          </div>
        ))}

        {retrievedContext.length === 0 ? (
          <EmptyState message="No knowledge context retrieved yet. Add and ingest KB documents to improve RAG output." />
        ) : null}
      </div>
    </Section>
  );
}