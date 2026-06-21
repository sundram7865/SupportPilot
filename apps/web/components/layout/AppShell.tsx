"use client";

import { UserButton, useAuth, useUser } from "@clerk/nextjs";
import Link from "next/link";
import { useEffect, useState } from "react";

import { OrgSwitcher } from "@/components/layout/OrgSwitcher";
import { bootstrapAuth } from "@/lib/api";
import type { AuthMeResponse } from "@/types/api";

export function AppShell({
  title,
  subtitle,
  right,
  children,
}: {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
}) {
  const { getToken, isSignedIn } = useAuth();
  const { user } = useUser();

  const [me, setMe] = useState<AuthMeResponse | null>(null);
  const [orgId, setOrgId] = useState<string | null>(null);

  useEffect(() => {
    async function run() {
      try {
        const boot = await bootstrapAuth(isSignedIn ? getToken : undefined);
        setMe(boot.me);
        setOrgId(boot.orgId);
      } catch {
        // Page-level components show exact API errors.
      }
    }

    run();
  }, [getToken, isSignedIn]);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-logo">SupportPilot</div>
        <div className="sidebar-subtitle">Agentic support workspace</div>

        <nav className="nav-list">
          <Link className="nav-link" href="/dashboard">
            Dashboard
          </Link>

          <Link className="nav-link" href="/approvals">
            Approval Inbox
          </Link>
          <Link className="nav-link" href="/settings/organization">
            Organization Settings
        </Link>
        </nav>

        <div style={{ marginTop: 24 }}>
          <OrgSwitcher me={me} orgId={orgId} />
        </div>

        {isSignedIn ? (
          <div style={{ marginTop: 24 }}>
            <div className="muted" style={{ marginBottom: 8 }}>
              {user?.primaryEmailAddress?.emailAddress || user?.username}
            </div>

            <UserButton />
          </div>
        ) : null}
      </aside>

      <main className="main">
        <div className="page-header">
          <div>
            <div className="page-title">{title}</div>
            {subtitle ? <div className="page-subtitle">{subtitle}</div> : null}
          </div>

          {right}
        </div>

        {children}
      </main>
    </div>
  );
}