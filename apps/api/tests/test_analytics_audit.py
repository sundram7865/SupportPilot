from uuid import uuid4


def create_ticket(client, headers, subject: str = "Analytics audit pytest ticket") -> str:
    response = client.post(
        "/tickets",
        headers=headers,
        json={
            "subject": subject,
            "description": "Customer needs help with order ORD-1001.",
            "priority": "URGENT",
            "category": "PAYMENT_ISSUE",
            "source": "SUPPORT_FORM",
            "customer_name": "Analytics Customer",
            "customer_email": "analytics.customer@example.com",
            "customer_phone": "+91-9999999999",
            "external_order_id": "ORD-1001",
            "metadata_json": {
                "test": True,
                "suite": "analytics_audit",
            },
        },
    )

    assert response.status_code == 200

    return response.json()["id"]


def configure_urbankart_integration(client, headers):
    response = client.put(
        "/integrations/urbankart",
        headers=headers,
        json={
            "base_url": "http://urbankart-mock-api:8001",
            "api_key": "dev_urbankart_key",
        },
    )

    assert response.status_code == 200

    return response.json()


def create_sent_reply(client, headers, ticket_id: str) -> dict:
    create_response = client.post(
        "/replies/drafts",
        headers=headers,
        json={
            "ticket_id": ticket_id,
            "subject": "Support update",
            "body": "Hi, thanks for reaching out. We checked your order and will keep you updated.",
            "source": "AGENT",
            "metadata_json": {
                "test": True,
                "suite": "analytics_audit",
            },
        },
    )

    assert create_response.status_code == 200

    draft = create_response.json()

    submit_response = client.post(
        f"/replies/drafts/{draft['id']}/submit-approval",
        headers=headers,
        json={
            "request_reason": "Analytics audit test approval.",
        },
    )

    assert submit_response.status_code == 200
    assert submit_response.json()["status"] == "PENDING_APPROVAL"

    approve_response = client.post(
        f"/replies/drafts/{draft['id']}/approve",
        headers=headers,
        json={
            "reason": "Approved during analytics audit test.",
        },
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"

    send_response = client.post(
        f"/replies/drafts/{draft['id']}/send",
        headers=headers,
        json={
            "send_notes": "Sent during analytics audit test.",
        },
    )

    assert send_response.status_code == 200

    return send_response.json()


def create_blocked_refund_tool_and_approval(client, headers, ticket_id: str) -> dict:
    configure_urbankart_integration(client, headers)

    execute_response = client.post(
        "/tools/execute",
        headers=headers,
        json={
            "tool_name": "urbankart_request_refund",
            "ticket_id": ticket_id,
            "args": {
                "order_id": "ORD-1001",
                "amount": 1499,
                "reason": "Payment issue reported by customer.",
            },
            "idempotency_key": f"pytest-analytics-refund-{uuid4()}",
        },
    )

    assert execute_response.status_code == 200

    execution = execute_response.json()

    assert execution["status"] == "BLOCKED_APPROVAL_REQUIRED"

    approval_response = client.post(
        f"/approvals/tool-executions/{execution['id']}/request",
        headers=headers,
        json={
            "request_reason": "Refund approval needed for analytics audit test.",
            "metadata_json": {
                "test": True,
            },
        },
    )

    assert approval_response.status_code == 200

    return approval_response.json()


def test_analytics_overview_counts_core_workflow(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
    create_sent_reply(client, headers, ticket_id)
    create_blocked_refund_tool_and_approval(client, headers, ticket_id)

    response = client.get("/analytics/overview", headers=headers)

    assert response.status_code == 200

    data = response.json()

    assert data["total_tickets"] >= 1
    assert data["urgent_tickets"] >= 1

    assert data["tool_executions_total"] >= 1
    assert data["tool_executions_blocked"] >= 1

    assert data["approvals_total"] >= 2
    assert data["approvals_pending"] >= 1
    assert data["approvals_approved"] >= 1

    assert data["replies_total"] >= 1
    assert data["replies_sent"] >= 1

    assert data["audit_events_total"] >= 1

    assert isinstance(data["tickets_by_status"], list)
    assert isinstance(data["tickets_by_priority"], list)
    assert isinstance(data["tickets_by_category"], list)
    assert isinstance(data["tickets_by_source"], list)
    assert isinstance(data["tickets_by_sla_status"], list)
    assert isinstance(data["recent_ticket_trend"], list)

    assert len(data["recent_ticket_trend"]) == 7


def test_audit_logs_list_contains_ticket_created(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)

    response = client.get("/audit-logs", headers=headers)

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert data["limit"] == 50
    assert data["offset"] == 0
    assert isinstance(data["items"], list)

    actions = [item["action"] for item in data["items"]]

    assert "TICKET_CREATED" in actions

    ticket_ids = [item["ticket_id"] for item in data["items"] if item["ticket_id"]]

    assert ticket_id in ticket_ids


def test_audit_logs_filter_by_action(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    create_ticket(client, headers)

    response = client.get(
        "/audit-logs",
        headers=headers,
        params={
            "action": "TICKET_CREATED",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    for item in data["items"]:
        assert item["action"] == "TICKET_CREATED"


def test_audit_logs_filter_by_ticket_id(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers, subject="Audit filter pytest ticket")

    response = client.get(
        "/audit-logs",
        headers=headers,
        params={
            "ticket_id": ticket_id,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    for item in data["items"]:
        assert item["ticket_id"] == ticket_id