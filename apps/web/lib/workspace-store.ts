"use client";

import { create } from "zustand";

import type { AuthMeResponse } from "@/types/api";

type WorkspaceState = {
  me: AuthMeResponse | null;
  orgId: string | null;
  status: "idle" | "loading" | "ready" | "error";
  error: string | null;
  setLoading: () => void;
  setWorkspace: (me: AuthMeResponse, orgId: string) => void;
  setOrgId: (orgId: string) => void;
  setError: (error: string) => void;
  reset: () => void;
};

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  me: null,
  orgId: null,
  status: "idle",
  error: null,
  setLoading: () => set({ status: "loading", error: null }),
  setWorkspace: (me, orgId) => set({ me, orgId, status: "ready", error: null }),
  setOrgId: (orgId) => set({ orgId }),
  setError: (error) => set({ status: "error", error }),
  reset: () => set({ me: null, orgId: null, status: "idle", error: null }),
}));
