def create_ticket_payload(subject: str = "Test ticket from pytest") -> dict:
    return {
        "subject": subject,
        "description": "Customer is asking about order ORD-TEST-1001.",
        "priority": "HIGH",
        "category": "ORDER_STATUS",
        "source": "SUPPORT_FORM",
        "customer_name": "Pytest Customer",
        "customer_email": "pytest.customer@example.com",
        "customer_phone": "+91-9999999999",
        "external_order_id": "ORD-TEST-1001",
        "metadata_json": {
            "test": True,
            "created_by": "pytest",
        },
    }


def test_create_ticket(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    response = client.post(
        "/tickets",
        headers=headers,
        json=create_ticket_payload(),
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"]
    assert data["ticket_number"].startswith("TICK-")
    assert data["subject"] == "Test ticket from pytest"
    assert data["status"] == "OPEN"
    assert data["priority"] == "HIGH"
    assert data["category"] == "ORDER_STATUS"
    assert data["source"] == "SUPPORT_FORM"
    assert data["customer_email"] == "pytest.customer@example.com"
    assert data["external_order_id"] == "ORD-TEST-1001"

    assert len(data["messages"]) == 1
    assert data["messages"][0]["sender_type"] == "CUSTOMER"

    assert len(data["timeline_events"]) >= 1

    event_types = [event["event_type"] for event in data["timeline_events"]]

    assert "TICKET_CREATED" in event_types
    assert "MESSAGE_ADDED" in event_types

def test_list_tickets(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    create_response = client.post(
        "/tickets",
        headers=headers,
        json=create_ticket_payload("List ticket pytest"),
    )

    assert create_response.status_code == 200

    response = client.get("/tickets", headers=headers)

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert data["total"] >= 1

    subjects = [item["subject"] for item in data["items"]]

    assert "List ticket pytest" in subjects


def test_get_ticket_detail(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    create_response = client.post(
        "/tickets",
        headers=headers,
        json=create_ticket_payload("Detail ticket pytest"),
    )

    assert create_response.status_code == 200

    ticket_id = create_response.json()["id"]

    response = client.get(f"/tickets/{ticket_id}", headers=headers)

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == ticket_id
    assert data["subject"] == "Detail ticket pytest"
    assert data["messages"]
    assert data["timeline_events"]


def test_get_ticket_timeline(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    create_response = client.post(
        "/tickets",
        headers=headers,
        json=create_ticket_payload("Timeline ticket pytest"),
    )

    assert create_response.status_code == 200

    ticket_id = create_response.json()["id"]

    response = client.get(f"/tickets/{ticket_id}/timeline", headers=headers)

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) >= 1

    event_types = [event["event_type"] for event in data]

    assert "TICKET_CREATED" in event_types
    assert "MESSAGE_ADDED" in event_types

def test_ticket_requires_organization_header(client, test_user_and_org):
    headers = dict(test_user_and_org["dev_headers"])
    headers.pop("x-organization-id")

    response = client.get("/tickets", headers=headers)

    assert response.status_code == 400

    data = response.json()

    assert data["error"]["message"] == (
        "x-organization-id header is required for organization-scoped routes."
    )
    assert data["error"]["status_code"] == 400
    assert data["error"]["request_id"]


def test_get_missing_ticket_returns_404(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    response = client.get(
        "/tickets/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )

    assert response.status_code == 404

    data = response.json()

    assert data["error"]["message"] == "Ticket not found."
    assert data["error"]["status_code"] == 404
    assert data["error"]["request_id"]