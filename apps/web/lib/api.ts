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

export function getStoredOrgId(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("supportpilot.orgId");
}

export const getOrgId = getStoredOrgId;

export function setStoredOrgId(orgId: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem("supportpilot.orgId", orgId);
}

export function clearStoredOrgId() {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem("supportpilot.orgId");
}

function extractOrgId(me: any): string | null {
  if (me?.organizations?.[0]?.id) {
    return me.organizations[0].id;
  }

  if (me?.memberships?.[0]?.organization_id) {
    return me.memberships[0].organization_id;
  }

  if (me?.memberships?.[0]?.organization?.id) {
    return me.memberships[0].organization.id;
  }

  if (me?.organization?.id) {
    return me.organization.id;
  }

  return null;
}

export async function bootstrapAuth(
  getToken?: () => Promise<string | null>
): Promise<{
  me: AuthMeResponse;
  orgId: string;
}> {
  let me = await apiFetch<AuthMeResponse>("/auth/me", {
    method: "GET",
    orgId: null,
    getToken,
  });

  let orgId = extractOrgId(me);

  if (!orgId) {
    await apiFetch("/auth/bootstrap-org", {
      method: "POST",
      orgId: null,
      getToken,
      body: JSON.stringify({}),
    });

    me = await apiFetch<AuthMeResponse>("/auth/me", {
      method: "GET",
      orgId: null,
      getToken,
    });

    orgId = extractOrgId(me);
  }

  if (!orgId) {
    throw new Error("No organization found for current user.");
  }

  setStoredOrgId(orgId);

  return {
    me,
    orgId,
  };
}

async function resolveOrgId(
  path: string,
  explicitOrgId?: string | null,
  getToken?: () => Promise<string | null>
) {
  if (explicitOrgId === null) return null;
  if (explicitOrgId) return explicitOrgId;
  if (path === "/auth/me" || path === "/auth/bootstrap-org") return null;

  const stored = getStoredOrgId();

  if (stored) return stored;

  const boot = await bootstrapAuth(getToken);
  return boot.orgId;
}

async function getAuthHeader(
  getToken?: () => Promise<string | null>
): Promise<Record<string, string>> {
  if (!getToken) {
    return getBaseDevHeaders();
  }

  const token = await getToken();

  if (!token) {
    return getBaseDevHeaders();
  }

  return {
    Authorization: `Bearer ${token}`,
  };
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & {
    orgId?: string | null;
    getToken?: () => Promise<string | null>;
  } = {}
): Promise<T> {
  const orgId = await resolveOrgId(path, options.orgId, options.getToken);
  const authHeaders = await getAuthHeader(options.getToken);

  const headers: Record<string, string> = {
    ...authHeaders,
  };

  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (orgId) {
    headers["x-organization-id"] = orgId;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...headers,
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

export async function getHeaders(options?: {
  orgId?: string | null;
  json?: boolean;
  getToken?: () => Promise<string | null>;
}): Promise<Record<string, string>> {
  const orgId = options?.orgId ?? getStoredOrgId();
  const authHeaders = await getAuthHeader(options?.getToken);

  const headers: Record<string, string> = {
    ...authHeaders,
  };

  if (options?.json !== false) {
    headers["Content-Type"] = "application/json";
  }

  if (orgId) {
    headers["x-organization-id"] = orgId;
  }

  return headers;
}