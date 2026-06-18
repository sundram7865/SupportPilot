import type { AuthMeResponse } from "@/types/api";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getBaseDevHeaders(): Record<string, string> {
  return {
    "x-dev-user-id": process.env.NEXT_PUBLIC_DEV_USER_ID || "dev-owner-1",
    "x-dev-email":
      process.env.NEXT_PUBLIC_DEV_EMAIL || "owner@urbankart.demo",
    "x-dev-name": process.env.NEXT_PUBLIC_DEV_NAME || "UrbanKart Owner",
  };
}

export function getOrgId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("supportpilot.orgId");
}

export function setOrgId(orgId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem("supportpilot.orgId", orgId);
}

export function getHeaders(options?: {
  orgId?: string | null;
  json?: boolean;
}): Record<string, string> {
  const orgId = options?.orgId ?? getOrgId();

  const headers: Record<string, string> = {
    ...getBaseDevHeaders(),
  };

  if (options?.json !== false) {
    headers["Content-Type"] = "application/json";
  }

  if (orgId) {
    headers["x-organization-id"] = orgId;
  }

  return headers;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { orgId?: string | null } = {}
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...getHeaders({
        orgId: options.orgId,
        json: !(options.body instanceof FormData),
      }),
      ...(options.headers || {}),
    },
    cache: "no-store",
  });

  const text = await response.text();

  let data: any = null;

  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    const message =
      typeof data === "object" && data?.detail
        ? data.detail
        : `Request failed: ${response.status}`;

    throw new Error(message);
  }

  return data as T;
}

export async function bootstrapAuth(): Promise<AuthMeResponse> {
  const me = await apiFetch<AuthMeResponse>("/auth/me", {
    method: "GET",
    orgId: null,
  });

  const firstOrgId = me.organizations?.[0]?.id;

  if (firstOrgId) {
    setOrgId(firstOrgId);
  }

  return me;
}

export async function getApiHealth() {
  const response = await fetch(`${API_URL}/health`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error("Failed to fetch API health");
  }

  return response.json();
}

export async function testUrbanKartConnection() {
  const response = await fetch(`${API_URL}/integrations/urbankart/test-connection`, {
    method: "POST",
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error("Failed to test UrbanKart connection");
  }

  return response.json();
}
