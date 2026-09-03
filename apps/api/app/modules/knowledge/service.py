from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import logging

from fastapi import UploadFile
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.common.cloudinary_service import CloudinaryService
from app.common.enums import KnowledgeDocumentStatus, KnowledgeIngestionStatus
from app.modules.knowledge.chunker import estimate_token_count, split_text_into_chunks
from app.modules.knowledge.content_extractor import ContentExtractor
from app.modules.knowledge.embeddings import embed_text, embed_texts_batch
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument

logger = logging.getLogger(__name__)


class KnowledgeService:
    def __init__(self, cloudinary_service: CloudinaryService):
        self.cloudinary_service = cloudinary_service
        self.content_extractor = ContentExtractor()
    
    async def create_document_with_file(
        self,
        db: Session,
        file: UploadFile,
        organization_id: UUID,
        user_id: UUID,
        title: Optional[str] = None,
        document_type: str = "OTHER",
        status: str = "DRAFT",
        metadata: Optional[dict] = None,
    ) -> KnowledgeDocument:
        """
        Complete pipeline:
        1. Upload to Cloudinary
        2. Extract text from file (PDF, DOCX, TXT, etc.)
        3. Save document to PostgreSQL
        4. Auto-ingest (chunk → embed → pgvector)
        """
        logger.info(f"Starting document upload for file: {file.filename}")
        
        # ========== STEP 1: Upload to Cloudinary ==========
        try:
            upload_result = await self.cloudinary_service.upload_document(
                file=file,
                organization_id=organization_id,
            )
            logger.info(f"Cloudinary upload successful: {upload_result['public_id']}")
        except Exception as e:
            logger.error(f"Cloudinary upload failed: {str(e)}")
            raise ValueError(f"Failed to upload file to Cloudinary: {str(e)}")
        
        # ========== STEP 2: Extract text content ==========
        try:
            file_content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            extracted_text = await self.content_extractor.extract_text(
                file_content=file_content,
                file_type=upload_result.get("format", ""),
                file_name=file.filename,
            )
            logger.info(f"Content extracted: {len(extracted_text or '')} characters")
        except Exception as e:
            logger.error(f"Content extraction failed: {str(e)}")
            extracted_text = None
        
        if not extracted_text or not extracted_text.strip():
            extracted_text = f"File uploaded: {file.filename}"
            logger.warning(f"No text content extracted from {file.filename}")
        
        # ========== STEP 3: Save document to database ==========
        document = KnowledgeDocument(
            organization_id=organization_id,
            title=title or file.filename,
            document_type=document_type,
            status=status,
            content=extracted_text,
            source_url=upload_result["url"],
            cloudinary_public_id=upload_result["public_id"],
            cloudinary_url=upload_result["url"],
            file_name=file.filename,
            file_size=upload_result["size_bytes"],
            file_type=upload_result.get("format", ""),
            content_extraction_status="extracted" if extracted_text else "failed",
            metadata_json=metadata,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
            ingestion_status=KnowledgeIngestionStatus.PENDING.value,
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        logger.info(f"Document saved: {document.id} - {document.title}")
        
        # ========== STEP 4: Auto-Ingest ==========
        # Only auto-ingest if we extracted meaningful content
        if extracted_text and extracted_text != f"File uploaded: {file.filename}":
            try:
                document = self.ingest_document(db, document)
                logger.info(
                    f"Auto-ingestion complete for {document.id}: "
                    f"{document.chunk_count} chunks created"
                )
            except Exception as e:
                logger.error(f"Auto-ingestion failed for {document.id}: {str(e)}")
                # Update document with error but don't fail the whole upload
                document.ingestion_status = KnowledgeIngestionStatus.FAILED.value
                document.ingestion_error = f"Auto-ingestion failed: {str(e)}"
                db.commit()
                db.refresh(document)
        else:
            logger.info(f"Skipping auto-ingest for {document.id}: no extractable content")
        
        return document
    
    def ingest_document(
        self,
        db: Session,
        document: KnowledgeDocument,
    ) -> KnowledgeDocument:
        """
        Core ingestion pipeline:
        1. Delete old chunks
        2. Split text into chunks (900 chars, 150 overlap)
        3. Generate embeddings (Gemini or lightweight fallback)
        4. Store chunks with embeddings in pgvector
        5. Update document status
        """
        logger.info(f"Starting ingestion for document: {document.id}")
        
        try:
            # ========== 1. Delete existing chunks ==========
            deleted_count = db.query(KnowledgeChunk).filter(
                KnowledgeChunk.document_id == document.id
            ).delete()
            logger.info(f"Deleted {deleted_count} existing chunks")
            
            # ========== 2. Split into chunks ==========
            raw_chunks = split_text_into_chunks(document.content)
            
            if not raw_chunks:
                raise ValueError("No content to ingest - chunking produced no chunks")
            
            logger.info(f"Text split into {len(raw_chunks)} chunks")
            
            # ========== 3. Generate embeddings ==========
            chunk_texts = list(raw_chunks)
            logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")
            
            try:
                embeddings = embed_texts_batch(chunk_texts)
                logger.info(f"Generated {len(embeddings)} embeddings (dim: {len(embeddings[0]) if embeddings else 0})")
            except Exception as e:
                logger.error(f"Embedding generation failed: {str(e)}")
                raise ValueError(f"Failed to generate embeddings: {str(e)}")
            
            # ========== 4. Store chunks in pgvector ==========
            for index, (chunk_text, embedding) in enumerate(zip(raw_chunks, embeddings)):
                chunk = KnowledgeChunk(
                    organization_id=document.organization_id,
                    document_id=document.id,
                    chunk_index=index,
                    content=chunk_text,
                    token_count=estimate_token_count(chunk_text),
                    embedding=embedding,  # pgvector Vector column
                    metadata_json={
                        "document_version": document.version,
                        "document_type": document.document_type,
                    },
                )
                db.add(chunk)
            
            logger.info(f"Created {len(raw_chunks)} chunk records")
            
            # ========== 5. Update document status ==========
            document.chunk_count = len(raw_chunks)
            document.ingestion_status = KnowledgeIngestionStatus.INGESTED.value
            document.ingestion_error = None
            document.ingested_at = datetime.now(timezone.utc)
            
            db.commit()
            db.refresh(document)
            
            logger.info(
                f"Ingestion complete for {document.id}: "
                f"status={document.ingestion_status}, chunks={document.chunk_count}"
            )
            
            return document
            
        except Exception as exc:
            logger.error(f"Ingestion failed for {document.id}: {str(exc)}")
            db.rollback()
            
            # Update document with error
            document.ingestion_status = KnowledgeIngestionStatus.FAILED.value
            document.ingestion_error = str(exc)
            db.commit()
            db.refresh(document)
            raise
    
    async def ingest_document_async(
        self,
        db: Session,
        document: KnowledgeDocument,
    ) -> KnowledgeDocument:
        """Async wrapper for ingestion"""
        return self.ingest_document(db, document)
    
    async def delete_document_with_cloudinary(
        self,
        db: Session,
        document: KnowledgeDocument,
    ) -> bool:
        """
        Delete document from both database and Cloudinary
        """
        logger.info(f"Deleting document: {document.id}")
        
        # Delete from Cloudinary if exists
        if document.cloudinary_public_id:
            try:
                await self.cloudinary_service.delete_document(document.cloudinary_public_id)
                logger.info(f"Deleted from Cloudinary: {document.cloudinary_public_id}")
            except Exception as e:
                logger.error(f"Failed to delete from Cloudinary: {str(e)}")
        
        # Delete from database (cascade will handle chunks)
        db.delete(document)
        db.commit()
        
        logger.info(f"Document deleted: {document.id}")
        return True
    
    async def update_document_file(
        self,
        db: Session,
        document: KnowledgeDocument,
        file: UploadFile,
    ) -> KnowledgeDocument:
        """
        Replace file: delete old from Cloudinary, upload new, re-ingest
        """
        logger.info(f"Updating file for document: {document.id}")
        
        # Delete old file from Cloudinary
        if document.cloudinary_public_id:
            try:
                await self.cloudinary_service.delete_document(document.cloudinary_public_id)
            except Exception as e:
                logger.warning(f"Failed to delete old file: {str(e)}")
        
        # Upload new file
        upload_result = await self.cloudinary_service.upload_document(
            file=file,
            organization_id=document.organization_id,
            document_id=document.id,
        )
        
        # Extract new content
        file_content = await file.read()
        await file.seek(0)
        
        extracted_text = await self.content_extractor.extract_text(
            file_content=file_content,
            file_type=upload_result.get("format", ""),
            file_name=file.filename,
        )
        
        # Update document fields
        document.content = extracted_text or document.content
        document.source_url = upload_result["url"]
        document.cloudinary_public_id = upload_result["public_id"]
        document.cloudinary_url = upload_result["url"]
        document.file_name = file.filename
        document.file_size = upload_result["size_bytes"]
        document.file_type = upload_result.get("format", "")
        document.version += 1
        document.ingestion_status = KnowledgeIngestionStatus.PENDING.value
        
        db.commit()
        db.refresh(document)
        
        # Re-ingest with new content
        if extracted_text:
            try:
                document = self.ingest_document(db, document)
                logger.info(f"Re-ingestion complete for {document.id}")
            except Exception as e:
                logger.error(f"Re-ingestion failed: {str(e)}")
        
        return document


# ============================================================================
# Legacy function compatibility
# ============================================================================

def ingest_document(
    db: Session,
    document: KnowledgeDocument,
) -> KnowledgeDocument:
    """Legacy wrapper for backward compatibility"""
    service = KnowledgeService(None)
    return service.ingest_document(db, document)


def search_knowledge_chunks(
    db: Session,
    organization_id: UUID,
    query: str,
    limit: int = 5,
    document_type: str | None = None,
) -> list:
    """
    Search knowledge base using pgvector cosine similarity.
    Embeds the query and finds nearest chunks in vector space.
    """
    query_embedding = embed_text(query)
    
    logger.info(f"Searching: '{query[:50]}...' (org: {organization_id})")

    filters = [
        KnowledgeDocument.organization_id == organization_id,
        KnowledgeDocument.status == KnowledgeDocumentStatus.ACTIVE.value,
        KnowledgeDocument.ingestion_status == KnowledgeIngestionStatus.INGESTED.value,
    ]

    if document_type:
        filters.append(KnowledgeDocument.document_type == document_type)

    # pgvector cosine distance
    distance_expression = KnowledgeChunk.embedding.cosine_distance(query_embedding)

    rows = db.execute(
        select(
            KnowledgeChunk,
            KnowledgeDocument,
            distance_expression.label("distance"),
        )
        .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
        .where(and_(*filters))
        .order_by(distance_expression)
        .limit(limit)
    ).all()

    results = []
    for chunk, document, distance in rows:
        score = max(0.0, 1.0 - float(distance))
        results.append((chunk, document, score))

    logger.info(f"Search returned {len(results)} results")
    return results


def count_documents(
    db: Session,
    organization_id: UUID,
    status_filter: str | None = None,
    document_type: str | None = None,
) -> int:
    filters = [KnowledgeDocument.organization_id == organization_id]

    if status_filter:
        filters.append(KnowledgeDocument.status == status_filter)

    if document_type:
        filters.append(KnowledgeDocument.document_type == document_type)

    return db.scalar(select(func.count(KnowledgeDocument.id)).where(and_(*filters))) or 0