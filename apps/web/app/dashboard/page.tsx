import { UserButton } from "@clerk/nextjs";

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-slate-50 px-6 py-8">
      <section className="mx-auto max-w-5xl">
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
              Phase 2
            </p>
            <h1 className="mt-2 text-3xl font-bold text-slate-950">
              SupportPilot Dashboard
            </h1>
            <p className="mt-2 text-sm text-slate-600">
              Auth, organization, users, roles, and RBAC foundation.
            </p>
          </div>

          <UserButton />
        </div>

        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-950">
            Next setup
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Create organization, sync user, and test protected backend routes.
          </p>
        </div>
      </section>
    </main>
  );
}