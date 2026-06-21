"use client";

import { useAuth, useUser } from "@clerk/nextjs";
import { useEffect, useMemo, useState } from "react";

import { clearStoredOrgId, syncAuthUser } from "@/lib/api";

type SyncState = "idle" | "syncing" | "done" | "error";

export function AuthSyncGate({ children }: { children: React.ReactNode }) {
  const { isLoaded: authLoaded, isSignedIn, getToken } = useAuth();
  const { isLoaded: userLoaded, user } = useUser();

  const [syncState, setSyncState] = useState<SyncState>("idle");
  const [error, setError] = useState<string | null>(null);

  const primaryEmail = useMemo(() => {
    return (
      user?.primaryEmailAddress?.emailAddress ||
      user?.emailAddresses?.[0]?.emailAddress ||
      null
    );
  }, [user]);

  useEffect(() => {
    let cancelled = false;

    async function run() {
      if (!authLoaded || !userLoaded) {
        return;
      }

      if (!isSignedIn) {
        clearStoredOrgId();
        setSyncState("done");
        return;
      }

      if (!user) {
        setError("Signed in, but Clerk user is not loaded.");
        setSyncState("error");
        return;
      }

      if (!primaryEmail) {
        setError("Your Clerk account does not have a primary email.");
        setSyncState("error");
        return;
      }

      try {
        setSyncState("syncing");

        await syncAuthUser(getToken, {
          clerk_user_id: user.id,
          email: primaryEmail,
          name: user.fullName || user.username || null,
          avatar_url: user.imageUrl || null,
        });

        if (!cancelled) {
          setSyncState("done");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Auth sync failed.");
          setSyncState("error");
        }
      }
    }

    run();

    return () => {
      cancelled = true;
    };
  }, [authLoaded, userLoaded, isSignedIn, user, primaryEmail, getToken]);

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