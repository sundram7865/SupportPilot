import { StatusCard } from "@/components/common/StatusCard";

export default function HomePage() {
  return (
    <main className="min-h-screen px-6 py-10">
      <section className="mx-auto max-w-5xl">
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
            Phase 1 Foundation
          </p>

          <h1 className="mt-3 text-4xl font-bold tracking-tight text-slate-950">
            SupportPilot
          </h1>

          <p className="mt-4 max-w-3xl text-base leading-7 text-slate-600">
            Agentic AI customer-support platform for e-commerce brands.
            This phase sets up the frontend, FastAPI backend, Celery worker,
            PostgreSQL, Redis, and UrbanKart mock support APIs.
          </p>
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <StatusCard
            title="Frontend"
            description="Next.js, TypeScript, Tailwind, and dashboard shell are ready."
            status="ready"
          />

          <StatusCard
            title="SupportPilot API"
            description="FastAPI base service with health, readiness, and UrbanKart integration routes."
            status="ready"
          />

          <StatusCard
            title="Worker"
            description="Celery worker foundation is ready for future AI, embedding, SLA, and notification jobs."
            status="ready"
          />

          <StatusCard
            title="UrbanKart Mock API"
            description="Mock order, payment, shipment, customer, refund, and replacement support APIs."
            status="ready"
          />
        </div>

        <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-950">
            Next Phase
          </h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Phase 2 will add authentication, organization setup, users,
            roles, permissions, and backend RBAC enforcement.
          </p>
        </div>
      </section>
    </main>
  );
}