"use client";

import { useState } from "react";

import { apiFetch } from "@/lib/api";
import type {
  CreateKnowledgeDocumentPayload,
  KnowledgeDocument,
} from "@/types/api";

const documentTypes = [
  "POLICY",
  "FAQ",
  "SOP",
  "TONE_GUIDE",
  "LEGAL",
  "OTHER",
];

export function CreateKnowledgeDocumentForm({
  getToken,
  onCreated,
}: {
  getToken?: () => Promise<string | null>;
  onCreated: () => void;
}) {
  const [title, setTitle] = useState("");
  const [documentType, setDocumentType] = useState("POLICY");
  const [sourceUrl, setSourceUrl] = useState("");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: React.FormEvent) {
    event.preventDefault();

    if (!getToken) return;

    setSubmitting(true);
    setMessage(null);

    try {
      const payload: CreateKnowledgeDocumentPayload = {
        title,
        document_type: documentType,
        content,
        source_url: sourceUrl || null,
      };

      await apiFetch<KnowledgeDocument>("/knowledge/documents", {
        method: "POST",
        getToken,
        body: JSON.stringify(payload),
      });

      setTitle("");
      setDocumentType("POLICY");
      setSourceUrl("");
      setContent("");
      setMessage("Knowledge document created.");

      await onCreated();
    } catch (err) {
      setMessage(
        err instanceof Error ? err.message : "Failed to create document."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="stack" onSubmit={submit}>
      <div className="grid-two">
        <div>
          <label className="label">Title</label>
          <input
            className="input"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Refund Policy"
            required
          />
        </div>

        <div>
          <label className="label">Document Type</label>
          <select
            className="input"
            value={documentType}
            onChange={(event) => setDocumentType(event.target.value)}
          >
            {documentTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>

        <div style={{ gridColumn: "1 / -1" }}>
          <label className="label">Source URL</label>
          <input
            className="input"
            value={sourceUrl}
            onChange={(event) => setSourceUrl(event.target.value)}
            placeholder="https://company.com/refund-policy"
          />
        </div>
      </div>

      <div>
        <label className="label">Content</label>
        <textarea
          className="input textarea"
          value={content}
          onChange={(event) => setContent(event.target.value)}
          placeholder="Paste policy, FAQ, SOP, or support guideline content here..."
          required
        />
      </div>

      {message ? <p className="muted">{message}</p> : null}

      <div>
        <button className="button" disabled={submitting}>
          {submitting ? "Creating..." : "Create Document"}
        </button>
      </div>
    </form>
  );
}