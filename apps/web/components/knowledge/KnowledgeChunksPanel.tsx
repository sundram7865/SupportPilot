import { LoadingState } from "@/components/ui/LoadingState";
import type { KnowledgeChunk, KnowledgeDocument } from "@/types/api";

export function KnowledgeChunksPanel({
  chunks,
  loading,
  selectedDocument,
}: {
  chunks: KnowledgeChunk[];
  loading: boolean;
  selectedDocument: KnowledgeDocument | null;
}) {
  if (!selectedDocument) {
    return <p className="muted">Select a document and click Chunks.</p>;
  }

  if (loading) {
    return <LoadingState label="Loading chunks..." />;
  }

  if (chunks.length === 0) {
    return (
      <p className="muted">
        No chunks found. Click Ingest for this document first.
      </p>
    );
  }

  return (
    <div className="stack">
      {chunks.map((chunk, index) => (
        <div key={chunk.id || index} className="card">
          <div className="muted" style={{ marginBottom: 8 }}>
            Chunk {chunk.chunk_index ?? index + 1}
            {chunk.token_count ? ` • ${chunk.token_count} tokens` : ""}
          </div>

          <p style={{ whiteSpace: "pre-wrap" }}>{chunk.content}</p>
        </div>
      ))}
    </div>
  );
}