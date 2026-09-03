"use client";

import { useAuth } from "@clerk/nextjs";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/layout/AppShell";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { LoadingState } from "@/components/ui/LoadingState";
import { Section } from "@/components/ui/Section";
import { CreateKnowledgeDocumentForm } from "@/components/knowledge/CreateKnowledgeDocumentForm";
import { KnowledgeChunksPanel } from "@/components/knowledge/KnowledgeChunksPanel";
import { KnowledgeDocumentsTable } from "@/components/knowledge/KnowledgeDocumentsTable";
import { KnowledgeSearchPanel } from "@/components/knowledge/KnowledgeSearchPanel";
import { apiFetch, bootstrapAuth } from "@/lib/api";
import type {
  AuthMeResponse,
  KnowledgeChunk,
  KnowledgeDocument,
} from "@/types/api";

export function KnowledgeBaseClient() {
  const { getToken, isSignedIn } = useAuth();

  const [me, setMe] = useState<AuthMeResponse | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [selectedDocument, setSelectedDocument] =
    useState<KnowledgeDocument | null>(null);
  const [chunks, setChunks] = useState<KnowledgeChunk[]>([]);
  const [loading, setLoading] = useState(true);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const tokenGetter = isSignedIn ? getToken : undefined;

  async function loadDocuments() {
    if (!tokenGetter) return;

    try {
      setLoading(true);
      setError(null);

      const boot = await bootstrapAuth(tokenGetter);
      setMe(boot.me);
      setOrgId(boot.orgId);

      const response = await apiFetch<{
        items: KnowledgeDocument[];
        total: number;
        limit: number;
        offset: number;
      }>("/knowledge/documents", {
        method: "GET",
        getToken: tokenGetter,
      });

      setDocuments(response.items || []);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load knowledge base."
      );
    } finally {
      setLoading(false);
    }
  }

  async function loadChunks(document: KnowledgeDocument) {
    if (!tokenGetter) return;

    try {
      setSelectedDocument(document);
      setChunksLoading(true);

      const response = await apiFetch<KnowledgeChunk[]>(
        `/knowledge/documents/${document.id}/chunks`,
        {
          method: "GET",
          getToken: tokenGetter,
        }
      );

      setChunks(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load chunks.");
    } finally {
      setChunksLoading(false);
    }
  }

  async function downloadDocument(document: KnowledgeDocument) {
    if (!tokenGetter || !document.cloudinary_public_id) {
      setError("No file available for download.");
      return;
    }

    try {
      const response = await apiFetch<{
        download_url: string;
        expires_in: number;
        file_name: string;
        file_size: number;
        file_type: string;
      }>(`/knowledge/documents/${document.id}/download?expiration=3600`, {
        method: "GET",
        getToken: tokenGetter,
      });

      // Create a hidden anchor to trigger download
      const link = window.document.createElement("a");
      link.href = response.download_url;
      link.download = response.file_name || document.title;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      window.document.body.appendChild(link);
      link.click();
      window.document.body.removeChild(link);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to download document."
      );
    }
  }

  useEffect(() => {
    loadDocuments();
  }, [isSignedIn]);

  return (
    <AppShell
      title="Knowledge Base"
      subtitle="Manage company policies, SOPs, FAQs, and searchable support knowledge."
    >
      {error ? (
        <ErrorBanner
          message={error}
          onDismiss={() => setError(null)}
        />
      ) : null}

      {loading ? (
        <LoadingState message="Loading knowledge base..." />
      ) : (
        <div className="stack">
          <Section title="Create Knowledge Document">
            <CreateKnowledgeDocumentForm
              getToken={tokenGetter}
              onCreated={loadDocuments}
            />
          </Section>

          <Section title="Documents">
            <KnowledgeDocumentsTable
              documents={documents}
              getToken={tokenGetter}
              onChanged={loadDocuments}
              onViewChunks={loadChunks}
              onDownload={downloadDocument}
            />
          </Section>

          <Section title="Search Knowledge Base">
            <KnowledgeSearchPanel getToken={tokenGetter} />
          </Section>

          <Section
            title={
              selectedDocument
                ? `Chunks: ${selectedDocument.title}`
                : "Document Chunks"
            }
          >
            <KnowledgeChunksPanel
              chunks={chunks}
              loading={chunksLoading}
              selectedDocument={selectedDocument}
            />
          </Section>
        </div>
      )}
    </AppShell>
  );
}