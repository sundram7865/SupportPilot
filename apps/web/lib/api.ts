import type { AuthMeResponse } from "@/types/api";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type ClerkSyncPayload = {
  clerk_user_id: string;
  email: string;
  name?: string | null;
  avatar_url?: string | null;
};

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

function getMembershipOrgIds(me: AuthMeResponse): string[] {
  return (me.memberships || [])
    .map((membership) => membership.organization_id)
    .filter(Boolean) as string[];
}

function extractOrgId(me: AuthMeResponse): string | null {
  const storedOrgId = getStoredOrgId();
  const membershipOrgIds = getMembershipOrgIds(me);

  if (storedOrgId && membershipOrgIds.includes(storedOrgId)) {
    return storedOrgId;
  }

  if (me.organizations?.[0]?.id) {
    return me.organizations[0].id;
  }

  if (me.memberships?.[0]?.organization_id) {
    return me.memberships[0].organization_id;
  }

  if (me.memberships?.[0]?.organization?.id) {
    return me.memberships[0].organization.id;
  }

  if (me.organization?.id) {
    return me.organization.id;
  }

  return null;
}

export async function syncAuthUser(
  getToken: () => Promise<string | null>,
  payload: ClerkSyncPayload
): Promise<void> {
  const token = await getToken();

  if (!token) {
    throw new Error("Missing Clerk token.");
  }

  const response = await fetch(`${API_URL}/auth/sync`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let message = `Auth sync failed with status ${response.status}`;

    try {
      const data = await response.json();
      message = data?.detail || message;
    } catch {
      // Ignore parse error.
    }

    throw new Error(message);
  }
}

export async function bootstrapAuth(
  getToken: () => Promise<string | null>
): Promise<{ me: AuthMeResponse; orgId: string }> {
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

  return { me, orgId };
}

async function resolveOrgId(
  path: string,
  explicitOrgId: string | null | undefined,
  getToken?: () => Promise<string | null>
): Promise<string | null> {
  if (explicitOrgId !== undefined) {
    return explicitOrgId;
  }

  if (
    path.startsWith("/auth") ||
    path === "/" ||
    path.startsWith("/health") ||
    path.startsWith("/ready")
  ) {
    return null;
  }

  const storedOrgId = getStoredOrgId();

  if (storedOrgId) {
    return storedOrgId;
  }

  if (!getToken) {
    throw new Error("Missing Clerk token getter.");
  }

  const boot = await bootstrapAuth(getToken);
  return boot.orgId;
}

async function getAuthHeader(
  getToken?: () => Promise<string | null>
): Promise<Record<string, string>> {
  if (!getToken) {
    throw new Error("Missing Clerk token getter.");
  }

  const token = await getToken();

  if (!token) {
    throw new Error("Missing Clerk token.");
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
  const { orgId, getToken, headers, ...fetchOptions } = options;

  const resolvedOrgId = await resolveOrgId(path, orgId, getToken);

  const authHeaders = await getAuthHeader(getToken);

  const finalHeaders: Record<string, string> = {
    ...authHeaders,
    ...(fetchOptions.body && !(fetchOptions.body instanceof FormData)
      ? { "Content-Type": "application/json" }
      : {}),
    ...(resolvedOrgId ? { "x-organization-id": resolvedOrgId } : {}),
    ...(headers as Record<string, string> | undefined),
  };

  const response = await fetch(`${API_URL}${path}`, {
    ...fetchOptions,
    headers: finalHeaders,
  });

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`;

    try {
      const data = await response.json();
      message = data?.error?.message || data?.detail || message;
    } catch {
      // Ignore parse errors.
    }

    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

// ============================================================================
// File Upload Helper - for multipart/form-data uploads
// ============================================================================
export async function uploadFile<T>(
  path: string,
  formData: FormData,
  options: {
    getToken?: () => Promise<string | null>;
  } = {}
): Promise<T> {
  const { getToken } = options;

  const authHeaders = await getAuthHeader(getToken);
  const orgId = getStoredOrgId();

  const headers: Record<string, string> = {
    ...authHeaders,
    ...(orgId ? { "x-organization-id": orgId } : {}),
    // DO NOT set Content-Type - browser sets it automatically with boundary
  };

  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    let message = `Upload failed with status ${response.status}`;

    try {
      const data = await response.json();
      message = data?.error?.message || data?.detail || message;
    } catch {
      // Ignore parse errors.
    }

    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function getHeaders(options?: {
  orgId?: string | null;
  json?: boolean;
  getToken?: () => Promise<string | null>;
}): Promise<Record<string, string>> {
  const resolvedOrgId = await resolveOrgId(
    "",
    options?.orgId,
    options?.getToken
  );

  const authHeaders = await getAuthHeader(options?.getToken);

  return {
    ...authHeaders,
    ...(options?.json === false ? {} : { "Content-Type": "application/json" }),
    ...(resolvedOrgId ? { "x-organization-id": resolvedOrgId } : {}),
  };
}