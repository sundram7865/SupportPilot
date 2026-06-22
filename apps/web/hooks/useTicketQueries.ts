"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";
import type { Ticket, TicketListResponse } from "@/types/api";

type GetToken = () => Promise<string | null>;

export type TicketListFilters = {
  status?: string;
  priority?: string;
  category?: string;
  search?: string;
};

export type CreateTicketPayload = {
  subject: string;
  description: string;
  customer_name?: string | null;
  customer_email: string;
  customer_phone?: string | null;
  external_order_id?: string | null;
  priority: string;
  category: string;
  source: string;
  metadata_json?: Record<string, unknown> | null;
};

function buildTicketQueryString(filters: TicketListFilters) {
  const params = new URLSearchParams();

  if (filters.status) params.set("status", filters.status);
  if (filters.priority) params.set("priority", filters.priority);
  if (filters.category) params.set("category", filters.category);
  if (filters.search) params.set("search", filters.search);

  params.set("limit", "50");
  params.set("offset", "0");

  const queryString = params.toString();
  return queryString ? `?${queryString}` : "";
}

export function useTickets({
  orgId,
  getToken,
  enabled,
  filters,
}: {
  orgId: string | null;
  getToken?: GetToken;
  enabled: boolean;
  filters: TicketListFilters;
}) {
  return useQuery({
    queryKey: [...queryKeys.tickets.lists(), orgId, filters],
    enabled: enabled && Boolean(orgId) && Boolean(getToken),
    queryFn: async () => {
      if (!orgId || !getToken) {
        throw new Error("Missing organization or auth token.");
      }

      const response = await apiFetch<TicketListResponse | Ticket[]>(
        `/tickets${buildTicketQueryString(filters)}`,
        {
          method: "GET",
          orgId,
          getToken,
        }
      );

      if (Array.isArray(response)) {
        return response;
      }

      return response.items || [];
    },
  });
}

export function useCreateTicket({
  orgId,
  getToken,
}: {
  orgId: string | null;
  getToken?: GetToken;
}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (payload: CreateTicketPayload) => {
      if (!orgId || !getToken) {
        throw new Error("Missing organization or auth token.");
      }

      return apiFetch<Ticket>("/tickets", {
        method: "POST",
        orgId,
        getToken,
        body: JSON.stringify(payload),
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: queryKeys.tickets.all,
      });
    },
  });
}