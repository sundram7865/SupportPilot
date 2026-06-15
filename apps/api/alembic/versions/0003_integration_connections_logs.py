"""integration connections and external api logs

Revision ID: 0003_integrations
Revises: 0002_auth_organizations_rbac
Create Date: 2026-06-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_integrations"
down_revision = "0002_auth_organizations_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "integration_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False, server_default="URBANKART"),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
        sa.Column("last_health_status", sa.String(length=50), nullable=True),
        sa.Column("last_health_message", sa.Text(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "provider", name="uq_integration_connection_org_provider"),
    )

    op.create_index(
        "ix_integration_connections_organization_id",
        "integration_connections",
        ["organization_id"],
    )

    op.create_table(
        "external_api_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("integration_connection_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("request_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["integration_connection_id"], ["integration_connections.id"], ondelete="SET NULL"),
    )

    op.create_index(
        "ix_external_api_logs_organization_id",
        "external_api_logs",
        ["organization_id"],
    )

    op.create_index(
        "ix_external_api_logs_integration_connection_id",
        "external_api_logs",
        ["integration_connection_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_external_api_logs_integration_connection_id", table_name="external_api_logs")
    op.drop_index("ix_external_api_logs_organization_id", table_name="external_api_logs")
    op.drop_table("external_api_logs")

    op.drop_index("ix_integration_connections_organization_id", table_name="integration_connections")
    op.drop_table("integration_connections")