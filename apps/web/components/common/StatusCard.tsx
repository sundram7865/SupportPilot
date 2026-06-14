type StatusCardProps = {
  title: string;
  description: string;
  status: "ready" | "pending" | "blocked";
};

export function StatusCard({ title, description, status }: StatusCardProps) {
  const label = {
    ready: "Ready",
    pending: "Pending",
    blocked: "Blocked"
  }[status];

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <h3 className="font-semibold text-slate-950">{title}</h3>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
          {label}
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-slate-600">{description}</p>
    </div>
  );
}