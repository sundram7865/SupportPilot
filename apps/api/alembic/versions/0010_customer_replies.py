"""customer reply draft review and send workflow

Revision ID: 0010_replies
Revises: 0009_approvals
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_replies"
down_revision = "0009_approvals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_reply_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approval_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rejected_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sent_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sent_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="AGENT"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("approval_reason", sa.Text(), nullable=True),
        sa.Column("send_notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["rejected_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sent_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sent_message_id"], ["ticket_messages.id"], ondelete="SET NULL"),
    )

    op.create_index("ix_customer_reply_drafts_organization_id", "customer_reply_drafts", ["organization_id"])
    op.create_index("ix_customer_reply_drafts_ticket_id", "customer_reply_drafts", ["ticket_id"])
    op.create_index("ix_customer_reply_drafts_agent_run_id", "customer_reply_drafts", ["agent_run_id"])
    op.create_index("ix_customer_reply_drafts_approval_request_id", "customer_reply_drafts", ["approval_request_id"])
    op.create_index("ix_customer_reply_drafts_created_by_user_id", "customer_reply_drafts", ["created_by_user_id"])
    op.create_index("ix_customer_reply_drafts_updated_by_user_id", "customer_reply_drafts", ["updated_by_user_id"])
    op.create_index("ix_customer_reply_drafts_approved_by_user_id", "customer_reply_drafts", ["approved_by_user_id"])
    op.create_index("ix_customer_reply_drafts_rejected_by_user_id", "customer_reply_drafts", ["rejected_by_user_id"])
    op.create_index("ix_customer_reply_drafts_sent_by_user_id", "customer_reply_drafts", ["sent_by_user_id"])
    op.create_index("ix_customer_reply_drafts_sent_message_id", "customer_reply_drafts", ["sent_message_id"])
    op.create_index("ix_customer_reply_drafts_source", "customer_reply_drafts", ["source"])
    op.create_index("ix_customer_reply_drafts_status", "customer_reply_drafts", ["status"])
    op.create_index("ix_customer_reply_drafts_created_at", "customer_reply_drafts", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_customer_reply_drafts_created_at", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_status", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_source", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_sent_message_id", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_sent_by_user_id", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_rejected_by_user_id", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_approved_by_user_id", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_updated_by_user_id", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_created_by_user_id", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_approval_request_id", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_agent_run_id", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_ticket_id", table_name="customer_reply_drafts")
    op.drop_index("ix_customer_reply_drafts_organization_id", table_name="customer_reply_drafts")
    op.drop_table("customer_reply_drafts")