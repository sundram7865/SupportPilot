# SupportPilot

SupportPilot is an agentic customer support platform for ecommerce and direct to consumer companies. It combines multi tenant ticket operations, Clerk authentication, organization and role management, ecommerce integrations, policy grounded retrieval, LangGraph agent workflows, controlled tools, human approvals, reply drafts, realtime timelines, SLA monitoring, audit logs, and analytics.

The central rule is:

```txt
The AI may reason and recommend.
The backend decides what is allowed.
Sensitive actions require human approval.
Every important action is recorded.
```

SupportPilot is not a prompt to answer chatbot. It is a support operations system where AI works inside backend enforced boundaries.

## Contents

1. Architecture
2. Repository and services
3. Frontend
4. Authentication and organizations
5. Ticketing
6. Ecommerce integrations
7. Knowledge and RAG
8. Agent workflow
9. Tools and approvals
10. Replies and realtime
11. SLA and background work
12. Database overview
13. API surface
14. Configuration
15. Local development
16. Free MVP operation
17. Optional Celery operation
18. Demo flows
19. Testing
20. Tradeoffs and limitations

## Architecture

```txt
Customer or support agent
          |
          v
Next.js frontend
          |
          v
FastAPI API
          |
          +── PostgreSQL and pgvector
          +── Redis
          +── Clerk
          +── Gemini and optional Groq evaluation
          +── Ecommerce provider API
```

The complete workflow is:

```txt
Ticket intake
→ Ticket, first message, timeline event, SLA deadlines
→ Agent run manually started in v1
→ Context loaded
→ Knowledge retrieved
→ Category and priority classified
→ Risk detected
→ Tools planned
→ Safe tools executed or risky tools blocked
→ Human approval when required
→ Response drafted
→ Policy decision
→ Reply draft, escalation, request for information, or no action
→ Timeline and audit records
```

## Repository

```txt
SupportPilot/
├── apps/api
│   ├── app/common
│   ├── app/core
│   ├── app/db
│   ├── app/modules
│   │   ├── agent, analytics, approvals, audit, auth
│   │   ├── external, integrations, internal, knowledge
│   │   ├── organizations, public, realtime, replies
│   │   ├── tickets, tools, users
│   ├── app/scripts
│   ├── app/worker
│   ├── alembic
│   ├── tests
│   ├── Dockerfile
│   └── requirements.txt
├── apps/web
├── apps/urbankart-mock-api
├── apps/worker
├── docs/SYSTEM_DESIGN.md
├── docs/DEMO_GUIDE.md
├── docker-compose.yml
├── docker-compose.prod.yml
└── .env.example
```

## Runtime Services

```txt
web                 Next.js dashboard and public pages, used by the free MVP
api                 FastAPI business workflows, required
PostgreSQL          Durable records and vectors, required and can be managed
Redis               Rate limits, events, and optional Celery broker
urbankart-mock-api  Demo ecommerce provider
worker              Optional Celery task process
celery-beat         Optional periodic scheduler
```

## Frontend

The frontend uses Next.js, TypeScript, Clerk, Zustand, TanStack Query, SSE, and Lucide icons.

Routes:

```txt
/sign-in
/sign-up
/dashboard
/tickets/{ticketId}
/approvals
/audit-logs
/settings/organization
/settings/integrations
/settings/knowledge
/support/{organizationSlug}
/embed/support
/e2e-health
```

`AuthSyncGate` synchronizes Clerk once per user and bootstraps a local organization only when needed. `workspace-store.ts` keeps `me`, `orgId`, `status`, and `error`. `AppShell` and organization switching consume this shared state.

The API client sends:

```txt
Authorization: Bearer <Clerk token>
x-organization-id: <current organization>
```

The frontend renders loading, partial failure, action failure, and realtime states. It never owns permissions, approval rules, lifecycle rules, or tool safety.

## Authentication and Organizations

```txt
Clerk sign in or sign up
→ POST /auth/sync
→ Verify Clerk JWT
→ Create or update local user
→ Accept pending email invitations
→ GET /auth/me
→ Create organization only when no membership exists
→ Store current organization ID
```

Invitation behavior:

```txt
Owner invites email
→ Pending invitation stored
→ Person signs up through Clerk
→ /auth/sync matches normalized email
→ ACTIVE membership created
→ Invitation becomes ACCEPTED
```

The current product does not send invitation email or use invitation tokens. Email delivery is an external responsibility.

Roles:

```txt
OWNER, ADMIN, MANAGER, SUPPORT_AGENT, VIEWER
```

Permission areas:

```txt
Organization, team, tickets, knowledge, agent, audit, analytics,
tools, approvals, and replies
```

Production requires `DEV_AUTH_ENABLED=false`, Clerk issuer and JWKS configuration, strict CORS, strong secrets, and no localhost origins.

## Ticketing

Ticket creation creates one transaction containing:

```txt
Ticket
Initial public TicketMessage
TicketTimelineEvent
First response and resolution SLA deadlines
```

Categories:

```txt
ORDER_STATUS, PAYMENT_ISSUE, REFUND_REQUEST, RETURN_REQUEST,
DAMAGED_PRODUCT, CANCEL_ORDER, INVOICE_REQUEST, WARRANTY_REQUEST,
GENERAL_FAQ, LEGAL_RISK, OTHER
```

Priorities:

```txt
LOW, MEDIUM, HIGH, URGENT
```

Statuses:

```txt
OPEN, IN_PROGRESS, WAITING_FOR_CUSTOMER,
WAITING_FOR_INTERNAL_REVIEW, RESOLVED, CLOSED
```

Resolved and closed tickets may be reopened through the lifecycle state machine. Invalid transitions are blocked and tracked.

## Ecommerce Integrations

Companies do not change `.env` per request. Each organization configures its provider once in Settings, and the backend stores the encrypted credential in `integration_connections`.

```txt
Organization
→ IntegrationConnection
→ encrypted API key and base URL
→ provider client
```

The UrbanKart adapter expects:

```txt
GET  /api/support/health
GET  /api/support/orders/{order_id}
GET  /api/support/orders/{order_id}/payment
GET  /api/support/orders/{order_id}/shipment
GET  /api/support/customers/by-email?email=...
POST /api/support/refunds/request
POST /api/support/replacements/request
```

Integration setup:

```txt
Admin enters base URL and API key
→ API encrypts and stores the key
→ Test connection calls health
→ Tool gateway resolves connection by organization
→ Provider result is written to external_api_logs
```

Future providers can use the same boundary through adapters for Shopify, WooCommerce, Magento, or a custom API.

## Knowledge and RAG

Text document flow:

```txt
Create document
→ ACTIVE or DRAFT status
→ Ingest
→ Split into overlapping chunks
→ Generate 384 dimension embedding
→ Store pgvector chunks
→ INGESTED status
```

File flow:

```txt
Upload PDF, DOCX, TXT, Markdown, CSV, JSON, or XML
→ Cloudinary metadata
→ Content extraction
→ Chunking and embeddings
→ pgvector storage
```

Search flow:

```txt
Question or ticket context
→ Query embedding
→ Organization filter
→ ACTIVE document filter
→ INGESTED document filter
→ Cosine similarity
→ Top chunks
→ Agent context
```

The database uses `vector(384)`. Lightweight embeddings and normalized Gemini embeddings match this dimension.

RAGAS is manual and evaluates current organization retrieval with golden questions, generated answers, context precision, context recall, faithfulness, and answer relevancy. It is not scheduled in production.

## Agent Workflow

```txt
load_context_step
→ retrieve_knowledge_step
→ classify_ticket_step
→ detect_risk_step
→ plan_tools_step
→ approval_node when required
→ execute_tools_node
→ draft_response_step
→ decision_step
→ END
```

The agent loads context, retrieves knowledge, classifies category and priority, detects risk, plans tools, pauses for approvals, drafts a grounded reply, and applies backend policy.

Decisions:

```txt
AUTO_REPLY_DRAFT
NEEDS_HUMAN_APPROVAL
ESCALATE_TO_MANAGER
ASK_CUSTOMER_FOR_MORE_INFO
NO_ACTION
```

Legal and critical risk escalate. Order dependent cases without an order ID ask for more information. Refund and replacement actions require approval.

`Run Agent` creates a new graph run from the beginning. `Execute Planned Tools` uses a stored plan and is intended for safe tools or legacy plans that were not executed. It does not rerun classification.

## Tools and Approvals

Registered tools:

```txt
urbankart_get_order_context       READ_ONLY
urbankart_request_refund          HIGH_RISK_WRITE
urbankart_request_replacement     HIGH_RISK_WRITE
```

Tool flow:

```txt
Tool request
→ Registry lookup
→ Scope validation
→ Argument normalization
→ Idempotency lookup
→ Execute or block
→ Provider call
→ Result, timeline, and audit records
```

Same organization, key, tool, scope, and arguments return the existing execution. A reused key with different input returns conflict.

Approval flow:

```txt
Risky tool planned
→ BLOCKED_APPROVAL_REQUIRED
→ ApprovalRequest PENDING
→ Human approves or rejects
→ Approved execution resumes
→ Rejection becomes SKIPPED
→ Timeline and audit records
```

## Replies and Realtime

Reply lifecycle:

```txt
DRAFT
→ PENDING_APPROVAL
→ APPROVED or REJECTED
→ SENT
→ Public TicketMessage
→ Timeline and audit records
```

Realtime lifecycle:

```txt
Domain action
→ Timeline event committed
→ Redis event bus
→ SSE stream
→ Browser appends event
→ Coalesced panel refresh
```

## SLA and Background Work

```txt
URGENT   first response 30 minutes   resolution 4 hours
HIGH     first response 1 hour        resolution 8 hours
MEDIUM   first response 4 hours       resolution 24 hours
LOW      first response 8 hours       resolution 48 hours
```

Shared function: `run_sla_check(db)`.

Free MVP:

```txt
External cron every minute
→ POST /internal/jobs/check-sla
→ FastAPI runs shared SLA function
→ PostgreSQL is updated
```

Required header:

```txt
X-Internal-Job-Secret: configured secret
```

Optional paid deployment:

```txt
Celery Beat every 60 seconds
→ Redis
→ Celery worker
→ shared SLA function
```

Do not run external cron and Celery Beat for the same environment. Celery is not used for RAGAS, agent runs, invitation email, or knowledge ingestion in the current v1.

## Database Overview

```txt
users
organizations
organization_members
organization_invitations
integration_connections
external_api_logs
tickets
ticket_messages
ticket_internal_notes
ticket_timeline_events
ticket_status_transitions
knowledge_documents
knowledge_chunks
agent_runs
agent_run_steps
tool_executions
approval_requests
customer_reply_drafts
audit_logs
```

```txt
Organization
├── Members and Invitations
├── Tickets
│   ├── Messages, Notes, Timeline, StatusTransitions
│   ├── AgentRuns and AgentRunSteps
│   ├── ToolExecutions
│   ├── ApprovalRequests
│   └── ReplyDrafts
├── KnowledgeDocuments and KnowledgeChunks
├── IntegrationConnections and ExternalApiLogs
└── AuditLogs
```

Complete attributes, foreign keys, delete rules, constraints, indexes, and migration details are in `docs/SYSTEM_DESIGN.md`.

## API Surface

```txt
GET    /health
GET    /ready
POST   /auth/sync
GET    /auth/me
POST   /auth/bootstrap-org
POST   /organizations
GET    /organizations/current
PATCH  /organizations/current
GET    /organizations/members
POST   /organizations/invite
GET    /organizations/invitations
PUT    /integrations/urbankart
GET    /integrations/urbankart
POST   /integrations/urbankart/test-connection
PATCH  /integrations/urbankart/deactivate
GET    /integrations/urbankart/orders/{order_id}
GET    /integrations/logs
POST   /tickets
GET    /tickets
GET    /tickets/{ticket_id}
PATCH  /tickets/{ticket_id}
GET    /tickets/{ticket_id}/timeline
POST   /tickets/{ticket_id}/messages
POST   /tickets/{ticket_id}/internal-notes
POST   /knowledge/documents
POST   /knowledge/documents/upload
GET    /knowledge/documents
PATCH  /knowledge/documents/{document_id}
DELETE /knowledge/documents/{document_id}
POST   /knowledge/documents/{document_id}/ingest
GET    /knowledge/documents/{document_id}/chunks
GET    /knowledge/documents/{document_id}/download
POST   /knowledge/search
POST   /knowledge/tickets/{ticket_id}/search
POST   /knowledge/evaluation/golden
GET    /knowledge/evaluation/questions
POST   /knowledge/evaluation/search-test
POST   /agent/tickets/{ticket_id}/run
GET    /agent/runs/{run_id}
GET    /agent/tickets/{ticket_id}/runs
POST   /tools/execute
POST   /tools/agent-runs/{run_id}/execute-safe
GET    /tools/executions/{execution_id}
GET    /tools/tickets/{ticket_id}/executions
GET    /approvals
GET    /approvals/{approval_id}
POST   /approvals/tool-executions/{execution_id}/request
POST   /approvals/{approval_id}/approve
POST   /approvals/{approval_id}/reject
POST   /replies/drafts
GET    /replies/tickets/{ticket_id}/drafts
PATCH  /replies/drafts/{draft_id}
POST   /replies/drafts/{draft_id}/submit-approval
POST   /replies/drafts/{draft_id}/approve
POST   /replies/drafts/{draft_id}/reject
POST   /replies/drafts/{draft_id}/send
GET    /realtime/tickets/{ticket_id}/timeline/stream
GET    /realtime/organizations/stream
GET    /public/organizations/{slug}
POST   /public/organizations/{slug}/tickets
POST   /external/tickets
POST   /internal/jobs/check-sla
GET    /audit-logs
GET    /analytics/overview
```

## Configuration

Development needs database, Redis, integration encryption, and API URLs. Production additionally requires Clerk configuration, strong `INTERNAL_JOB_SECRET`, strong `INTEGRATION_SECRET_KEY`, `DEV_AUTH_ENABLED=false`, and frontend-only CORS origins.

Typical development values:

```env
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DB
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
URBANKART_BASE_URL=http://localhost:8001
URBANKART_API_KEY=dev_urbankart_key
DEV_AUTH_ENABLED=true
INTEGRATION_SECRET_KEY=replace-with-fernet-key
INTERNAL_JOB_SECRET=dev-internal-job-secret
AI_PROVIDER=mock
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

Never commit `.env` or real credentials. Rotate exposed credentials.

## Local Development

```bash
docker compose build
docker compose up -d
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed_demo
curl http://localhost:8000/ready
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`.

## Free MVP Operation

Set `INTERNAL_JOB_SECRET` in the API environment. Deploy only the API, database, frontend, and optional Redis. Configure cron-job.org or another scheduler:

```txt
Method: POST
URL: https://api.example.com/internal/jobs/check-sla
Header: X-Internal-Job-Secret: your-secret
Schedule: every minute
```

## Optional Celery Operation

```bash
celery -A app.worker.celery_app.celery_app worker
celery -A app.worker.celery_app.celery_app beat
```

Run only one Beat process. Use Celery when the platform supports separate workers or when long running agent, ingestion, email, webhook, or evaluation jobs need isolation.

## Testing

```bash
docker compose exec api pytest -q
cd apps/web
npm run build
npm run test:e2e
```

The backend suite covers health, readiness, tickets, replies, tools, idempotency, approvals, analytics, audit logs, and the internal SLA job endpoint.

## Tradeoffs and Current Limits

```txt
PostgreSQL is the durable source of truth; Redis is coordination infrastructure.
LangGraph makes state and approval pauses inspectable, at the cost of more setup.
The tool gateway prevents direct AI side effects, at the cost of explicit adapters.
SSE is simpler than WebSockets for server to client timeline updates.
External cron keeps the free MVP inexpensive, while Celery scales long jobs better.
Invitation acceptance is currently email based and has no built in mail delivery.
Only UrbanKart provider behavior is implemented.
Agent runs and RAGAS are manual and synchronous in v1.
```
