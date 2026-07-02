# SupportPilot Demo Guide

## 1. Start Services

```bash
docker compose up -d --build
```

## 2. Run Migrations

```bash
docker compose exec api alembic upgrade head
```

## 3. Seed Demo Data

```bash
docker compose exec api python -m app.scripts.seed_demo
```

## 4. Verify API

```bash
curl http://localhost:8000/ready
```

PowerShell:

```powershell
Invoke-RestMethod http://localhost:8000/ready | ConvertTo-Json
```

## 5. Start Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open:

```txt
http://localhost:3000
```

## 6. Demo Flow: Order Status

```txt
Customer: Where is my order ORD-1001?

Ticket created
→ Agent classifies ORDER_STATUS
→ Risk LOW
→ Tool gateway calls UrbanKart order context tool
→ Order/payment/shipment context returned
→ RAG retrieves shipping policy
→ Agent drafts reply
→ Policy engine allows auto-reply if safe
```

## 7. Demo Flow: Payment Deducted

```txt
Customer: Payment deducted ₹1499 but order not created.

Ticket created
→ Agent classifies PAYMENT_ISSUE / REFUND_REQUEST
→ Money-related risk detected
→ Payment/order context checked
→ Policy engine requires approval
→ Approval request created
```

## 8. Demo Flow: Legal Risk

```txt
Customer: I will file a consumer court complaint.

Ticket created
→ Legal risk detected
→ Immediate escalation
→ No automatic risky reply
→ Human review required
```

## 9. Demo Flow: Damaged Product

```txt
Customer: Product arrived damaged.

Ticket created
→ Category RETURN_REPLACEMENT / DAMAGED_PRODUCT
→ RAG retrieves damaged product SOP
→ Replacement/refund policy evaluated
→ Approval or reply draft created
```

## 10. Manual Agent Run

Current v1:

```txt
Ticket creation does not automatically run the AI agent.
Agent is triggered manually.
```

Trigger:

```txt
Run Agent button
or
POST /agent/tickets/{ticket_id}/run
```

## 11. Show Safety Design

```txt
AI does not access UrbanKart database directly.
AI only requests backend-approved tools.
Risky tools require approval.
Refunds are idempotency-protected.
Audit logs track important actions.
Rate limiting protects public/external intake.
Dev auth is disabled in production.
```

## 12. Show Tests

```bash
docker compose exec api python -m pytest -q
```

Expected:

```txt
26 passed
```
