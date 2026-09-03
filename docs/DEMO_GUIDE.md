# SupportPilot Demo Guide

This guide demonstrates the current v1 using the UrbanKart mock ecommerce API.

## 1. Start

```bash
docker compose build
docker compose up -d
docker compose exec api alembic upgrade head
docker compose exec api python -m app.scripts.seed_demo
curl http://localhost:8000/ready
```

Start the frontend from its own directory:

```bash
cd apps/web
npm install
npm run dev
```

Open `http://localhost:3000`.

## 2. Demo Provider

Inside Docker:

```txt
Base URL: http://urbankart-mock-api:8001
API key: dev_urbankart_key
Demo order: ORD-1001
```

From the host, the mock API is available at `http://localhost:8001`.

## 3. Configure Integration

Open `Settings` and `Integration Settings`.

```txt
Base URL: http://urbankart-mock-api:8001
API key: dev_urbankart_key
```

Click `Test Connection`.

The API stores the key encrypted for the current organization. Companies do not change `.env` per request. A real merchant must expose the UrbanKart compatible health, order, payment, shipment, refund, and replacement operations, or use a provider adapter.

## 4. Order Status

Create:

```txt
Subject: Where is my order?
Description: Please check delivery status for order ORD-1001.
Category: ORDER_STATUS
Priority: MEDIUM
Order ID: ORD-1001
```

Click `Run Agent`.

```txt
Context loaded
→ Knowledge retrieved
→ ORDER_STATUS classified
→ LOW risk detected
→ Order context tool planned
→ Order, payment, shipment fetched
→ Reply drafted
→ Policy decision
```

The order context tool is read only and does not require approval.

## 5. Payment and Refund Approval

Create:

```txt
Subject: Payment deducted but order failed
Description: Payment was deducted for order ORD-1002 but the order failed.
Category: PAYMENT_ISSUE
Priority: HIGH
Order ID: ORD-1002
```

Click `Run Agent`.

```txt
Payment issue classified
→ HIGH risk detected
→ Context tool planned
→ Refund tool planned
→ Refund execution blocked
→ Approval request PENDING
→ Graph pauses
```

Approve from the approval panel:

```txt
Approval approved
→ Execution marked APPROVED
→ Graph resumes
→ UrbanKart refund request sent
→ Result, timeline, and audit records
```

Rejecting produces:

```txt
Execution SKIPPED
→ No refund request
→ Timeline and audit records
```

## 6. Damaged Product Replacement

Create:

```txt
Subject: Product arrived damaged
Description: Product from order ORD-1001 arrived damaged and needs replacement.
Category: DAMAGED_PRODUCT
Priority: HIGH
Order ID: ORD-1001
```

Click `Run Agent`.

```txt
Damaged product classified
→ HIGH risk
→ Replacement tool planned
→ Approval required
→ Human decision
```

The provider action is `POST /api/support/replacements/request`.

## 7. Legal Risk

Create:

```txt
Subject: Legal complaint
Description: I will file a consumer court complaint if this is not resolved.
Category: LEGAL_RISK
Priority: URGENT
```

Expected:

```txt
Legal keywords
→ CRITICAL risk
→ ESCALATE_TO_MANAGER
→ No automatic risky action
→ Human review
```

## 8. Run Agent and Execute Planned Tools

`Run Agent` starts a new graph run:

```txt
Load context
→ Retrieve knowledge
→ Classify
→ Risk detection
→ Plan tools
→ Approval pause if required
→ Draft and decision
```

`Execute Planned Tools` does not start a new graph run. It uses the latest stored plan:

```txt
Stored plan
→ Read only tools execute
→ Risky tools remain blocked
→ Approval requests are created
```

Use it only when a plan exists but safe tools have not been executed. Repeated clicks are unnecessary. Idempotency protects external side effects.

## 9. Knowledge and RAG

Open `Settings` and `Knowledge Base`.

Create an active policy:

```txt
Title: Return Policy
Type: POLICY
Status: ACTIVE
Content: Returns are accepted within 7 days of delivery. Personal care products are non-returnable.
```

Ingest the document. The backend performs:

```txt
Content
→ Chunks
→ 384 dimension embeddings
→ pgvector
→ INGESTED status
```

Search uses only the current organization and ACTIVE plus INGESTED documents.

File uploads support PDF, DOCX, TXT, Markdown, CSV, JSON, and XML through extraction and Cloudinary metadata.

## 10. Organizations and Invitations

Open `Settings` and `Organization Settings`.

Invite an existing local user:

```txt
Invite email
→ Active membership immediately
```

Invite a new Clerk user:

```txt
Invite email
→ User completes Clerk sign up
→ /auth/sync matches normalized email
→ Active membership created
```

The current backend does not send invitation email. The invitation must be delivered outside the API.

## 11. Public Intake

Open:

```txt
/support/{organization-slug}
```

Submit a ticket without dashboard authentication.

The backend creates a ticket, customer message, timeline event, and SLA deadlines. Public intake is rate limited.

## 12. External Intake

Send:

```txt
POST /external/tickets
x-organization-slug: organization-slug
x-supportpilot-api-key: configured key
```

This is intended for merchant systems sending tickets into SupportPilot.

## 13. Replies

From a ticket:

```txt
Create draft
→ Edit
→ Submit approval
→ Approve or reject
→ Send
```

Sending creates the public message and updates the draft, timeline, audit, and first response state.

## 14. Realtime

Keep a ticket open and perform an action in another tab.

```txt
Approval or message
→ Timeline event
→ Redis event bus
→ SSE stream
→ Timeline appears immediately
→ Related panels refresh once after a short coalescing delay
```

## 15. Free MVP SLA Scheduling

Development test:

```powershell
Invoke-RestMethod `
  -Method POST `
  -Uri http://localhost:8000/internal/jobs/check-sla `
  -Headers @{ "X-Internal-Job-Secret" = "dev-internal-job-secret" }
```

Production cron configuration:

```txt
Method: POST
URL: https://your-api-domain.com/internal/jobs/check-sla
Header: X-Internal-Job-Secret: production-secret
Schedule: every minute
```

Set the same secret in the backend environment as `INTERNAL_JOB_SECRET`.

## 16. Optional Celery Demo

For a deployment with separate processes:

```bash
celery -A app.worker.celery_app.celery_app worker
celery -A app.worker.celery_app.celery_app beat
```

Run either Celery Beat or external cron for SLA scheduling in one environment, not both.

## 17. RAGAS Evaluation

RAGAS is manual and should run against a development or evaluation organization:

```txt
GROK_API_KEY
GEMINI_API_KEY
```

It retrieves knowledge, generates answers, and computes context precision, context recall, faithfulness, and answer relevancy. It is not part of normal ticket handling and is not scheduled in production.

## 18. Commands and Safety Checklist

```bash
docker compose exec api pytest -q
cd apps/web
npm run build
npm run test:e2e
```

```txt
AI does not receive ecommerce credentials.
AI does not access merchant databases directly.
Unknown tools fail registry validation.
Refunds and replacements require approval.
Duplicate writes use idempotency keys.
Organization boundaries are checked.
Public and external intake are rate limited.
Important actions create timeline and audit records.
Development auth is disabled in production.
RAGAS is not production scheduled.
```
