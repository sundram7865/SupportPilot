# SupportPilot Roadmap

## Completed

```txt
Phase 0   Product scope lock
Phase 1   Engineering foundation
Phase 2   Auth, organization, RBAC
Phase 3   UrbanKart integration
Phase 4   Ticketing system
Phase 5   Ticket lifecycle state machine
Phase 6   Knowledge base + RAG
Phase 7   LangGraph agent
Phase 8   Tool gateway
Phase 9   Approval system
Phase 10  SSE timeline
Phase 11  Reply workflow
Phase 12  SLA background workflow
Phase 13  Audit logs
Phase 14  Analytics
Phase 15-28 Testing and frontend integration
Phase 29  Security hardening
Phase 30  Deployment preparation
Phase 31  Documentation
```

## Current v1 Behavior

```txt
Ticket creation is automatic.
Agent execution is manual.
Celery handles background/SLA workflows.
Risky actions require approval.
```

## Planned v2

### Automatic Agent Execution

```txt
Ticket created
→ Celery task queued
→ Worker runs LangGraph agent
→ SSE streams progress
→ Final decision created
```

### Email Ingestion

```txt
Inbound email
→ ticket creation
→ threaded replies
→ classification
→ AI workflow
```

### WhatsApp Integration

```txt
WhatsApp message
→ ticket creation
→ customer reply delivery
```

### Agent Replay and Evaluation

```txt
Historical ticket
→ replay agent workflow
→ compare output
→ detect policy violations
→ measure quality
```

### Observability

```txt
Sentry
structured logs
agent traces
metrics dashboard
tool execution monitoring
```

### More Integrations

```txt
Shopify
WooCommerce
payment gateways
shipping providers
CRM systems
```
