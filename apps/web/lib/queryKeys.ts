export const queryKeys = {
  auth: {
    me: ["auth", "me"] as const,
  },

  tickets: {
    all: ["tickets"] as const,
    lists: () => ["tickets", "list"] as const,
    detail: (ticketId: string) => ["tickets", "detail", ticketId] as const,
    timeline: (ticketId: string) =>
      ["tickets", "timeline", ticketId] as const,
  },

  approvals: {
    all: ["approvals"] as const,
    pending: ["approvals", "pending"] as const,
  },

  organization: {
    current: ["organization", "current"] as const,
    members: ["organization", "members"] as const,
    invitations: ["organization", "invitations"] as const,
  },

  integrations: {
    urbankart: ["integrations", "urbankart"] as const,
    logs: ["integrations", "logs"] as const,
  },

  knowledge: {
    documents: (orgId: string | null) => ["knowledge", orgId, "documents"] as const,
    chunks: (orgId: string | null, documentId: string) =>
      ["knowledge", orgId, "documents", documentId, "chunks"] as const,
    search: (orgId: string | null, query: string) =>
      ["knowledge", orgId, "search", query] as const,
  },
};