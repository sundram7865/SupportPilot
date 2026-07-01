def create_ticket(client, headers, subject: str = "Reply workflow pytest ticket") -> str:
    response = client.post(
        "/tickets",
        headers=headers,
        json={
            "subject": subject,
            "description": "Customer is asking for support and needs a reply.",
            "priority": "MEDIUM",
            "category": "ORDER_STATUS",
            "source": "SUPPORT_FORM",
            "customer_name": "Reply Test Customer",
            "customer_email": "reply.customer@example.com",
            "customer_phone": "+91-9999999999",
            "external_order_id": "ORD-1001",
            "metadata_json": {
                "test": True,
                "suite": "replies",
            },
        },
    )

    assert response.status_code == 200

    return response.json()["id"]


def create_reply_draft(client, headers, ticket_id: str) -> dict:
    response = client.post(
        "/replies/drafts",
        headers=headers,
        json={
            "ticket_id": ticket_id,
            "subject": "Update about your order",
            "body": "Hi, thanks for reaching out. We are checking your order and will update you shortly.",
            "source": "AGENT",
            "metadata_json": {
                "test": True,
                "created_by": "pytest",
            },
        },
    )

    assert response.status_code == 200

    return response.json()


def submit_reply_for_approval(client, headers, draft_id: str) -> dict:
    response = client.post(
        f"/replies/drafts/{draft_id}/submit-approval",
        headers=headers,
        json={
            "request_reason": "Please review this customer reply before sending.",
        },
    )

    assert response.status_code == 200

    return response.json()


def test_create_reply_draft(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
    draft = create_reply_draft(client, headers, ticket_id)

    assert draft["id"]
    assert draft["ticket_id"] == ticket_id
    assert draft["source"] == "AGENT"
    assert draft["status"] == "DRAFT"
    assert draft["subject"] == "Update about your order"
    assert "thanks for reaching out" in draft["body"]
    assert draft["approval_request_id"] is None
    assert draft["sent_message_id"] is None


def test_list_and_get_reply_draft(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
    draft = create_reply_draft(client, headers, ticket_id)

    list_response = client.get(
        f"/replies/tickets/{ticket_id}/drafts",
        headers=headers,
    )

    assert list_response.status_code == 200

    list_data = list_response.json()

    assert list_data["total"] >= 1

    draft_ids = [item["id"] for item in list_data["items"]]

    assert draft["id"] in draft_ids

    get_response = client.get(
        f"/replies/drafts/{draft['id']}",
        headers=headers,
    )

    assert get_response.status_code == 200

    fetched = get_response.json()

    assert fetched["id"] == draft["id"]
    assert fetched["ticket_id"] == ticket_id
    assert fetched["status"] == "DRAFT"


def test_update_reply_draft(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
    draft = create_reply_draft(client, headers, ticket_id)

    response = client.patch(
        f"/replies/drafts/{draft['id']}",
        headers=headers,
        json={
            "subject": "Updated order support reply",
            "body": "Hi, we checked your order and our team is working on the next update.",
            "metadata_json": {
                "test": True,
                "updated_by": "pytest",
            },
        },
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["id"] == draft["id"]
    assert updated["status"] == "DRAFT"
    assert updated["subject"] == "Updated order support reply"
    assert "checked your order" in updated["body"]


def test_submit_and_approve_reply_draft(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
    draft = create_reply_draft(client, headers, ticket_id)

    submitted = submit_reply_for_approval(client, headers, draft["id"])

    assert submitted["id"] == draft["id"]
    assert submitted["status"] == "PENDING_APPROVAL"
    assert submitted["approval_request_id"] is not None

    approve_response = client.post(
        f"/replies/drafts/{draft['id']}/approve",
        headers=headers,
        json={
            "reason": "Reply is accurate and safe to send.",
        },
    )

    assert approve_response.status_code == 200

    approved = approve_response.json()

    assert approved["id"] == draft["id"]
    assert approved["status"] == "APPROVED"
    assert approved["approval_reason"] == "Reply is accurate and safe to send."
    assert approved["approved_by_user_id"] is not None
    assert approved["approved_at"] is not None


def test_reject_reply_draft_then_edit_again(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
    draft = create_reply_draft(client, headers, ticket_id)

    submitted = submit_reply_for_approval(client, headers, draft["id"])

    assert submitted["status"] == "PENDING_APPROVAL"

    reject_response = client.post(
        f"/replies/drafts/{draft['id']}/reject",
        headers=headers,
        json={
            "reason": "Needs a more empathetic tone.",
        },
    )

    assert reject_response.status_code == 200

    rejected = reject_response.json()

    assert rejected["id"] == draft["id"]
    assert rejected["status"] == "REJECTED"
    assert rejected["rejection_reason"] == "Needs a more empathetic tone."
    assert rejected["rejected_by_user_id"] is not None

    update_response = client.patch(
        f"/replies/drafts/{draft['id']}",
        headers=headers,
        json={
            "body": "Hi, we are sorry for the inconvenience. We are checking this carefully and will update you shortly.",
        },
    )

    assert update_response.status_code == 200

    updated = update_response.json()

    assert updated["status"] == "DRAFT"
    assert updated["rejection_reason"] is None
    assert "sorry for the inconvenience" in updated["body"]


def test_send_approved_reply_draft(client, test_user_and_org):
    headers = test_user_and_org["dev_headers"]

    ticket_id = create_ticket(client, headers)
    draft = create_reply_draft(client, headers, ticket_id)

    submitted = submit_reply_for_approval(client, headers, draft["id"])

    assert submitted["status"] == "PENDING_APPROVAL"

    approve_response = client.post(
        f"/replies/drafts/{draft['id']}/approve",
        headers=headers,
        json={
            "reason": "Approved for customer delivery.",
        },
    )

    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"

    send_response = client.post(
        f"/replies/drafts/{draft['id']}/send",
        headers=headers,
        json={
            "send_notes": "Sent during pytest reply workflow validation.",
        },
    )

    assert send_response.status_code == 200

    sent = send_response.json()

    assert sent["id"] == draft["id"]
    assert sent["status"] == "SENT"
    assert sent["sent_by_user_id"] is not None
    assert sent["sent_message_id"] is not None
    assert sent["send_notes"] == "Sent during pytest reply workflow validation."
    assert sent["sent_at"] is not None

    ticket_response = client.get(
        f"/tickets/{ticket_id}",
        headers=headers,
    )

    assert ticket_response.status_code == 200

    ticket = ticket_response.json()

    message_ids = [message["id"] for message in ticket["messages"]]
    message_bodies = [message["body"] for message in ticket["messages"]]

    assert sent["sent_message_id"] in message_ids
    assert any("thanks for reaching out" in body for body in message_bodies)