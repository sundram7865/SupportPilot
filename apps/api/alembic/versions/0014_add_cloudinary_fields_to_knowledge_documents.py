"""add cloudinary fields to knowledge documents

Revision ID: 0014_cloudinary_knowledge
Revises: 0013_audit_logs
Create Date: 2026-08-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0014_cloudinary_knowledge"
down_revision = "0013_audit_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add Cloudinary and file management columns to knowledge_documents
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "cloudinary_public_id",
            sa.String(length=500),
            nullable=True,
        ),
    )
    
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "cloudinary_url",
            sa.String(length=2000),
            nullable=True,
        ),
    )
    
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "file_name",
            sa.String(length=500),
            nullable=True,
        ),
    )
    
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "file_size",
            sa.Integer(),
            nullable=True,
        ),
    )
    
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "file_type",
            sa.String(length=100),
            nullable=True,
        ),
    )
    
    op.add_column(
        "knowledge_documents",
        sa.Column(
            "content_extraction_status",
            sa.String(length=50),
            nullable=True,
            server_default="pending",
        ),
    )

    # Create indexes for new columns
    op.create_index(
        "ix_knowledge_documents_cloudinary_public_id",
        "knowledge_documents",
        ["cloudinary_public_id"],
        unique=False,
    )
    
    op.create_index(
        "ix_knowledge_documents_file_name",
        "knowledge_documents",
        ["file_name"],
        unique=False,
    )
    
    op.create_index(
        "ix_knowledge_documents_file_type",
        "knowledge_documents",
        ["file_type"],
        unique=False,
    )
    
    op.create_index(
        "ix_knowledge_documents_content_extraction_status",
        "knowledge_documents",
        ["content_extraction_status"],
        unique=False,
    )

    # Composite indexes for common queries
    op.create_index(
        "ix_knowledge_documents_org_file_type",
        "knowledge_documents",
        ["organization_id", "file_type"],
        unique=False,
    )
    
    op.create_index(
        "ix_knowledge_documents_org_extraction_status",
        "knowledge_documents",
        ["organization_id", "content_extraction_status"],
        unique=False,
    )

    # Set content_extraction_status for existing documents with content
    op.execute("""
        UPDATE knowledge_documents 
        SET content_extraction_status = 'extracted'
        WHERE content_extraction_status IS NULL 
        AND content IS NOT NULL 
        AND content != '';
    """)

    # Add comment on table for documentation
    op.execute("""
        COMMENT ON COLUMN knowledge_documents.cloudinary_public_id IS 'Cloudinary public ID for uploaded file';
        COMMENT ON COLUMN knowledge_documents.cloudinary_url IS 'Cloudinary secure URL for uploaded file';
        COMMENT ON COLUMN knowledge_documents.file_name IS 'Original file name of uploaded document';
        COMMENT ON COLUMN knowledge_documents.file_size IS 'File size in bytes';
        COMMENT ON COLUMN knowledge_documents.file_type IS 'File extension/type (pdf, docx, txt, etc.)';
        COMMENT ON COLUMN knowledge_documents.content_extraction_status IS 'Status of content extraction: pending, extracted, failed';
    """)


def downgrade() -> None:
    # Remove composite indexes first
    op.drop_index(
        "ix_knowledge_documents_org_extraction_status",
        table_name="knowledge_documents",
    )
    
    op.drop_index(
        "ix_knowledge_documents_org_file_type",
        table_name="knowledge_documents",
    )
    
    # Remove single column indexes
    op.drop_index(
        "ix_knowledge_documents_content_extraction_status",
        table_name="knowledge_documents",
    )
    
    op.drop_index(
        "ix_knowledge_documents_file_type",
        table_name="knowledge_documents",
    )
    
    op.drop_index(
        "ix_knowledge_documents_file_name",
        table_name="knowledge_documents",
    )
    
    op.drop_index(
        "ix_knowledge_documents_cloudinary_public_id",
        table_name="knowledge_documents",
    )

    # Remove columns
    op.drop_column("knowledge_documents", "content_extraction_status")
    op.drop_column("knowledge_documents", "file_type")
    op.drop_column("knowledge_documents", "file_size")
    op.drop_column("knowledge_documents", "file_name")
    op.drop_column("knowledge_documents", "cloudinary_url")
    op.drop_column("knowledge_documents", "cloudinary_public_id")