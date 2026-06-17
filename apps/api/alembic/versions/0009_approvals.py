"""human approval workflow

Revision ID: 0009_approvals
Revises: 0008_tools
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_approvals"
down_revision = "0008_tools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "approval_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("request_type", sa.String(length=80), nullable=False, server_default="TOOL_EXECUTION"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=False, server_default="HIGH_RISK_WRITE"),
        sa.Column("tool_name", sa.String(length=100), nullable=True),
        sa.Column("input_args", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("request_reason", sa.Text(), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("result_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tool_execution_id"], ["tool_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decided_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "organization_id",
            "tool_execution_id",
            name="uq_approval_requests_org_tool_execution",
        ),
    )

    op.create_index("ix_approval_requests_organization_id", "approval_requests", ["organization_id"])
    op.create_index("ix_approval_requests_ticket_id", "approval_requests", ["ticket_id"])
    op.create_index("ix_approval_requests_agent_run_id", "approval_requests", ["agent_run_id"])
    op.create_index("ix_approval_requests_tool_execution_id", "approval_requests", ["tool_execution_id"])
    op.create_index("ix_approval_requests_requested_by_user_id", "approval_requests", ["requested_by_user_id"])
    op.create_index("ix_approval_requests_decided_by_user_id", "approval_requests", ["decided_by_user_id"])
    op.create_index("ix_approval_requests_request_type", "approval_requests", ["request_type"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index("ix_approval_requests_risk_level", "approval_requests", ["risk_level"])
    op.create_index("ix_approval_requests_tool_name", "approval_requests", ["tool_name"])
    op.create_index("ix_approval_requests_created_at", "approval_requests", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_approval_requests_created_at", table_name="approval_requests")
    op.drop_index("ix_approval_requests_tool_name", table_name="approval_requests")
    op.drop_index("ix_approval_requests_risk_level", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_request_type", table_name="approval_requests")
    op.drop_index("ix_approval_requests_decided_by_user_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_requested_by_user_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_tool_execution_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_agent_run_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_ticket_id", table_name="approval_requests")
    op.drop_index("ix_approval_requests_organization_id", table_name="approval_requests")
    op.drop_table("approval_requests")