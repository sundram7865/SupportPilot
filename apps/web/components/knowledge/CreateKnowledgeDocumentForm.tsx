"use client";

import { useState, useRef } from "react";
import { Upload, FileText, X, File, AlertCircle } from "lucide-react";

import { apiFetch, uploadFile } from "@/lib/api";
import type { KnowledgeDocument } from "@/types/api";

const documentTypes = [
  "POLICY",
  "FAQ",
  "SOP",
  "TONE_GUIDE",
  "LEGAL",
  "OTHER",
];

const ALLOWED_EXTENSIONS = [".pdf", ".txt", ".md", ".csv", ".json", ".xml", ".docx"];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export function CreateKnowledgeDocumentForm({
  getToken,
  onCreated,
}: {
  getToken?: () => Promise<string | null>;
  onCreated: () => void;
}) {
  const [activeTab, setActiveTab] = useState<"text" | "upload">("text");

  // Text form state
  const [title, setTitle] = useState("");
  const [documentType, setDocumentType] = useState("POLICY");
  const [sourceUrl, setSourceUrl] = useState("");
  const [content, setContent] = useState("");

  // Upload form state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadTitle, setUploadTitle] = useState("");
  const [uploadDocumentType, setUploadDocumentType] = useState("OTHER");
  const [isDragging, setIsDragging] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<{
    type: "success" | "error";
    text: string;
  } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ==================== Text Document Submit ====================
  async function submitTextDocument(event: React.FormEvent) {
    event.preventDefault();
    if (!getToken) return;

    setSubmitting(true);
    setMessage(null);

    try {
      await apiFetch<KnowledgeDocument>("/knowledge/documents", {
        method: "POST",
        getToken,
        body: JSON.stringify({
          title,
          document_type: documentType,
          status: "ACTIVE",
          content,
          source_url: sourceUrl || null,
        }),
      });

      setTitle("");
      setDocumentType("POLICY");
      setSourceUrl("");
      setContent("");
      setMessage({ type: "success", text: "Document created successfully!" });
      await onCreated();
    } catch (err) {
      setMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to create document.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  // ==================== File Upload Submit ====================
  async function submitFileUpload(event: React.FormEvent) {
    event.preventDefault();
    if (!getToken || !selectedFile) {
      setMessage({ type: "error", text: "Please select a file." });
      return;
    }

    setSubmitting(true);
    setMessage(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile, selectedFile.name);
      if (uploadTitle.trim()) {
        formData.append("title", uploadTitle.trim());
      }
      formData.append("document_type", uploadDocumentType);
      formData.append("doc_status", "ACTIVE");
      await uploadFile<KnowledgeDocument>(
        "/knowledge/documents/upload",
        formData,
        { getToken }
      );

      // Reset form
      setSelectedFile(null);
      setUploadTitle("");
      setUploadDocumentType("OTHER");

      setMessage({
        type: "success",
        text: "File uploaded and ingested successfully!",
      });

      await onCreated();
    } catch (err) {
      setMessage({
        type: "error",
        text: err instanceof Error ? err.message : "Failed to upload file.",
      });
    } finally {
      setSubmitting(false);
    }
  }

  // ==================== File Handling ====================
  function validateFile(file: File): string | null {
    const extension = "." + file.name.split(".").pop()?.toLowerCase();

    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      return `Invalid file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
    }

    if (file.size > MAX_FILE_SIZE) {
      return `File too large. Max size: ${MAX_FILE_SIZE / 1024 / 1024}MB`;
    }

    return null;
  }

  function handleFileSelect(file: File) {
    const error = validateFile(file);
    if (error) {
      setMessage({ type: "error", text: error });
      return;
    }

    setSelectedFile(file);
    if (!uploadTitle) {
      setUploadTitle(file.name.replace(/\.[^/.]+$/, ""));
    }
    setMessage(null);
  }

  function handleDrop(event: React.DragEvent) {
    event.preventDefault();
    setIsDragging(false);

    const file = event.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  }

  function handleDragOver(event: React.DragEvent) {
    event.preventDefault();
    setIsDragging(true);
  }

  function handleDragLeave(event: React.DragEvent) {
    event.preventDefault();
    setIsDragging(false);
  }

  function clearFile() {
    setSelectedFile(null);
    if (uploadTitle === selectedFile?.name.replace(/\.[^/.]+$/, "")) {
      setUploadTitle("");
    }
  }

  function formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  // ==================== Render ====================
  return (
    <div className="stack">
      {/* Tab Switcher */}
      <div style={{ display: "flex", gap: 0, marginBottom: 4 }}>
        <button
          className={`button ${activeTab === "text" ? "" : "secondary"}`}
          onClick={() => setActiveTab("text")}
          style={{
            borderTopRightRadius: 0,
            borderBottomRightRadius: 0,
            borderRight: "none",
          }}
          type="button"
        >
          <FileText size={16} style={{ marginRight: 6 }} />
          Text
        </button>
        <button
          className={`button ${activeTab === "upload" ? "" : "secondary"}`}
          onClick={() => setActiveTab("upload")}
          style={{
            borderTopLeftRadius: 0,
            borderBottomLeftRadius: 0,
          }}
          type="button"
        >
          <Upload size={16} style={{ marginRight: 6 }} />
          Upload File
        </button>
      </div>

      {/* Message Banner */}
      {message && (
        <div
          style={{
            padding: "10px 14px",
            display: "flex",
            alignItems: "center",
            gap: 8,
            borderRadius: 8,
            backgroundColor:
              message.type === "error" ? "#fee2e2" : "#d1fae5",
            color: message.type === "error" ? "#991b1b" : "#065f46",
            fontSize: 14,
          }}
        >
          <AlertCircle size={16} />
          <span style={{ flex: 1 }}>{message.text}</span>
          <button
            onClick={() => setMessage(null)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              padding: 2,
              color: "inherit",
            }}
            type="button"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* ==================== Text Content Form ==================== */}
      {activeTab === "text" && (
        <form className="stack" onSubmit={submitTextDocument}>
          <div className="grid-two">
            <div>
              <label className="label">Title</label>
              <input
                className="input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Refund Policy"
                required
                disabled={submitting}
              />
            </div>

            <div>
              <label className="label">Document Type</label>
              <select
                className="input"
                value={documentType}
                onChange={(e) => setDocumentType(e.target.value)}
                disabled={submitting}
              >
                {documentTypes.map((type) => (
                  <option key={type} value={type}>
                    {type.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ gridColumn: "1 / -1" }}>
              <label className="label">Source URL (optional)</label>
              <input
                className="input"
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                placeholder="https://company.com/refund-policy"
                disabled={submitting}
              />
            </div>
          </div>

          <div>
            <label className="label">Content</label>
            <textarea
              className="input textarea"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste policy, FAQ, SOP, or support guideline content here..."
              rows={10}
              required
              disabled={submitting}
            />
          </div>

          <div>
            <button className="button" disabled={submitting} type="submit">
              {submitting ? "Creating..." : "Create Document"}
            </button>
          </div>
        </form>
      )}

      {/* ==================== File Upload Form ==================== */}
      {activeTab === "upload" && (
        <form className="stack" onSubmit={submitFileUpload}>
          {!selectedFile ? (
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: `2px dashed ${isDragging ? "#3b82f6" : "#d1d5db"}`,
                borderRadius: 8,
                padding: 32,
                textAlign: "center",
                cursor: "pointer",
                backgroundColor: isDragging ? "#eff6ff" : "transparent",
                transition: "all 0.2s",
              }}
            >
              <Upload
                size={32}
                style={{ margin: "0 auto 12px", color: "#9ca3af" }}
              />
              <p style={{ fontWeight: 500, marginBottom: 4 }}>
                Drop your file here or click to browse
              </p>
              <p style={{ fontSize: 13, color: "#6b7280" }}>
                Supports: {ALLOWED_EXTENSIONS.join(", ")}
              </p>
              <p style={{ fontSize: 13, color: "#6b7280" }}>
                Max size: {MAX_FILE_SIZE / 1024 / 1024}MB
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept={ALLOWED_EXTENSIONS.join(",")}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileSelect(file);
                }}
                style={{ display: "none" }}
              />
            </div>
          ) : (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: 14,
                border: "1px solid #d1d5db",
                borderRadius: 8,
              }}
            >
              <File size={24} style={{ color: "#3b82f6" }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontWeight: 500, marginBottom: 2, wordBreak: "break-all" }}>
                  {selectedFile.name}
                </p>
                <p style={{ fontSize: 13, color: "#6b7280" }}>
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
              <button
                onClick={clearFile}
                style={{ background: "none", border: "none", cursor: "pointer", padding: 4 }}
                type="button"
              >
                <X size={18} />
              </button>
            </div>
          )}

          <div className="grid-two">
            <div>
              <label className="label">
                Title{" "}
                <span style={{ fontWeight: 400, color: "#6b7280" }}>
                  (optional)
                </span>
              </label>
              <input
                className="input"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
                placeholder="Document title"
                disabled={submitting}
              />
            </div>

            <div>
              <label className="label">Document Type</label>
              <select
                className="input"
                value={uploadDocumentType}
                onChange={(e) => setUploadDocumentType(e.target.value)}
                disabled={submitting}
              >
                {documentTypes.map((type) => (
                  <option key={type} value={type}>
                    {type.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <button
              className="button"
              disabled={!selectedFile || submitting}
              type="submit"
            >
              {submitting ? "Uploading..." : "Upload Document"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}