import Link from "next/link";

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
        </nav>
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