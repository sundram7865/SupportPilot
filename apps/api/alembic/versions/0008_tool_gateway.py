"""tool gateway and safe tool execution

Revision ID: 0008_tools
Revises: 0007_agent
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_tools"
down_revision = "0007_agent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tool_executions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("risk_level", sa.String(length=50), nullable=False, server_default="READ_ONLY"),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="STARTED"),
        sa.Column("approval_status", sa.String(length=80), nullable=False, server_default="NOT_REQUIRED"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("input_args", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "organization_id",
            "idempotency_key",
            name="uq_tool_execution_org_idempotency_key",
        ),
    )

    op.create_index("ix_tool_executions_organization_id", "tool_executions", ["organization_id"])
    op.create_index("ix_tool_executions_ticket_id", "tool_executions", ["ticket_id"])
    op.create_index("ix_tool_executions_agent_run_id", "tool_executions", ["agent_run_id"])
    op.create_index("ix_tool_executions_requested_by_user_id", "tool_executions", ["requested_by_user_id"])
    op.create_index("ix_tool_executions_tool_name", "tool_executions", ["tool_name"])
    op.create_index("ix_tool_executions_risk_level", "tool_executions", ["risk_level"])
    op.create_index("ix_tool_executions_status", "tool_executions", ["status"])
    op.create_index("ix_tool_executions_approval_status", "tool_executions", ["approval_status"])
    op.create_index("ix_tool_executions_idempotency_key", "tool_executions", ["idempotency_key"])
    op.create_index("ix_tool_executions_created_at", "tool_executions", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_tool_executions_created_at", table_name="tool_executions")
    op.drop_index("ix_tool_executions_idempotency_key", table_name="tool_executions")
    op.drop_index("ix_tool_executions_approval_status", table_name="tool_executions")
    op.drop_index("ix_tool_executions_status", table_name="tool_executions")
    op.drop_index("ix_tool_executions_risk_level", table_name="tool_executions")
    op.drop_index("ix_tool_executions_tool_name", table_name="tool_executions")
    op.drop_index("ix_tool_executions_requested_by_user_id", table_name="tool_executions")
    op.drop_index("ix_tool_executions_agent_run_id", table_name="tool_executions")
    op.drop_index("ix_tool_executions_ticket_id", table_name="tool_executions")
    op.drop_index("ix_tool_executions_organization_id", table_name="tool_executions")
    op.drop_table("tool_executions")