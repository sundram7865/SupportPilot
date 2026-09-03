"use client";

import { UserButton, useAuth, useUser } from "@clerk/nextjs";
import Link from "next/link";
import type { ReactNode } from "react";

import { OrgSwitcher } from "@/components/layout/OrgSwitcher";
import { useWorkspaceStore } from "@/lib/workspace-store";

export function AppShell({
  title,
  subtitle,
  right,
  children,
}: {
  title: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
}) {
  const { isSignedIn } = useAuth();
  const { user } = useUser();

  const me = useWorkspaceStore((state) => state.me);
  const orgId = useWorkspaceStore((state) => state.orgId);
  const setOrgId = useWorkspaceStore((state) => state.setOrgId);

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

          <Link className="nav-link" href="/audit-logs">
            Audit Logs
          </Link>

          <Link className="nav-link" href="/settings/organization">
            Organization Settings
          </Link>

          <Link className="nav-link" href="/settings/integrations">
            Integration Settings
          </Link>

          <Link className="nav-link" href="/settings/knowledge">
            Knowledge Base
          </Link>
        </nav>

        <div style={{ marginTop: 24 }}>
          <OrgSwitcher me={me} orgId={orgId} onChanged={setOrgId} />
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