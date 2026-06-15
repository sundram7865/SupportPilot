"""ticket lifecycle state machine

Revision ID: 0005_lifecycle
Revises: 0004_tickets
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_lifecycle"
down_revision = "0004_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "tickets",
        sa.Column("status_changed_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    op.add_column(
        "tickets",
        sa.Column("status_reason", sa.Text(), nullable=True),
    )

    op.create_foreign_key(
        "fk_tickets_status_changed_by_user_id_users",
        "tickets",
        "users",
        ["status_changed_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_tickets_status_changed_by_user_id",
        "tickets",
        ["status_changed_by_user_id"],
    )

    op.create_table(
        "ticket_status_transitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("from_status", sa.String(length=50), nullable=False),
        sa.Column("to_status", sa.String(length=50), nullable=False),
        sa.Column("trigger", sa.String(length=80), nullable=False, server_default="AGENT_ACTION"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_allowed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_index(
        "ix_ticket_status_transitions_organization_id",
        "ticket_status_transitions",
        ["organization_id"],
    )

    op.create_index(
        "ix_ticket_status_transitions_ticket_id",
        "ticket_status_transitions",
        ["ticket_id"],
    )

    op.create_index(
        "ix_ticket_status_transitions_actor_user_id",
        "ticket_status_transitions",
        ["actor_user_id"],
    )

    op.create_index(
        "ix_ticket_status_transitions_from_status",
        "ticket_status_transitions",
        ["from_status"],
    )

    op.create_index(
        "ix_ticket_status_transitions_to_status",
        "ticket_status_transitions",
        ["to_status"],
    )

    op.create_index(
        "ix_ticket_status_transitions_trigger",
        "ticket_status_transitions",
        ["trigger"],
    )

    op.create_index(
        "ix_ticket_status_transitions_created_at",
        "ticket_status_transitions",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_status_transitions_created_at", table_name="ticket_status_transitions")
    op.drop_index("ix_ticket_status_transitions_trigger", table_name="ticket_status_transitions")
    op.drop_index("ix_ticket_status_transitions_to_status", table_name="ticket_status_transitions")
    op.drop_index("ix_ticket_status_transitions_from_status", table_name="ticket_status_transitions")
    op.drop_index("ix_ticket_status_transitions_actor_user_id", table_name="ticket_status_transitions")
    op.drop_index("ix_ticket_status_transitions_ticket_id", table_name="ticket_status_transitions")
    op.drop_index("ix_ticket_status_transitions_organization_id", table_name="ticket_status_transitions")
    op.drop_table("ticket_status_transitions")

    op.drop_index("ix_tickets_status_changed_by_user_id", table_name="tickets")
    op.drop_constraint("fk_tickets_status_changed_by_user_id_users", "tickets", type_="foreignkey")

    op.drop_column("tickets", "status_reason")
    op.drop_column("tickets", "status_changed_by_user_id")
    op.drop_column("tickets", "status_changed_at")