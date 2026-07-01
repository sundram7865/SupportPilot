from uuid import uuid4


def create_ticket(client, headers) -> str:
    response = client.post(
        "/tickets",
        headers=headers,
        json={
            "subject": "Tool approval pytest ticket",
            "description": "Customer asks about order ORD-1001 and refund eligibility.",
            "priority": "HIGH",
            "category": "PAYMENT_ISSUE",
            "source": "SUPPORT_FORM",
            "customer_name": "Tool Test Customer",
            "customer_email": "tool.customer@example.com",
            "customer_phone": "+91-9999999999",
            "external_order_id": "ORD-1001",
            "metadata_json": {
                "test": True,
                "suite": "tools_approvals",
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

    data = response.json()

    assert data["provider"] == "URBANKART"
    assert data["status"] == "ACTIVE"

    return data


def test_read_only_tool_execution_success(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
    configure_urbankart_integration(client, headers)

    response = client.post(
        "/tools/execute",
        headers=headers,
        json={
            "tool_name": "urbankart_get_order_context",
            "ticket_id": ticket_id,
            "args": {
                "order_id": "ORD-1001",
            },
            "idempotency_key": f"pytest-order-context-{uuid4()}",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"]
    assert data["ticket_id"] == ticket_id
    assert data["tool_name"] == "urbankart_get_order_context"
    assert data["risk_level"] == "READ_ONLY"
    assert data["status"] == "SUCCESS"
    assert data["approval_status"] == "NOT_REQUIRED"
    assert data["output_json"] is not None


def test_tool_execution_idempotency_returns_same_execution(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
    configure_urbankart_integration(client, headers)

    idempotency_key = f"pytest-idempotency-{uuid4()}"

    payload = {
        "tool_name": "urbankart_get_order_context",
        "ticket_id": ticket_id,
        "args": {
            "order_id": "ORD-1001",
        },
        "idempotency_key": idempotency_key,
    }

    first_response = client.post(
        "/tools/execute",
        headers=headers,
        json=payload,
    )

    second_response = client.post(
        "/tools/execute",
        headers=headers,
        json=payload,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first = first_response.json()
    second = second_response.json()

    assert first["id"] == second["id"]
    assert first["idempotency_key"] == idempotency_key
    assert second["idempotency_key"] == idempotency_key


def test_list_ticket_tool_executions(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
    configure_urbankart_integration(client, headers)

    execute_response = client.post(
        "/tools/execute",
        headers=headers,
        json={
            "tool_name": "urbankart_get_order_context",
            "ticket_id": ticket_id,
            "args": {
                "order_id": "ORD-1001",
            },
            "idempotency_key": f"pytest-list-tools-{uuid4()}",
        },
    )

    assert execute_response.status_code == 200

    response = client.get(
        f"/tools/tickets/{ticket_id}/executions",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    tool_names = [item["tool_name"] for item in data["items"]]

    assert "urbankart_get_order_context" in tool_names


def test_risky_refund_tool_blocks_and_can_request_approval(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
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
                "reason": "Payment deducted but order issue reported by customer.",
            },
            "idempotency_key": f"pytest-refund-approval-{uuid4()}",
        },
    )

    assert execute_response.status_code == 200

    execution = execute_response.json()

    assert execution["id"]
    assert execution["ticket_id"] == ticket_id
    assert execution["tool_name"] == "urbankart_request_refund"
    assert execution["status"] == "BLOCKED_APPROVAL_REQUIRED"
    assert execution["approval_status"] in {"REQUIRED", "PENDING"}

    approval_response = client.post(
        f"/approvals/tool-executions/{execution['id']}/request",
        headers=headers,
        json={
            "request_reason": "Refund is a high-risk write action and needs human approval.",
            "metadata_json": {
                "test": True,
                "source": "pytest",
            },
        },
    )

    assert approval_response.status_code == 200

    approval = approval_response.json()

    assert approval["id"]
    assert approval["ticket_id"] == ticket_id
    assert approval["tool_execution_id"] == execution["id"]
    assert approval["request_type"] == "TOOL_EXECUTION"
    assert approval["status"] == "PENDING"
    assert approval["tool_name"] == "urbankart_request_refund"


def test_list_and_get_approval(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
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
                "reason": "Customer requested refund.",
            },
            "idempotency_key": f"pytest-list-approval-{uuid4()}",
        },
    )

    assert execute_response.status_code == 200

    execution_id = execute_response.json()["id"]

    approval_response = client.post(
        f"/approvals/tool-executions/{execution_id}/request",
        headers=headers,
        json={
            "request_reason": "Approval required for refund tool.",
            "metadata_json": {
                "test": True,
            },
        },
    )

    assert approval_response.status_code == 200

    approval_id = approval_response.json()["id"]

    list_response = client.get("/approvals", headers=headers)

    assert list_response.status_code == 200

    list_data = list_response.json()

    assert list_data["total"] >= 1

    ids = [item["id"] for item in list_data["items"]]

    assert approval_id in ids

    get_response = client.get(
        f"/approvals/{approval_id}",
        headers=headers,
    )

    assert get_response.status_code == 200

    approval = get_response.json()

    assert approval["id"] == approval_id
    assert approval["status"] == "PENDING"


def test_reject_approval(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
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
                "reason": "Customer requested refund.",
            },
            "idempotency_key": f"pytest-reject-approval-{uuid4()}",
        },
    )

    assert execute_response.status_code == 200

    execution_id = execute_response.json()["id"]

    approval_response = client.post(
        f"/approvals/tool-executions/{execution_id}/request",
        headers=headers,
        json={
            "request_reason": "Approval required for refund tool.",
            "metadata_json": {
                "test": True,
            },
        },
    )

    assert approval_response.status_code == 200

    approval_id = approval_response.json()["id"]

    reject_response = client.post(
        f"/approvals/{approval_id}/reject",
        headers=headers,
        json={
            "decision_reason": "Rejected during pytest validation.",
        },
    )

    assert reject_response.status_code == 200

    rejected = reject_response.json()

    assert rejected["id"] == approval_id
    assert rejected["status"] == "REJECTED"
    assert rejected["decision_reason"] == "Rejected during pytest validation."