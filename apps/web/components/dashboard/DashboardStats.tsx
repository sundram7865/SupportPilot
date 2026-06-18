import type { Ticket } from "@/types/api";

export function DashboardStats({ tickets }: { tickets: Ticket[] }) {
  const open = tickets.filter((ticket) => ticket.status === "OPEN").length;
  const urgent = tickets.filter((ticket) => ticket.priority === "URGENT").length;
  const waiting = tickets.filter((ticket) =>
    ticket.status.includes("WAITING")
  ).length;

  return (
    <div className="grid grid-3">
      <div className="stat-card">
        <div className="muted">Total tickets</div>
        <div className="stat-value">{tickets.length}</div>
      </div>

      <div className="stat-card">
        <div className="muted">Open</div>
        <div className="stat-value">{open}</div>
      </div>

      <div className="stat-card">
        <div className="muted">Urgent / Waiting</div>
        <div className="stat-value">{urgent + waiting}</div>
      </div>
    </div>
  );
}