"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

import { clearStoredOrgId, syncAuthUser } from "@/lib/api";
import { bootstrapAuth } from "@/lib/api";
import { useWorkspaceStore } from "@/lib/workspace-store";

type SyncState = "idle" | "syncing" | "done" | "error";

export function AuthSyncGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const { isLoaded: authLoaded, isSignedIn, getToken } = useAuth();
  const { isLoaded: userLoaded, user } = useUser();

  const [syncState, setSyncState] = useState<SyncState>("idle");
  const [error, setError] = useState<string | null>(null);
  const syncedUserRef = useRef<string | null>(null);
  const setLoading = useWorkspaceStore((state) => state.setLoading);
  const setWorkspace = useWorkspaceStore((state) => state.setWorkspace);
  const setWorkspaceError = useWorkspaceStore((state) => state.setError);
  const resetWorkspace = useWorkspaceStore((state) => state.reset);

  const isPublicRoute =
    pathname.startsWith("/sign-in") ||
    pathname.startsWith("/sign-up") ||
    pathname.startsWith("/support") ||
    pathname.startsWith("/embed") ||
    pathname.startsWith("/widget");

  const primaryEmail = useMemo(() => {
    return (
      user?.primaryEmailAddress?.emailAddress ||
      user?.emailAddresses?.[0]?.emailAddress ||
      null
    );
  }, [user]);

  useEffect(() => {
    if (isPublicRoute) {
      return;
    }

    let cancelled = false;

    async function run() {
      if (!authLoaded || !userLoaded) {
        return;
      }

      if (!isSignedIn) {
        syncedUserRef.current = null;
        clearStoredOrgId();
        resetWorkspace();

        if (!cancelled) {
          setSyncState("done");
        }

        return;
      }

      if (!user) {
        if (!cancelled) {
          setError("Signed in, but Clerk user is not loaded.");
          setSyncState("error");
        }

        return;
      }

      if (!primaryEmail) {
        if (!cancelled) {
          setError("Your Clerk account does not have a primary email.");
          setSyncState("error");
        }

        return;
      }

      try {
        if (syncedUserRef.current === user.id) {
          if (!cancelled) {
            setSyncState("done");
          }
          return;
        }

        if (!cancelled) {
          setError(null);
          setSyncState("syncing");
          setLoading();
        }

        await syncAuthUser(getToken, {
          clerk_user_id: user.id,
          email: primaryEmail,
          name: user.fullName || user.username || null,
          avatar_url: user.imageUrl || null,
        });

        const boot = await bootstrapAuth(getToken);
        if (cancelled) return;

        setWorkspace(boot.me, boot.orgId);
        syncedUserRef.current = user.id;

        if (!cancelled) {
          setSyncState("done");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Auth sync failed.");
          setWorkspaceError(err instanceof Error ? err.message : "Auth sync failed.");
          setSyncState("error");
        }
      }
    }

    run();

    return () => {
      cancelled = true;
    };
  }, [
    isPublicRoute,
    authLoaded,
    userLoaded,
    isSignedIn,
    user,
    primaryEmail,
    getToken,
    resetWorkspace,
    setLoading,
    setWorkspace,
    setWorkspaceError,
  ]);

  // Public customer routes must never go to Clerk/auth sync.
  // These are customer-facing:
  // /support/[organizationSlug]
  // /embed/support?org=...
  // /widget/supportpilot-widget.js
  if (isPublicRoute) {
    return <>{children}</>;
  }

  if (
    !authLoaded ||
    !userLoaded ||
    syncState === "idle" ||
    syncState === "syncing"
  ) {
    return (
      <main className="auth-page">
        <div className="card" style={{ maxWidth: 420 }}>
          <h2 style={{ marginTop: 0 }}>Preparing workspace...</h2>
          <p className="muted">
            Syncing your Clerk account with SupportPilot.
          </p>
        </div>
      </main>
    );
  }

  if (syncState === "error") {
    return (
      <main className="auth-page">
        <div className="card" style={{ maxWidth: 520 }}>
          <h2 style={{ marginTop: 0 }}>Authentication sync failed</h2>
          <p className="muted">{error}</p>
        </div>
      </main>
    );
  }

  return <>{children}</>;
}