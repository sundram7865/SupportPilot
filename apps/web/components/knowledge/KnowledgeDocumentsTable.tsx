"use client";
import {useState} from "react"
import { Download, FileText, RefreshCw } from "lucide-react";
import { apiFetch } from "@/lib/api";
import type { KnowledgeDocument } from "@/types/api";

export function KnowledgeDocumentsTable({
  documents,
  getToken,
  onChanged,
  onViewChunks,
  onDownload,
}: {
  documents: KnowledgeDocument[];
  getToken?: () => Promise<string | null>;
  onChanged: () => void;
  onViewChunks: (document: KnowledgeDocument) => void;
  onDownload?: (document: KnowledgeDocument) => void;
}) {
  const [ingestingIds, setIngestingIds] = useState<Set<string>>(new Set());

  async function ingest(documentId: string) {
    if (!getToken) return;

    setIngestingIds((prev) => new Set(prev).add(documentId));

    try {
      await apiFetch(`/knowledge/documents/${documentId}/ingest`, {
        method: "POST",
        getToken,
      });

      await onChanged();
    } catch (err) {
      alert(
        err instanceof Error ? err.message : "Ingestion failed."
      );
    } finally {
      setIngestingIds((prev) => {
        const next = new Set(prev);
        next.delete(documentId);
        return next;
      });
    }
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

  function getStatusBadge(document: KnowledgeDocument) {
    const status = document.ingestion_status || document.status || "DRAFT";
    
    const styles: Record<string, { bg: string; color: string; label: string }> = {
      INGESTED: { bg: "#d1fae5", color: "#065f46", label: "Ingested" },
      PENDING: { bg: "#fef3c7", color: "#92400e", label: "Pending" },
      FAILED: { bg: "#fee2e2", color: "#991b1b", label: "Failed" },
      DRAFT: { bg: "#e0e7ff", color: "#3730a3", label: "Draft" },
      ACTIVE: { bg: "#d1fae5", color: "#065f46", label: "Active" },
      ARCHIVED: { bg: "#f3f4f6", color: "#374151", label: "Archived" },
    };

    const style = styles[status] || { bg: "#f3f4f6", color: "#374151", label: status };

    return (
      <span
        style={{
          display: "inline-block",
          padding: "2px 8px",
          borderRadius: 12,
          fontSize: 12,
          fontWeight: 500,
          backgroundColor: style.bg,
          color: style.color,
        }}
      >
        {style.label}
      </span>
    );
  }

  function formatDate(dateString?: string | null): string {
    if (!dateString) return "-";
    try {
      return new Date(dateString).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "-";
    }
  }

  function formatFileSize(bytes?: number | null): string {
    if (!bytes) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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
            <th>File</th>
            <th>Status</th>
            <th>Chunks</th>
            <th>Updated</th>
            <th style={{ width: 220 }}>Actions</th>
          </tr>
        </thead>

        <tbody>
          {documents.map((document) => (
            <tr key={document.id}>
              <td>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  {document.file_name && (
                    <FileText size={14} style={{ color: "var(--color-muted, #9ca3af)" }} />
                  )}
                  <span style={{ fontWeight: 500 }}>{document.title}</span>
                </div>
                {document.ingestion_error && (
                  <div style={{ fontSize: 11, color: "var(--color-danger, #ef4444)", marginTop: 2 }}>
                    {document.ingestion_error.substring(0, 60)}
                    {document.ingestion_error.length > 60 ? "..." : ""}
                  </div>
                )}
              </td>
              <td>
                <span className="muted" style={{ fontSize: 13 }}>
                  {document.document_type?.replace(/_/g, " ")}
                </span>
              </td>
              <td>
                {document.file_name ? (
                  <div style={{ fontSize: 13 }}>
                    <div style={{ wordBreak: "break-all" }}>{document.file_name}</div>
                    {document.file_size && (
                      <span className="muted">
                        {formatFileSize(document.file_size)}
                      </span>
                    )}
                  </div>
                ) : (
                  <span className="muted" style={{ fontSize: 13 }}>
                    Text
                  </span>
                )}
              </td>
              <td>{getStatusBadge(document)}</td>
              <td style={{ textAlign: "center" }}>{document.chunk_count ?? 0}</td>
              <td>
                <span className="muted" style={{ fontSize: 13 }}>
                  {formatDate(document.updated_at)}
                </span>
              </td>
              <td>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap", alignItems: "center" }}>
                  <button
                    className="button secondary"
                    onClick={() => ingest(document.id)}
                    disabled={ingestingIds.has(document.id)}
                    style={{ fontSize: 12, padding: "4px 8px" }}
                    title="Ingest document for search"
                  >
                    {ingestingIds.has(document.id) ? (
                      <RefreshCw size={12} style={{ animation: "spin 1s linear infinite" }} />
                    ) : (
                      "Ingest"
                    )}
                  </button>

                  <button
                    className="button secondary"
                    onClick={() => onViewChunks(document)}
                    style={{ fontSize: 12, padding: "4px 8px" }}
                    title="View document chunks"
                  >
                    Chunks
                  </button>

                  {document.cloudinary_public_id && onDownload && (
                    <button
                      className="button secondary"
                      onClick={() => onDownload(document)}
                      style={{ fontSize: 12, padding: "4px 8px" }}
                      title="Download original file"
                    >
                      <Download size={14} />
                    </button>
                  )}

                  <button
                    className="button danger"
                    onClick={() => remove(document.id)}
                    style={{ fontSize: 12, padding: "4px 8px" }}
                    title="Delete document"
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <style jsx>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}