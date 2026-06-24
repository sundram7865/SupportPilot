"""ticket sla fields

Revision ID: 0012_ticket_sla
Revises: 0011_organization_invitations
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_ticket_sla"
down_revision = "0011_organization_invitations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column("first_response_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column("resolution_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "sla_status",
            sa.String(length=50),
            nullable=False,
            server_default="OK",
        ),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "sla_near_breach_notified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "tickets",
        sa.Column("sla_breached_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_tickets_first_response_due_at",
        "tickets",
        ["first_response_due_at"],
    )
    op.create_index(
        "ix_tickets_resolution_due_at",
        "tickets",
        ["resolution_due_at"],
    )
    op.create_index(
        "ix_tickets_sla_status",
        "tickets",
        ["sla_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_tickets_sla_status", table_name="tickets")
    op.drop_index("ix_tickets_resolution_due_at", table_name="tickets")
    op.drop_index("ix_tickets_first_response_due_at", table_name="tickets")

    op.drop_column("tickets", "sla_breached_at")
    op.drop_column("tickets", "sla_near_breach_notified_at")
    op.drop_column("tickets", "sla_status")
    op.drop_column("tickets", "resolution_due_at")
    op.drop_column("tickets", "first_response_due_at")