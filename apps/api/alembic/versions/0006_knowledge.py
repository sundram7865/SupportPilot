"""knowledge base and rag foundation

Revision ID: 0006_knowledge
Revises: 0005_lifecycle
Create Date: 2026-06-16
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0006_knowledge"
down_revision = "0005_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=80), nullable=False, server_default="OTHER"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="DRAFT"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ingestion_status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("ingestion_error", sa.Text(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("organization_id", "title", name="uq_knowledge_documents_org_title"),
    )

    op.create_index("ix_knowledge_documents_organization_id", "knowledge_documents", ["organization_id"])
    op.create_index("ix_knowledge_documents_title", "knowledge_documents", ["title"])
    op.create_index("ix_knowledge_documents_document_type", "knowledge_documents", ["document_type"])
    op.create_index("ix_knowledge_documents_status", "knowledge_documents", ["status"])
    op.create_index("ix_knowledge_documents_ingestion_status", "knowledge_documents", ["ingestion_status"])
    op.create_index("ix_knowledge_documents_created_at", "knowledge_documents", ["created_at"])

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", Vector(384), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_knowledge_chunks_organization_id", "knowledge_chunks", ["organization_id"])
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.create_index("ix_knowledge_chunks_created_at", "knowledge_chunks", ["created_at"])

    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding_cosine "
        "ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_embedding_cosine")

    op.drop_index("ix_knowledge_chunks_created_at", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_organization_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")

    op.drop_index("ix_knowledge_documents_created_at", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_ingestion_status", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_status", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_document_type", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_title", table_name="knowledge_documents")
    op.drop_index("ix_knowledge_documents_organization_id", table_name="knowledge_documents")
    op.drop_table("knowledge_documents")