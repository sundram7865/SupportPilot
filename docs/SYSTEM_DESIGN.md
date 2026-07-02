# SupportPilot System Design

This document explains SupportPilot from a system-design perspective.

---

## 1. System Goal

SupportPilot is an agentic AI customer support platform for e-commerce and D2C brands.

The system supports multi-tenant organizations, ticket lifecycle management, AI-assisted ticket resolution, RAG over support policies, safe tool execution against external systems, human approval for risky actions, real-time timeline updates, SLA monitoring, audit logs, and analytics.

---

## 2. Main Design Constraints

### AI Safety

The AI agent must not directly access merchant databases or perform sensitive actions freely.

All sensitive operations go through:

```txt
Agent request
→ Backend tool gateway
→ Permission check
→ Risk check
→ Idempotency check
→ Approval if required
→ External API call
→ Audit log
```

### Multi-Tenancy

Every major entity is scoped by organization:

```txt
tickets
messages
knowledge documents
tool executions
approvals
reply drafts
audit logs
analytics
integrations
```

### Auditability

Actions that affect support workflow are traceable.

Examples:

```txt
ticket.created
tool.execution.started
tool.execution.blocked
approval.created
reply.sent
sla.breached
```

---

## 3. High-Level Architecture

```txt
Frontend
→ FastAPI Backend
→ PostgreSQL + pgvector
→ Redis
→ Celery Worker/Beat
→ Gemini/LangGraph
→ UrbanKart Mock API
```

---

## 4. Request Flow

### Dashboard Request

```txt
Browser
→ Clerk token
→ Next.js frontend
→ FastAPI API
→ Auth dependency
→ Organization membership check
→ Permission check
→ Route handler
→ Database
→ Response
```

### Public Ticket Request

```txt
Customer public form
→ POST /public/organizations/{slug}/tickets
→ Rate limit check
→ Organization lookup
→ Ticket creation
→ Message creation
→ Timeline creation
→ Response
```

### External API Ticket Request

```txt
External system
→ POST /external/tickets
→ Rate limit check
→ Organization slug lookup
→ API key verification
→ Ticket creation
→ External API log
→ Response
```

---

## 5. Agentic AI Flow

```txt
POST /agent/tickets/{ticket_id}/run
→ Create agent run
→ Load ticket context
→ Classify ticket
→ Detect risk
→ Route by risk
→ Plan tools
→ Validate tools
→ Execute tools
→ Search knowledge base
→ Draft response
→ Policy engine decision
→ Final route
```

Final routes:

```txt
AUTO_REPLY
APPROVAL_REQUIRED
ASK_MORE_INFO
ESCALATE
```

---

## 6. Tool Gateway Design

The tool gateway separates AI reasoning from external action.

```txt
Agent chooses tool name + args
→ Backend validates tool
→ Backend executes tool
→ Tool execution record is stored
→ Timeline is updated
→ Approval is created if needed
```

Read tools can execute directly. Risky tools require approval.

---

## 7. Idempotency Design

Risky tools use idempotency keys.

```txt
same idempotency key + same args
→ return existing execution

same idempotency key + different args
→ 409 conflict
```

This protects against duplicate refunds and repeated external actions.

---

## 8. RAG Design

```txt
Document
→ Chunking
→ Embedding
→ pgvector
→ Query embedding
→ Similarity search
→ Retrieved policy context
→ Agent response drafting
```

---

## 9. Approval Design

Approval can be attached to tool execution, customer reply, or ticket escalation.

Lifecycle:

```txt
PENDING
→ APPROVED / REJECTED
```

---

## 10. Realtime Design

SSE is used for timeline updates because one-way backend-to-frontend events are enough and simpler than WebSockets for this use case.

---

## 11. Background Job Design

Current Celery use:

```txt
SLA monitoring
near-breach detection
breach detection
```

Future Celery use:

```txt
automatic agent runs
email ingestion
webhook processing
agent replay/evaluation
```

---

## 12. Security Design

Implemented protections:

```txt
Clerk JWT verification
dev auth disabled in production
organization membership checks
RBAC permission checks
CORS validation
security headers
Redis-backed rate limiting
safe error response shape
Fernet-encrypted integration keys
audit logs
```

---

## 13. Scaling Notes

Scaling options:

```txt
API replicas behind load balancer
separate worker replicas
single celery-beat instance
managed PostgreSQL
managed Redis
separate UrbanKart mock API service
```

Important:

```txt
Only one celery-beat instance should run in production.
```

---

## 14. Failure Handling

Handled or planned cases:

```txt
UrbanKart API failure → tool execution failed
duplicate idempotency key → existing result or conflict
missing organization → 401/403
missing permission → 403
missing ticket → 404
unsafe production env → startup failure
rate limit exceeded → 429
unexpected server error → safe error response
```
