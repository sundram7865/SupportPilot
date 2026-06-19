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

export async function streamTicketTimeline(params: {
  ticketId: string;
  getToken?: () => Promise<string | null>;
  onEvent: (payload: RealtimePayload) => void;
  onError?: (error: unknown) => void;
  signal?: AbortSignal;
}) {
  const headers = await getHeaders({
    json: false,
    getToken: params.getToken,
  });

  return fetchEventSource(
    `${API_URL}/realtime/tickets/${params.ticketId}/timeline/stream`,
    {
      method: "GET",
      headers,
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

export async function streamOrganization(params: {
  getToken?: () => Promise<string | null>;
  onEvent: (payload: RealtimePayload) => void;
  onError?: (error: unknown) => void;
  signal?: AbortSignal;
}) {
  const headers = await getHeaders({
    json: false,
    getToken: params.getToken,
  });

  return fetchEventSource(`${API_URL}/realtime/organizations/stream`, {
    method: "GET",
    headers,
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