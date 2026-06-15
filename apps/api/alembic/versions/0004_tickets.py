"""core ticketing system

Revision ID: 0004_tickets
Revises: 0003_integrations
Create Date: 2026-06-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0004_tickets"
down_revision = "0003_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_number", sa.String(length=50), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="OPEN"),
        sa.Column("priority", sa.String(length=50), nullable=False, server_default="MEDIUM"),
        sa.Column("category", sa.String(length=80), nullable=False, server_default="OTHER"),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="SUPPORT_FORM"),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("customer_email", sa.String(length=255), nullable=False),
        sa.Column("customer_phone", sa.String(length=50), nullable=True),
        sa.Column("external_order_id", sa.String(length=100), nullable=True),
        sa.Column("assigned_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("ai_confidence_score", sa.Integer(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_to_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_tickets_organization_id", "tickets", ["organization_id"])
    op.create_index("ix_tickets_ticket_number", "tickets", ["ticket_number"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])
    op.create_index("ix_tickets_category", "tickets", ["category"])
    op.create_index("ix_tickets_customer_email", "tickets", ["customer_email"])
    op.create_index("ix_tickets_external_order_id", "tickets", ["external_order_id"])
    op.create_index("ix_tickets_assigned_to_user_id", "tickets", ["assigned_to_user_id"])
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])

    op.create_unique_constraint(
        "uq_tickets_org_ticket_number",
        "tickets",
        ["organization_id", "ticket_number"],
    )

    op.create_table(
        "ticket_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sender_type", sa.String(length=50), nullable=False, server_default="CUSTOMER"),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sender_name", sa.String(length=255), nullable=True),
        sa.Column("sender_email", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_ticket_messages_organization_id", "ticket_messages", ["organization_id"])
    op.create_index("ix_ticket_messages_ticket_id", "ticket_messages", ["ticket_id"])
    op.create_index("ix_ticket_messages_sender_type", "ticket_messages", ["sender_type"])
    op.create_index("ix_ticket_messages_sender_user_id", "ticket_messages", ["sender_user_id"])
    op.create_index("ix_ticket_messages_created_at", "ticket_messages", ["created_at"])

    op.create_table(
        "ticket_internal_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_ticket_internal_notes_organization_id", "ticket_internal_notes", ["organization_id"])
    op.create_index("ix_ticket_internal_notes_ticket_id", "ticket_internal_notes", ["ticket_id"])
    op.create_index("ix_ticket_internal_notes_author_user_id", "ticket_internal_notes", ["author_user_id"])
    op.create_index("ix_ticket_internal_notes_created_at", "ticket_internal_notes", ["created_at"])

    op.create_table(
        "ticket_timeline_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False, server_default="TICKET_CREATED"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("old_value", sa.String(length=255), nullable=True),
        sa.Column("new_value", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_ticket_timeline_events_organization_id", "ticket_timeline_events", ["organization_id"])
    op.create_index("ix_ticket_timeline_events_ticket_id", "ticket_timeline_events", ["ticket_id"])
    op.create_index("ix_ticket_timeline_events_actor_user_id", "ticket_timeline_events", ["actor_user_id"])
    op.create_index("ix_ticket_timeline_events_event_type", "ticket_timeline_events", ["event_type"])
    op.create_index("ix_ticket_timeline_events_created_at", "ticket_timeline_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ticket_timeline_events_created_at", table_name="ticket_timeline_events")
    op.drop_index("ix_ticket_timeline_events_event_type", table_name="ticket_timeline_events")
    op.drop_index("ix_ticket_timeline_events_actor_user_id", table_name="ticket_timeline_events")
    op.drop_index("ix_ticket_timeline_events_ticket_id", table_name="ticket_timeline_events")
    op.drop_index("ix_ticket_timeline_events_organization_id", table_name="ticket_timeline_events")
    op.drop_table("ticket_timeline_events")

    op.drop_index("ix_ticket_internal_notes_created_at", table_name="ticket_internal_notes")
    op.drop_index("ix_ticket_internal_notes_author_user_id", table_name="ticket_internal_notes")
    op.drop_index("ix_ticket_internal_notes_ticket_id", table_name="ticket_internal_notes")
    op.drop_index("ix_ticket_internal_notes_organization_id", table_name="ticket_internal_notes")
    op.drop_table("ticket_internal_notes")

    op.drop_index("ix_ticket_messages_created_at", table_name="ticket_messages")
    op.drop_index("ix_ticket_messages_sender_user_id", table_name="ticket_messages")
    op.drop_index("ix_ticket_messages_sender_type", table_name="ticket_messages")
    op.drop_index("ix_ticket_messages_ticket_id", table_name="ticket_messages")
    op.drop_index("ix_ticket_messages_organization_id", table_name="ticket_messages")
    op.drop_table("ticket_messages")

    op.drop_constraint("uq_tickets_org_ticket_number", "tickets", type_="unique")
    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_index("ix_tickets_assigned_to_user_id", table_name="tickets")
    op.drop_index("ix_tickets_external_order_id", table_name="tickets")
    op.drop_index("ix_tickets_customer_email", table_name="tickets")
    op.drop_index("ix_tickets_category", table_name="tickets")
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_ticket_number", table_name="tickets")
    op.drop_index("ix_tickets_organization_id", table_name="tickets")
    op.drop_table("tickets")