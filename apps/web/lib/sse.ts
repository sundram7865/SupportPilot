import { fetchEventSource } from "@microsoft/fetch-event-source";

import { API_URL, getHeaders } from "@/lib/api";

export type RealtimePayload = {
  type: string;
  organization_id?: string;
  ticket_id?: string;
  event?: any;
  message?: string;
  created_at?: string;
};

export function streamTicketTimeline(params: {
  ticketId: string;
  onEvent: (payload: RealtimePayload) => void;
  onError?: (error: unknown) => void;
  signal?: AbortSignal;
}) {
  return fetchEventSource(
    `${API_URL}/realtime/tickets/${params.ticketId}/timeline/stream`,
    {
      method: "GET",
      headers: getHeaders({ json: false }),
      signal: params.signal,
      onmessage(message) {
        if (!message.data) return;

        try {
          params.onEvent(JSON.parse(message.data));
        } catch {
          params.onEvent({
            type: "raw",
            message: message.data,
          });
        }
      },
      onerror(error) {
        params.onError?.(error);
        throw error;
      },
      openWhenHidden: true,
    }
  );
}

export function streamOrganization(params: {
  onEvent: (payload: RealtimePayload) => void;
  onError?: (error: unknown) => void;
  signal?: AbortSignal;
}) {
  return fetchEventSource(`${API_URL}/realtime/organizations/stream`, {
    method: "GET",
    headers: getHeaders({ json: false }),
    signal: params.signal,
    onmessage(message) {
      if (!message.data) return;

      try {
        params.onEvent(JSON.parse(message.data));
      } catch {
        params.onEvent({
          type: "raw",
          message: message.data,
        });
      }
    },
    onerror(error) {
      params.onError?.(error);
      throw error;
    },
    openWhenHidden: true,
  });
}