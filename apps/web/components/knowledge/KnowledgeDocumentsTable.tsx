"use client";

import { apiFetch } from "@/lib/api";
import type { KnowledgeDocument } from "@/types/api";

export function KnowledgeDocumentsTable({
  documents,
  getToken,
  onChanged,
  onViewChunks,
}: {
  documents: KnowledgeDocument[];
  getToken?: () => Promise<string | null>;
  onChanged: () => void;
  onViewChunks: (document: KnowledgeDocument) => void;
}) {
  async function ingest(documentId: string) {
    if (!getToken) return;

    await apiFetch(`/knowledge/documents/${documentId}/ingest`, {
      method: "POST",
      getToken,
    });

    await onChanged();
  }

  async function remove(documentId: string) {
    if (!getToken) return;

    const ok = window.confirm("Delete this knowledge document?");
    if (!ok) return;

    await apiFetch(`/knowledge/documents/${documentId}`, {
      method: "DELETE",
      getToken,
    });

    await onChanged();
  }

  if (documents.length === 0) {
    return <p className="muted">No knowledge documents yet.</p>;
  }

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Type</th>
            <th>Status</th>
            <th>Version</th>
            <th>Updated</th>
            <th />
          </tr>
        </thead>

        <tbody>
          {documents.map((document) => (
            <tr key={document.id}>
              <td>{document.title}</td>
              <td>{document.document_type}</td>
              <td>{document.ingestion_status || document.status}</td>
              <td>{document.version || "-"}</td>
              <td>
                {document.updated_at
                  ? new Date(document.updated_at).toLocaleString()
                  : "-"}
              </td>
              <td>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <button
                    className="button secondary"
                    onClick={() => ingest(document.id)}
                  >
                    Ingest
                  </button>

                  <button
                    className="button secondary"
                    onClick={() => onViewChunks(document)}
                  >
                    Chunks
                  </button>

                  <button
                    className="button danger"
                    onClick={() => remove(document.id)}
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}