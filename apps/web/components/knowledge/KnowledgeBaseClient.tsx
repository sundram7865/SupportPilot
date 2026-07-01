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

  useEffect(() => {
    loadDocuments();
  }, [isSignedIn]);

  return (
    <AppShell
      title="Knowledge Base"
      subtitle="Manage company policies, SOPs, FAQs, and searchable support knowledge."
    >
      {error ? <ErrorBanner message={error} /> : null}

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