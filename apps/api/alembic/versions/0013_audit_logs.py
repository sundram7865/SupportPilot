"""audit logs

Revision ID: 0013_audit_logs
Revises: 0012_ticket_sla
Create Date: 2026-06-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_audit_logs"
down_revision = "0012_ticket_sla"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reply_draft_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=100), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_resource_id", "audit_logs", ["resource_id"])
    op.create_index("ix_audit_logs_ticket_id", "audit_logs", ["ticket_id"])
    op.create_index("ix_audit_logs_agent_run_id", "audit_logs", ["agent_run_id"])
    op.create_index("ix_audit_logs_tool_execution_id", "audit_logs", ["tool_execution_id"])
    op.create_index("ix_audit_logs_approval_request_id", "audit_logs", ["approval_request_id"])
    op.create_index("ix_audit_logs_reply_draft_id", "audit_logs", ["reply_draft_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_index(
        "ix_audit_logs_org_created_at",
        "audit_logs",
        ["organization_id", "created_at"],
    )

    op.create_index(
        "ix_audit_logs_org_action_created_at",
        "audit_logs",
        ["organization_id", "action", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_org_action_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_org_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_reply_draft_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_approval_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tool_execution_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_agent_run_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_ticket_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_organization_id", table_name="audit_logs")

    op.drop_table("audit_logs")