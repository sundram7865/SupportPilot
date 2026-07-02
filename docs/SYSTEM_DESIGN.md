# SupportPilot System Design

This document describes the internal system design of SupportPilot.

It focuses on architecture, boundaries, data ownership, workflows, safety controls, scaling, and failure handling. Product overview, local setup, deployment commands, and feature summary are intentionally kept in `README.md`.

---

## 1. Design Summary

SupportPilot is structured as a modular, multi-tenant support platform where ticket operations, AI reasoning, external tool execution, and human approvals are separated into clear backend-controlled layers.

The central architectural idea is:

```txt
AI can reason.
Backend controls execution.
Humans approve risky actions.
Every important action is traceable.
```

The system is built around four control boundaries:

```txt
1. Tenant boundary
   Every resource belongs to an organization.

2. Permission boundary
   Users act through roles and permissions.

3. Tool boundary
   AI cannot call external systems directly.

4. Policy boundary
   Risky replies/actions require approval or escalation.
```

---

## 2. Non-Functional Requirements

### 2.1 Safety

The system must prevent uncontrolled AI actions.

Examples:

```txt
AI should not directly issue refunds.
AI should not directly access merchant DBs.
AI should not auto-reply to legal-risk tickets.
AI should not bypass organization permissions.
AI should not repeat risky external actions on retry.
```

### 2.2 Tenant Isolation

All business data must be organization-scoped.

```txt
organization_id is the primary isolation key.
```

A user can access organization data only if an active membership exists.

### 2.3 Traceability

Every important workflow transition should leave an operational trace.

Trace records include:

```txt
timeline events
audit logs
tool execution records
approval records
reply draft state changes
```

### 2.4 Reliability

The system should tolerate failures from:

```txt
LLM provider
UrbanKart API
Redis
Celery worker
database transient errors
network timeouts
duplicate requests
```

### 2.5 Extensibility

The system should allow adding:

```txt
new ticket sources
new merchant integrations
new tools
new approval policies
new knowledge documents
new background workflows
new analytics
```

---

## 3. System Boundary Diagram

```txt
┌──────────────────────────────────────────────────────────────────┐
│                         SupportPilot                              │
│                                                                  │
│  ┌──────────────┐       ┌─────────────────────────────────────┐  │
│  │   Frontend   │──────▶│              API Layer               │  │
│  │   Next.js    │       │ FastAPI routers + dependencies       │  │
│  └──────────────┘       └──────────────────┬──────────────────┘  │
│                                            │                     │
│                                            ▼                     │
│                         ┌─────────────────────────────────────┐  │
│                         │          Domain Modules              │  │
│                         │ Tickets | Agent | Tools | Approval   │  │
│                         │ Knowledge | SLA | Audit | Analytics  │  │
│                         └──────────────────┬──────────────────┘  │
│                                            │                     │
│                ┌───────────────────────────┼──────────────────┐ │
│                ▼                           ▼                  ▼ │
│     ┌──────────────────┐       ┌──────────────────┐  ┌────────┐│
│     │ PostgreSQL        │       │ Redis             │  │ Gemini ││
│     │ + pgvector        │       │ Celery + limits    │  │ LLM    ││
│     └──────────────────┘       └──────────────────┘  └────────┘│
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                 ┌──────────────────────────┐
                 │     UrbanKart Mock API    │
                 │ External merchant system  │
                 └──────────────────────────┘
```

---

## 4. Layered Architecture

SupportPilot follows a layered architecture.

```txt
Presentation Layer
→ Next.js UI, public form, dashboard

API Layer
→ FastAPI routers, request validation, auth dependencies

Domain Layer
→ tickets, agent, tools, approvals, replies, SLA, audit, analytics

Integration Layer
→ UrbanKart client, Gemini client, Redis, Clerk JWKS

Persistence Layer
→ SQLAlchemy models, PostgreSQL, pgvector

Background Layer
→ Celery worker and celery beat
```

### Why this separation matters

```txt
Frontend does not own business rules.
AI does not execute external actions directly.
Tools do not decide policy.
Policy engine does not call external APIs.
Approvals are stored separately from tool execution.
Audit logs are append-only operational records.
```

---

## 5. Module Dependency Direction

Preferred dependency direction:

```txt
Routes
→ Dependencies
→ Services / Helpers
→ Models / Database
→ External Clients
```

For AI workflow:

```txt
Agent Graph
→ Tool Gateway
→ Tool Executor
→ UrbanKart Client
```

For knowledge retrieval:

```txt
Agent Graph
→ Knowledge Search Service
→ pgvector
```

For approvals:

```txt
Tool Execution / Reply Draft
→ Approval Request
→ Human Decision
→ Final State Update
```

Avoid:

```txt
UrbanKart client calling agent logic
Approval module directly calling LLM
Frontend deciding workflow state
AI bypassing tool gateway
```

---

## 6. Runtime Components

```txt
web
api
worker
celery-beat
postgres
redis
urbankart-mock-api
```

### Component Responsibility Matrix

| Component | Owns | Does Not Own |
|---|---|---|
| `web` | UI state, API calls, SSE rendering | Business authorization, AI decisions |
| `api` | Auth, domain workflows, tool gateway | Long-running scheduled jobs |
| `worker` | Background tasks, SLA checks | HTTP routing |
| `celery-beat` | Scheduling periodic jobs | Task execution logic |
| `postgres` | Durable relational/vector data | Transient rate-limit counters |
| `redis` | Celery broker/result backend, rate limits | Source of truth business records |
| `urbankart-mock-api` | Mock merchant data/actions | SupportPilot tenant state |

---

## 7. Request Lifecycle

### 7.1 Authenticated Dashboard Request

```txt
Browser
→ Next.js page/component
→ API client attaches Clerk token
→ API receives request
→ Auth dependency resolves user
→ Organization dependency checks x-organization-id
→ RBAC dependency checks permission
→ Route handler executes
→ SQLAlchemy transaction
→ Response returned
```

Failure points:

```txt
missing token → 401
invalid token → 401
missing organization → 401/403
inactive membership → 403
missing permission → 403
resource not found in org → 404
```

### 7.2 Public Ticket Request

```txt
Customer public form
→ POST /public/organizations/{slug}/tickets
→ Redis rate limit
→ organization lookup by slug
→ ticket create
→ initial message create
→ timeline event create
→ response
```

Public route does not require dashboard authentication.

### 7.3 External API Ticket Request

```txt
External system
→ POST /external/tickets
→ Redis rate limit
→ organization lookup by slug
→ integration lookup
→ decrypt stored API key
→ constant-time compare
→ ticket create
→ external API log create
→ response
```

---

## 8. Data Ownership Model

The organization is the primary ownership boundary.

```txt
Organization
├── Members
├── Tickets
│   ├── Messages
│   ├── Internal Notes
│   ├── Timeline Events
│   ├── Agent Runs
│   ├── Tool Executions
│   ├── Approvals
│   └── Reply Drafts
├── Knowledge Documents
│   └── Knowledge Chunks
├── Integrations
│   └── External API Logs
└── Audit Logs
```

### Ownership Rules

```txt
A ticket belongs to one organization.
A tool execution belongs to one organization and usually one ticket.
An approval belongs to one organization and may reference a tool/reply/ticket.
A knowledge document belongs to one organization.
A user accesses organization data only through membership.
```

---

## 9. Core Data Model

### 9.1 Identity and Tenant

```txt
users
organizations
organization_members
```

Purpose:

```txt
users                  stores platform users
organizations          stores tenant/workspace
organization_members   joins user to organization with role/status
```

### 9.2 Ticketing

```txt
tickets
ticket_messages
ticket_internal_notes
ticket_timeline_events
```

Purpose:

```txt
tickets                 support case source of truth
ticket_messages         public/customer-visible messages
ticket_internal_notes   private support notes
ticket_timeline_events  operational ticket history
```

### 9.3 Knowledge and RAG

```txt
knowledge_documents
knowledge_chunks
```

Purpose:

```txt
knowledge_documents     policy/SOP/FAQ documents
knowledge_chunks        searchable chunks with vector embeddings
```

### 9.4 Agent and Tools

```txt
agent_runs
tool_executions
```

Purpose:

```txt
agent_runs       one execution of LangGraph workflow
tool_executions  individual backend tool calls
```

### 9.5 Human Review

```txt
approval_requests
customer_reply_drafts
```

Purpose:

```txt
approval_requests       human-in-the-loop decisions
customer_reply_drafts   AI/agent/template-generated replies
```

### 9.6 Operations

```txt
integration_connections
external_api_logs
audit_logs
```

Purpose:

```txt
integration_connections encrypted merchant API config
external_api_logs       external request/response tracking
audit_logs              durable action history
```

---

## 10. Ticket Domain Design

Ticket is the main workflow aggregate.

Ticket state is changed by:

```txt
customer intake
support agent action
agent workflow
approval outcome
reply send
SLA background job
```

### Ticket Creation Transaction

```txt
BEGIN
  create ticket
  create initial message
  create timeline event
COMMIT
```

This ensures a ticket is not created without its first message/timeline record.

### Ticket Numbering

Ticket number is generated in a human-readable sequence:

```txt
TICK-00001
TICK-00002
```

### Ticket Metadata

Metadata is used for non-core contextual data:

```txt
source channel
client host
user agent
external payload
agent run hints
```

---

## 11. Ticket Lifecycle Design

Ticket statuses:

```txt
OPEN
IN_PROGRESS
WAITING_FOR_CUSTOMER
WAITING_FOR_INTERNAL_REVIEW
RESOLVED
CLOSED
```

State machine:

```txt
              ┌──────────────────────┐
              │        OPEN          │
              └──────────┬───────────┘
                         ▼
              ┌──────────────────────┐
              │     IN_PROGRESS      │
              └───────┬────────┬─────┘
                      │        │
                      ▼        ▼
 ┌──────────────────────────┐ ┌──────────────────────────────┐
 │ WAITING_FOR_CUSTOMER     │ │ WAITING_FOR_INTERNAL_REVIEW  │
 └────────────┬─────────────┘ └──────────────┬───────────────┘
              │                              │
              ▼                              ▼
              ┌──────────────────────┐
              │       RESOLVED       │
              └──────────┬───────────┘
                         ▼
              ┌──────────────────────┐
              │        CLOSED        │
              └──────────────────────┘
```

Reopen path:

```txt
RESOLVED / CLOSED
→ OPEN
```

Invalid transitions are blocked.

---

## 12. Agent Workflow Design

Agent workflow is modeled as a graph, not a single function.

```txt
Ticket
→ Load Context
→ Classify
→ Detect Risk
→ Route
→ Plan Tools
→ Check Tool Permission
→ Execute Tools
→ Retrieve Knowledge
→ Draft Response
→ Policy Check
→ Final Decision
```

### Agent State

```txt
ticket_id
organization_id
customer_message
ticket_category
priority
sentiment
risk_level
confidence
required_tools
tool_outputs
retrieved_sources
draft_response
policy_decision
final_action
```

### Final Actions

```txt
AUTO_REPLY
APPROVAL_REQUIRED
ASK_MORE_INFO
ESCALATE
```

---

## 13. LangGraph Node Design

```txt
┌──────────────────────────┐
│ load_ticket_context_node │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│  classify_ticket_node    │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│  risk_detection_node     │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│    route_after_risk      │
└───────┬─────────┬────────┘
        │         │
        │         ▼
        │  immediate_escalation_node
        │
        ▼
┌──────────────────────────┐
│   tool_planning_node     │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│  tool_permission_node    │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│   execute_tools_node     │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│  rag_policy_search_node  │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│   draft_response_node    │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│   policy_engine_node     │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ final_decision_edge      │
└──────┬──────┬──────┬─────┘
       │      │      │
       ▼      ▼      ▼
 auto_reply approval escalation
```

### Node Responsibilities

| Node | Responsibility |
|---|---|
| `load_ticket_context_node` | Load ticket, messages, customer, org, metadata |
| `classify_ticket_node` | Classify category, priority, sentiment, risk, confidence |
| `risk_detection_node` | Detect legal/financial/policy-sensitive cases |
| `route_after_risk` | Branch based on risk and missing information |
| `tool_planning_node` | Decide which tools are required |
| `tool_permission_node` | Validate tool access and approval requirement |
| `execute_tools_node` | Execute approved backend tools |
| `rag_policy_search_node` | Retrieve relevant policies/SOPs |
| `draft_response_node` | Generate grounded response draft |
| `policy_engine_node` | Evaluate safety of response/action |
| `final_decision_edge` | Route to auto-reply, approval, ask-more-info, escalation |

---

## 14. Tool Gateway Design

Tool gateway separates AI reasoning from external execution.

```txt
Agent chooses tool + args
→ Tool registry lookup
→ Organization/ticket validation
→ Risk classification
→ Approval requirement check
→ Idempotency check
→ Execute or block
→ Store execution
→ Create timeline event
```

### Tool Categories

Read-only tools:

```txt
urbankart_get_order_context
getOrderDetails
checkPaymentStatus
checkShipmentStatus
getCustomerProfile
searchKnowledgeBase
```

Risky/write tools:

```txt
urbankart_request_refund
requestReplacement
sendCustomerReply
```

### Tool Execution States

```txt
STARTED
SUCCESS
FAILED
BLOCKED_APPROVAL_REQUIRED
```

### Approval States

```txt
NOT_REQUIRED
PENDING
APPROVED
REJECTED
```

---

## 15. Idempotency Design

Idempotency protects external side effects.

Idempotency key is checked with:

```txt
ticket_id
agent_run_id
tool_name
input_args
idempotency_key
```

Same request:

```txt
same key + same tool + same args
→ return previous execution
```

Conflict:

```txt
same key + different tool/args/ticket
→ 409 Conflict
```

Used for:

```txt
refund request
replacement request
send customer reply
future external write tools
```

---

## 16. RAG Design

Knowledge ingestion:

```txt
Document
→ chunk text
→ generate embedding
→ store chunk + vector
```

Query flow:

```txt
Ticket context / customer question
→ generate query embedding
→ pgvector similarity search
→ return top knowledge chunks
→ pass sources to agent
```

RAG helps with:

```txt
refund policy
return policy
shipping policy
damaged product SOP
payment failure SOP
legal risk SOP
support tone guide
```

RAG result shape:

```txt
chunk_id
document_id
document_title
document_type
chunk_index
content
score
```

---

## 17. Policy Engine Design

Policy engine is the final safety evaluator.

Inputs:

```txt
ticket category
risk level
confidence
tool outputs
draft response
amount/payment context
retrieved policies
```

Rules:

```txt
refund > ₹1000 → approval
money-related reply → approval
legal risk → escalation
confidence < 0.80 → approval
low risk + confidence >= 0.80 → auto reply
```

Outputs:

```txt
AUTO_REPLY
APPROVAL_REQUIRED
ASK_MORE_INFO
ESCALATE
```

---

## 18. Approval System Design

Approval is a separate workflow object.

Can be linked to:

```txt
tool execution
reply draft
ticket escalation
```

Approval lifecycle:

```txt
PENDING
→ APPROVED
→ REJECTED
```

Side effects:

```txt
approval approved
→ update related object
→ create timeline event
→ create audit log

approval rejected
→ block related object/action
→ create timeline event
→ create audit log
```

Approval routes:

```txt
GET  /approvals
GET  /approvals/{approval_id}
POST /approvals/tool-executions/{execution_id}/request
POST /approvals/{approval_id}/approve
POST /approvals/{approval_id}/reject
```

---

## 19. Reply Workflow Design

Reply draft is separate from ticket message until sent.

Reason:

```txt
Drafts can be edited.
Drafts can require approval.
Rejected drafts should not become public messages.
Sent replies should create public message history.
```

Lifecycle:

```txt
DRAFT
→ PENDING_APPROVAL
→ APPROVED / REJECTED
→ SENT
```

Send flow:

```txt
Approved draft
→ send action
→ create TicketMessage
→ mark draft SENT
→ create timeline event
→ create audit log
```

---

## 20. SSE Realtime Design

Timeline events are the source of realtime UI updates.

```txt
Domain action
→ timeline event created
→ SSE event emitted
→ frontend timeline updates
```

SSE event examples:

```txt
ticket.created
agent.started
agent.node.completed
tool.called
tool.completed
approval.created
approval.approved
reply.sent
sla.near_breach
sla.breached
```

SSE is used instead of WebSocket because current realtime needs are mostly server-to-client.

---

## 21. Celery Background Design

Current background jobs:

```txt
SLA check
near-breach detection
breach detection
health/background task
```

Future background jobs:

```txt
automatic agent execution
email ingestion
webhook processing
agent replay/evaluation
scheduled analytics
```

Architecture:

```txt
FastAPI / Celery Beat
→ Redis broker
→ Celery worker
→ database update
→ timeline/audit update
```

Production rule:

```txt
Only one celery-beat instance should run.
Multiple workers are allowed.
```

---

## 22. SLA Design

SLA statuses:

```txt
OK
NEAR_BREACH
BREACHED
```

SLA check flow:

```txt
Celery beat triggers task
→ worker scans active tickets
→ worker compares current time with SLA deadline
→ update SLA state
→ create timeline event
→ create audit log
```

---

## 23. Audit Design

Audit logs are append-style operational records.

Audit answers:

```txt
who performed the action
what resource changed
when it happened
what metadata was attached
```

Resource types:

```txt
TICKET
TICKET_MESSAGE
TICKET_INTERNAL_NOTE
AGENT_RUN
TOOL_EXECUTION
APPROVAL_REQUEST
REPLY_DRAFT
ORGANIZATION
INTEGRATION
SLA
```

---

## 24. Analytics Design

Analytics is derived from operational tables.

Source tables:

```txt
tickets
approval_requests
tool_executions
customer_reply_drafts
audit_logs
```

Metrics:

```txt
tickets by status
tickets by category
tickets by priority
approval counts
tool execution counts
SLA counts
reply counts
```

Endpoint:

```txt
GET /analytics/overview
```

Permission:

```txt
ANALYTICS_VIEW
```

---

## 25. Security Design

Security controls:

```txt
Clerk JWT verification
organization membership check
RBAC permission check
dev auth disabled in production
CORS validation
security headers
Redis-backed rate limiting
safe error response
encrypted integration API keys
audit logs
```

Production config validation prevents unsafe startup.

Rate-limited routes:

```txt
GET  /public/organizations/{slug}
POST /public/organizations/{slug}/tickets
POST /external/tickets
```

---

## 26. Error Handling Design

Standard error shape:

```json
{
  "error": {
    "message": "Ticket not found.",
    "status_code": 404,
    "request_id": "..."
  }
}
```

Common failures:

```txt
missing organization → 401/403
missing permission → 403
missing ticket → 404
invalid transition → 400
idempotency conflict → 409
rate limit exceeded → 429
unexpected error → safe 500
```

---

## 27. Deployment Architecture

Recommended production architecture:

```txt
Vercel Frontend
      │
      ▼
Render/Railway API
      │
      ├── Neon/Supabase PostgreSQL + pgvector
      ├── Upstash/managed Redis
      ├── Gemini API
      ├── Clerk JWKS
      └── UrbanKart Mock API

Render/Railway Worker
      │
      ├── PostgreSQL
      └── Redis

Render/Railway Beat
      │
      └── Redis
```

---

## 28. Scaling Strategy

### API

```txt
Stateless API replicas
Load balancer
Managed Postgres
Managed Redis
```

### Workers

```txt
Multiple Celery workers
Shared Redis broker
Idempotent external actions
```

### Beat

```txt
Single celery-beat instance
```

### Database

Recommended indexes:

```txt
organization_id
ticket_id
status
category
priority
created_at
assignee_id
```

For pgvector:

```txt
vector index on knowledge_chunks.embedding
```

### Realtime

Current:

```txt
single API instance SSE
```

Future multi-instance:

```txt
Redis pub/sub for SSE fanout
or WebSocket gateway if bidirectional events are needed
```

---

## 29. Failure Handling

```txt
UrbanKart API failure
→ tool execution FAILED
→ error stored
→ timeline event created

Duplicate idempotency key with same args
→ previous execution returned

Duplicate idempotency key with different args
→ 409 Conflict

Missing organization
→ 401/403

Missing permission
→ 403

Missing ticket
→ 404

Invalid status transition
→ 400

Unsafe production env
→ startup failure

Rate limit exceeded
→ 429

Unexpected server error
→ safe 500 response
```

---

## 30. Current Limitations

```txt
Agent execution is manual in v1.
Celery does not auto-run agent yet.
Email ingestion is not implemented yet.
WhatsApp ingestion is not implemented yet.
Advanced agent replay/eval is not implemented yet.
Frontend e2e tests were skipped due Clerk dev setup issues.
```

---

## 31. Future Improvements

```txt
Automatic Celery-based agent execution
Email channel ingestion
WhatsApp integration
Agent replay/evaluation system
Agent trace viewer
Sentry/structured observability
More granular approval policies
More merchant integrations
Webhook delivery
Advanced SLA analytics
Advanced support QA dashboard
```
