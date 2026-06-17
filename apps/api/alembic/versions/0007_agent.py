"""langgraph agent foundation

Revision ID: 0007_agent
Revises: 0006_knowledge
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_agent"
down_revision = "0006_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("started_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="STARTED"),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="mock"),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("detected_category", sa.String(length=80), nullable=True),
        sa.Column("detected_priority", sa.String(length=50), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=False, server_default="LOW"),
        sa.Column("decision", sa.String(length=80), nullable=False, server_default="NO_ACTION"),
        sa.Column("draft_response", sa.Text(), nullable=True),
        sa.Column("reasoning_summary", sa.Text(), nullable=True),
        sa.Column("planned_tools", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("retrieved_context", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("final_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["started_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_agent_runs_organization_id", "agent_runs", ["organization_id"])
    op.create_index("ix_agent_runs_ticket_id", "agent_runs", ["ticket_id"])
    op.create_index("ix_agent_runs_started_by_user_id", "agent_runs", ["started_by_user_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    op.create_index("ix_agent_runs_risk_level", "agent_runs", ["risk_level"])
    op.create_index("ix_agent_runs_decision", "agent_runs", ["decision"])
    op.create_index("ix_agent_runs_created_at", "agent_runs", ["created_at"])

    op.create_table(
        "agent_run_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("step_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="STARTED"),
        sa.Column("input_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_agent_run_steps_organization_id", "agent_run_steps", ["organization_id"])
    op.create_index("ix_agent_run_steps_agent_run_id", "agent_run_steps", ["agent_run_id"])
    op.create_index("ix_agent_run_steps_ticket_id", "agent_run_steps", ["ticket_id"])
    op.create_index("ix_agent_run_steps_step_name", "agent_run_steps", ["step_name"])
    op.create_index("ix_agent_run_steps_created_at", "agent_run_steps", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_agent_run_steps_created_at", table_name="agent_run_steps")
    op.drop_index("ix_agent_run_steps_step_name", table_name="agent_run_steps")
    op.drop_index("ix_agent_run_steps_ticket_id", table_name="agent_run_steps")
    op.drop_index("ix_agent_run_steps_agent_run_id", table_name="agent_run_steps")
    op.drop_index("ix_agent_run_steps_organization_id", table_name="agent_run_steps")
    op.drop_table("agent_run_steps")

    op.drop_index("ix_agent_runs_created_at", table_name="agent_runs")
    op.drop_index("ix_agent_runs_decision", table_name="agent_runs")
    op.drop_index("ix_agent_runs_risk_level", table_name="agent_runs")
    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_started_by_user_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_ticket_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_organization_id", table_name="agent_runs")
    op.drop_table("agent_runs")