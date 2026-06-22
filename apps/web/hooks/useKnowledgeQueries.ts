"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import type {
  CreateKnowledgeDocumentPayload,
  KnowledgeChunk,
  KnowledgeDocument,
  KnowledgeSearchResult,
} from "@/types/api";

type GetToken = () => Promise<string | null>;

type KnowledgeDocumentListResponse = {
  items: KnowledgeDocument[];
  total: number;
  limit: number;
  offset: number;
};

type KnowledgeSearchResponse = {
  query: string;
  results: KnowledgeSearchResult[];
};

export function useKnowledgeDocuments({
  getToken,
  enabled,
}: {
  getToken?: GetToken;
  enabled: boolean;
}) {
  return useQuery({
    queryKey: queryKeys.knowledge.documents,
    enabled: enabled && Boolean(getToken),
    queryFn: async () => {
      if (!getToken) {
        throw new Error("Missing auth token getter.");
      }

      const response = await apiFetch<KnowledgeDocumentListResponse>(
        "/knowledge/documents",
        {
          method: "GET",
          getToken,
        }
      );

      return response.items || [];
    },
  });
}

export function useKnowledgeChunks({
  documentId,
  getToken,
  enabled,
}: {
  documentId?: string | null;
  getToken?: GetToken;
  enabled: boolean;
}) {
  return useQuery({
    queryKey: documentId
      ? queryKeys.knowledge.chunks(documentId)
      : ["knowledge", "documents", "no-document", "chunks"],
    enabled: enabled && Boolean(getToken) && Boolean(documentId),
    queryFn: async () => {
      if (!getToken || !documentId) {
        throw new Error("Missing document or auth token getter.");
      }

      return apiFetch<KnowledgeChunk[]>(
        `/knowledge/documents/${documentId}/chunks`,
        {
          method: "GET",
          getToken,
        }
      );
    },
  });
}

export function useCreateKnowledgeDocument({
  getToken,
}: {
  getToken?: GetToken;
}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateKnowledgeDocumentPayload) => {
      if (!getToken) {
        throw new Error("Missing auth token getter.");
      }

      return apiFetch<KnowledgeDocument>("/knowledge/documents", {
        method: "POST",
        getToken,
        body: JSON.stringify(payload),
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.knowledge.documents,
      });
    },
  });
}

export function useIngestKnowledgeDocument({
  getToken,
}: {
  getToken?: GetToken;
}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (documentId: string) => {
      if (!getToken) {
        throw new Error("Missing auth token getter.");
      }

      return apiFetch(`/knowledge/documents/${documentId}/ingest`, {
        method: "POST",
        getToken,
      });
    },
    onSuccess: async (_data, documentId) => {
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: queryKeys.knowledge.documents,
        }),
        queryClient.invalidateQueries({
          queryKey: queryKeys.knowledge.chunks(documentId),
        }),
      ]);
    },
  });
}

export function useDeleteKnowledgeDocument({
  getToken,
}: {
  getToken?: GetToken;
}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (documentId: string) => {
      if (!getToken) {
        throw new Error("Missing auth token getter.");
      }

      return apiFetch(`/knowledge/documents/${documentId}`, {
        method: "DELETE",
        getToken,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.knowledge.documents,
      });
    },
  });
}

export function useSearchKnowledge({
  getToken,
}: {
  getToken?: GetToken;
}) {
  return useMutation({
    mutationFn: async ({
      query,
      limit,
    }: {
      query: string;
      limit: number;
    }) => {
      if (!getToken) {
        throw new Error("Missing auth token getter.");
      }

      const response = await apiFetch<KnowledgeSearchResponse>(
        "/knowledge/search",
        {
          method: "POST",
          getToken,
          body: JSON.stringify({
            query,
            limit,
          }),
        }
      );

      return response.results || [];
    },
  });
}