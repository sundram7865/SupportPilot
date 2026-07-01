import os
import re
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.common.enums import (
    KnowledgeDocumentStatus,
    KnowledgeDocumentType,
    KnowledgeIngestionStatus,
    MemberStatus,
    OrganizationRole,
    TicketCategory,
    TicketMessageSenderType,
    TicketPriority,
    TicketSlaStatus,
    TicketSource,
    TicketStatus,
    TicketTimelineEventType,
)
from app.db.base import import_all_models
from app.db.session import SessionLocal
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.tickets.models import Ticket, TicketMessage, TicketTimelineEvent
from app.modules.tickets.sla import initialize_ticket_sla
from app.modules.users.models import User


DEMO_USER_EMAIL = "demo-owner@supportpilot.local"
DEMO_ORG_NAME = "UrbanKart Demo"
DEMO_ORG_SLUG = "urbankart-demo"

DEMO_KB_TITLES = [
    "Demo Refund Policy",
    "Demo Shipping Policy",
    "Demo Damaged Product SOP",
    "Demo Legal Risk SOP",
    "Demo Support Tone Guide",
]

DEMO_TICKET_SUBJECTS = [
    "Where is my order ORD-1001?",
    "Payment deducted but order not created",
    "I will file consumer court complaint",
    "Product arrived damaged",
    "SLA near breach sample",
    "SLA breached sample",
]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def zero_embedding() -> list[float]:
    return [0.0 for _ in range(384)]


def get_or_create_demo_user(db) -> User:
    user = db.scalar(select(User).where(User.email == DEMO_USER_EMAIL))

    if user:
        return user

    user = User(
        clerk_user_id=None,
        email=DEMO_USER_EMAIL,
        name="SupportPilot Demo Owner",
        avatar_url=None,
    )

    db.add(user)
    db.flush()

    return user


def get_target_organization(db, demo_user: User) -> Organization:
    requested_slug = os.getenv("SUPPORTPILOT_DEMO_ORG_SLUG")

    if requested_slug:
        org = db.scalar(select(Organization).where(Organization.slug == requested_slug))

        if org:
            return org

    existing_org = db.scalar(select(Organization).order_by(Organization.created_at.asc()))

    if existing_org:
        return existing_org

    org = Organization(
        name=DEMO_ORG_NAME,
        slug=DEMO_ORG_SLUG,
        support_email="support@urbankart.demo",
        plan="DEMO",
    )

    db.add(org)
    db.flush()

    membership = OrganizationMember(
        organization_id=org.id,
        user_id=demo_user.id,
        role=OrganizationRole.OWNER.value,
        status=MemberStatus.ACTIVE.value,
    )

    db.add(membership)
    db.flush()

    return org


def delete_existing_demo_data(db, organization_id: uuid.UUID) -> None:
    demo_tickets = db.scalars(
        select(Ticket).where(
            Ticket.organization_id == organization_id,
            Ticket.subject.in_(DEMO_TICKET_SUBJECTS),
        )
    ).all()

    for ticket in demo_tickets:
        db.delete(ticket)

    demo_documents = db.scalars(
        select(KnowledgeDocument).where(
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.title.in_(DEMO_KB_TITLES),
        )
    ).all()

    for document in demo_documents:
        db.delete(document)

    db.flush()


def next_ticket_number(db, organization_id: uuid.UUID) -> str:
    ticket_numbers = db.scalars(
        select(Ticket.ticket_number).where(Ticket.organization_id == organization_id)
    ).all()

    max_number = 0

    for ticket_number in ticket_numbers:
        if not ticket_number:
            continue

        match = re.search(r"TICK-(\d+)", ticket_number)

        if match:
            max_number = max(max_number, int(match.group(1)))

    return f"TICK-{max_number + 1:05d}"


def add_timeline_event(
    db,
    organization_id: uuid.UUID,
    ticket_id: uuid.UUID,
    event_type: TicketTimelineEventType,
    title: str,
    description: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
) -> None:
    db.add(
        TicketTimelineEvent(
            organization_id=organization_id,
            ticket_id=ticket_id,
            actor_user_id=None,
            event_type=event_type.value,
            title=title,
            description=description,
            old_value=old_value,
            new_value=new_value,
            metadata_json={"demo_seed": True},
        )
    )


def add_customer_message(
    db,
    ticket: Ticket,
    body: str,
    customer_name: str,
    customer_email: str,
) -> None:
    db.add(
        TicketMessage(
            organization_id=ticket.organization_id,
            ticket_id=ticket.id,
            sender_type=TicketMessageSenderType.CUSTOMER.value,
            sender_user_id=None,
            sender_name=customer_name,
            sender_email=customer_email,
            body=body,
            is_public=True,
            metadata_json={"demo_seed": True},
        )
    )


def create_ticket(
    db,
    organization_id: uuid.UUID,
    subject: str,
    description: str,
    customer_name: str,
    customer_email: str,
    external_order_id: str | None,
    status: TicketStatus,
    priority: TicketPriority,
    category: TicketCategory,
    source: TicketSource = TicketSource.MANUAL,
    created_minutes_ago: int = 10,
) -> Ticket:
    created_at = now_utc() - timedelta(minutes=created_minutes_ago)

    ticket = Ticket(
        organization_id=organization_id,
        ticket_number=next_ticket_number(db, organization_id),
        subject=subject,
        description=description,
        status=status.value,
        status_changed_at=created_at,
        status_changed_by_user_id=None,
        status_reason="Created by demo seed script.",
        priority=priority.value,
        category=category.value,
        source=source.value,
        customer_name=customer_name,
        customer_email=customer_email,
        customer_phone="+91-9999999999",
        external_order_id=external_order_id,
        assigned_to_user_id=None,
        created_by_user_id=None,
        metadata_json={"demo_seed": True},
        created_at=created_at,
    )

    initialize_ticket_sla(ticket)

    db.add(ticket)
    db.flush()

    add_customer_message(
        db=db,
        ticket=ticket,
        customer_name=customer_name,
        customer_email=customer_email,
        body=description,
    )

    add_timeline_event(
        db=db,
        organization_id=organization_id,
        ticket_id=ticket.id,
        event_type=TicketTimelineEventType.TICKET_CREATED,
        title="Demo ticket created",
        description="Ticket was seeded for SupportPilot demo.",
    )

    return ticket


def seed_knowledge_documents(db, organization_id: uuid.UUID) -> None:
    documents = [
        {
            "title": "Demo Refund Policy",
            "document_type": KnowledgeDocumentType.REFUND_POLICY.value,
            "content": """
Refund Policy:
Refunds can be requested when payment is deducted but the order is not created,
when the order is cancelled before shipment, or when the product cannot be delivered.
Refunds above ₹1000 require human approval before execution.
Refunds should be processed only after checking payment and order status.
""".strip(),
        },
        {
            "title": "Demo Shipping Policy",
            "document_type": KnowledgeDocumentType.SHIPPING_POLICY.value,
            "content": """
Shipping Policy:
UrbanKart orders usually ship within 24 hours.
Customers can ask for order status using their order ID.
If shipment is out for delivery, support should share tracking status and expected delivery.
For delayed orders, support should check shipment details before replying.
""".strip(),
        },
        {
            "title": "Demo Damaged Product SOP",
            "document_type": KnowledgeDocumentType.SOP.value,
            "content": """
Damaged Product SOP:
Ask for photos of the damaged product and packaging.
Check order details before offering replacement.
Replacement requests are write actions and may require approval depending on risk.
Use a polite and apologetic tone.
""".strip(),
        },
        {
            "title": "Demo Legal Risk SOP",
            "document_type": KnowledgeDocumentType.SOP.value,
            "content": """
Legal Risk SOP:
If the customer mentions consumer court, legal notice, police complaint, fraud,
or public complaint, mark the ticket as legal risk.
Do not auto-resolve legal-risk tickets.
Escalate to a human manager for review.
""".strip(),
        },
        {
            "title": "Demo Support Tone Guide",
            "document_type": KnowledgeDocumentType.OTHER.value,
            "content": """
Support Tone Guide:
Be polite, concise, and helpful.
Acknowledge the customer's concern.
Avoid overpromising.
Explain the next action clearly.
For refunds or replacements, mention that the request is being reviewed.
""".strip(),
        },
    ]

    for item in documents:
        document = KnowledgeDocument(
            organization_id=organization_id,
            title=item["title"],
            document_type=item["document_type"],
            status=KnowledgeDocumentStatus.ACTIVE.value,
            content=item["content"],
            source_url=None,
            version=1,
            ingestion_status=KnowledgeIngestionStatus.INGESTED.value,
            ingestion_error=None,
            chunk_count=1,
            metadata_json={"demo_seed": True},
            created_by_user_id=None,
            updated_by_user_id=None,
            ingested_at=now_utc(),
        )

        db.add(document)
        db.flush()

        chunk = KnowledgeChunk(
            organization_id=organization_id,
            document_id=document.id,
            chunk_index=0,
            content=item["content"],
            token_count=len(item["content"].split()),
            embedding=zero_embedding(),
            metadata_json={"demo_seed": True},
        )

        db.add(chunk)


def seed_tickets(db, organization_id: uuid.UUID) -> None:
    create_ticket(
        db=db,
        organization_id=organization_id,
        subject="Where is my order ORD-1001?",
        description="Hi, where is my order ORD-1001? It was supposed to arrive today.",
        customer_name="Aarav Sharma",
        customer_email="aarav.demo@urbankart.local",
        external_order_id="ORD-1001",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        category=TicketCategory.ORDER_STATUS,
        created_minutes_ago=15,
    )

    create_ticket(
        db=db,
        organization_id=organization_id,
        subject="Payment deducted but order not created",
        description="My payment of ₹1499 was deducted but I cannot see the order in my account. Please refund it.",
        customer_name="Priya Mehta",
        customer_email="priya.demo@urbankart.local",
        external_order_id="ORD-1002",
        status=TicketStatus.OPEN,
        priority=TicketPriority.HIGH,
        category=TicketCategory.PAYMENT_ISSUE,
        created_minutes_ago=40,
    )

    create_ticket(
        db=db,
        organization_id=organization_id,
        subject="I will file consumer court complaint",
        description="This is fraud. I will file a consumer court complaint if my issue is not solved immediately.",
        customer_name="Rahul Verma",
        customer_email="rahul.demo@urbankart.local",
        external_order_id="ORD-1003",
        status=TicketStatus.OPEN,
        priority=TicketPriority.URGENT,
        category=TicketCategory.LEGAL_RISK,
        created_minutes_ago=55,
    )

    create_ticket(
        db=db,
        organization_id=organization_id,
        subject="Product arrived damaged",
        description="My UrbanStep Sneakers arrived damaged. The box was torn and the product has scratches.",
        customer_name="Neha Singh",
        customer_email="neha.demo@urbankart.local",
        external_order_id="ORD-1004",
        status=TicketStatus.OPEN,
        priority=TicketPriority.HIGH,
        category=TicketCategory.RETURN_REPLACEMENT,
        created_minutes_ago=30,
    )

    near_breach_ticket = create_ticket(
        db=db,
        organization_id=organization_id,
        subject="SLA near breach sample",
        description="This ticket is seeded to demonstrate near-breach SLA state.",
        customer_name="Demo Customer",
        customer_email="nearbreach.demo@urbankart.local",
        external_order_id="ORD-1005",
        status=TicketStatus.OPEN,
        priority=TicketPriority.HIGH,
        category=TicketCategory.OTHER,
        created_minutes_ago=58,
    )

    near_breach_ticket.first_response_due_at = now_utc() + timedelta(minutes=3)
    near_breach_ticket.resolution_due_at = now_utc() + timedelta(minutes=20)
    near_breach_ticket.sla_status = TicketSlaStatus.NEAR_BREACH.value
    near_breach_ticket.sla_near_breach_notified_at = now_utc()

    add_timeline_event(
        db=db,
        organization_id=organization_id,
        ticket_id=near_breach_ticket.id,
        event_type=TicketTimelineEventType.SLA_NEAR_BREACH,
        title="SLA near breach",
        description="Demo ticket is close to SLA breach.",
    )

    breached_ticket = create_ticket(
        db=db,
        organization_id=organization_id,
        subject="SLA breached sample",
        description="This ticket is seeded to demonstrate breached SLA state.",
        customer_name="Demo Customer",
        customer_email="breached.demo@urbankart.local",
        external_order_id="ORD-1006",
        status=TicketStatus.OPEN,
        priority=TicketPriority.URGENT,
        category=TicketCategory.OTHER,
        created_minutes_ago=120,
    )

    breached_ticket.first_response_due_at = now_utc() - timedelta(minutes=30)
    breached_ticket.resolution_due_at = now_utc() - timedelta(minutes=5)
    breached_ticket.sla_status = TicketSlaStatus.BREACHED.value
    breached_ticket.sla_breached_at = now_utc()

    add_timeline_event(
        db=db,
        organization_id=organization_id,
        ticket_id=breached_ticket.id,
        event_type=TicketTimelineEventType.SLA_BREACHED,
        title="SLA breached",
        description="Demo ticket has breached SLA.",
    )


def seed_demo() -> None:
    import_all_models()

    db = SessionLocal()

    try:
        demo_user = get_or_create_demo_user(db)
        organization = get_target_organization(db, demo_user)

        delete_existing_demo_data(db, organization.id)

        seed_knowledge_documents(db, organization.id)
        seed_tickets(db, organization.id)

        db.commit()

        print("✅ Demo data seeded successfully.")
        print(f"Organization: {organization.name}")
        print(f"Organization ID: {organization.id}")
        print("")
        print("Seeded demo tickets:")

        for subject in DEMO_TICKET_SUBJECTS:
            print(f" - {subject}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()                                                                                                                                                                                              