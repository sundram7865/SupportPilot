import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

# Keep tests in dev-auth mode.
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("DEV_AUTH_ENABLED", "true")

from app.common.enums import MemberStatus, OrganizationRole
from app.db.base import import_all_models
from app.db.session import SessionLocal
from app.main import app
from app.modules.approvals.models import ApprovalRequest
from app.modules.audit.models import AuditLog
from app.modules.integrations.models import ExternalApiLog, IntegrationConnection
from app.modules.organizations.models import Organization, OrganizationMember
from app.modules.tickets.models import (
    Ticket,
    TicketInternalNote,
    TicketMessage,
    TicketStatusTransition,
    TicketTimelineEvent,
)
from app.modules.tools.models import ToolExecution
from app.modules.users.models import User
from app.modules.replies.models import CustomerReplyDraft

@pytest.fixture(scope="session", autouse=True)
def load_models():
    import_all_models()


@pytest.fixture(scope="session")
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_user_and_org(db_session):
    unique = uuid4().hex[:10]

    user = User(
        clerk_user_id=f"test-owner-{unique}",
        email=f"test-owner-{unique}@urbankart.demo",
        name="Test Owner",
        avatar_url=None,
    )

    db_session.add(user)
    db_session.flush()

    organization = Organization(
        name=f"Test Org {unique}",
        slug=f"test-org-{unique}",
        support_email=f"support-{unique}@urbankart.demo",
        plan="TEST",
    )

    db_session.add(organization)
    db_session.flush()

    membership = OrganizationMember(
        organization_id=organization.id,
        user_id=user.id,
        role=OrganizationRole.OWNER.value,
        status=MemberStatus.ACTIVE.value,
    )

    db_session.add(membership)
    db_session.commit()

    try:
        yield {
            "user": user,
            "organization": organization,
            "dev_headers": {
                "x-dev-user-id": user.clerk_user_id,
                "x-dev-email": user.email,
                "x-dev-name": user.name,
                "x-organization-id": str(organization.id),
            },
        }

    finally:
        ticket_ids = db_session.scalars(
            select(Ticket.id).where(Ticket.organization_id == organization.id)
        ).all()
        db_session.execute(
            delete(AuditLog).where(AuditLog.organization_id == organization.id)
        )
        db_session.execute(
            delete(CustomerReplyDraft).where(
                 CustomerReplyDraft.organization_id == organization.id
            )
        )

        db_session.execute(
            delete(ApprovalRequest).where(
                ApprovalRequest.organization_id == organization.id
            )
        )

        db_session.execute(
            delete(ToolExecution).where(
                ToolExecution.organization_id == organization.id
            )
        )

        db_session.execute(
            delete(ExternalApiLog).where(
                ExternalApiLog.organization_id == organization.id
            )
        )

        db_session.execute(
            delete(IntegrationConnection).where(
                IntegrationConnection.organization_id == organization.id
            )
        )

        if ticket_ids:
            db_session.execute(
                delete(TicketTimelineEvent).where(
                    TicketTimelineEvent.ticket_id.in_(ticket_ids)
                )
            )
            db_session.execute(
                delete(TicketStatusTransition).where(
                    TicketStatusTransition.ticket_id.in_(ticket_ids)
                )
            )
            db_session.execute(
                delete(TicketInternalNote).where(
                    TicketInternalNote.ticket_id.in_(ticket_ids)
                )
            )
            db_session.execute(
                delete(TicketMessage).where(TicketMessage.ticket_id.in_(ticket_ids))
            )
            db_session.execute(delete(Ticket).where(Ticket.id.in_(ticket_ids)))

        db_session.execute(
            delete(OrganizationMember).where(
                OrganizationMember.organization_id == organization.id
            )
        )
        db_session.execute(delete(Organization).where(Organization.id == organization.id))
        db_session.execute(delete(User).where(User.id == user.id))

        db_session.commit()