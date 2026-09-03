from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session, selectinload

from app.common.cloudinary_config import CloudinaryConfig
from app.common.cloudinary_service import CloudinaryService
from app.common.enums import KnowledgeIngestionStatus
from app.db.session import get_db
from app.modules.auth.dependencies import (
    get_current_organization,
    get_or_create_current_user,
    require_permission,
)
from app.modules.auth.permissions import Permission
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument
from app.modules.knowledge.schemas import (
    CreateKnowledgeDocumentRequest,
    IngestKnowledgeDocumentResponse,
    KnowledgeChunkResponse,
    KnowledgeDocumentListItemResponse,
    KnowledgeDocumentListResponse,
    KnowledgeDocumentResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    TicketKnowledgeSearchRequest,
    UpdateKnowledgeDocumentRequest,
)
from app.modules.knowledge.service import (
    KnowledgeService,
    count_documents,
    ingest_document,
    search_knowledge_chunks,
)
from app.modules.organizations.models import Organization
from app.modules.tickets.models import Ticket
from app.modules.users.models import User


cloudinary_config = CloudinaryConfig.from_env()
cloudinary_service = CloudinaryService(cloudinary_config)
knowledge_service = KnowledgeService(cloudinary_service)

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


def get_document_or_404(
    db: Session,
    organization_id: UUID,
    document_id: UUID,
) -> KnowledgeDocument:
    """Fetch a knowledge document or raise 404"""
    document = db.scalar(
        select(KnowledgeDocument)
        .options(selectinload(KnowledgeDocument.chunks))
        .where(KnowledgeDocument.id == document_id)
        .where(KnowledgeDocument.organization_id == organization_id)
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge document not found.",
        )

    return document


def to_document_response(document: KnowledgeDocument) -> KnowledgeDocumentResponse:
    """Convert KnowledgeDocument model to response schema"""
    return KnowledgeDocumentResponse(
        id=str(document.id),
        organization_id=str(document.organization_id),
        title=document.title,
        document_type=document.document_type,
        status=document.status,
        content=document.content,
        source_url=document.source_url,
        version=document.version,
        ingestion_status=document.ingestion_status,
        ingestion_error=document.ingestion_error,
        chunk_count=document.chunk_count,
        metadata_json=document.metadata_json,
        cloudinary_public_id=document.cloudinary_public_id if hasattr(document, 'cloudinary_public_id') else None,
        cloudinary_url=document.cloudinary_url if hasattr(document, 'cloudinary_url') else None,
        file_name=document.file_name if hasattr(document, 'file_name') else None,
        file_size=document.file_size if hasattr(document, 'file_size') else None,
        file_type=document.file_type if hasattr(document, 'file_type') else None,
        created_by_user_id=(
            str(document.created_by_user_id) if document.created_by_user_id else None
        ),
        updated_by_user_id=(
            str(document.updated_by_user_id) if document.updated_by_user_id else None
        ),
        ingested_at=document.ingested_at,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )
    


def to_document_list_item(
    document: KnowledgeDocument,
) -> KnowledgeDocumentListItemResponse:
    """Convert KnowledgeDocument model to list item response schema"""
    return KnowledgeDocumentListItemResponse(
        id=str(document.id),
        title=document.title,
        document_type=document.document_type,
        status=document.status,
        version=document.version,
        ingestion_status=document.ingestion_status,
        chunk_count=document.chunk_count,
        file_name=document.file_name if hasattr(document, 'file_name') else None,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def to_chunk_response(chunk: KnowledgeChunk) -> KnowledgeChunkResponse:
    """Convert KnowledgeChunk model to response schema"""
    return KnowledgeChunkResponse(
        id=str(chunk.id),
        document_id=str(chunk.document_id),
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        token_count=chunk.token_count,
        created_at=chunk.created_at,
    )


# ============================================================================
# Document CRUD Routes
# ============================================================================

@router.post(
    "/documents",
    response_model=KnowledgeDocumentResponse,
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_CREATE))],
)
def create_document(
    payload: CreateKnowledgeDocumentRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    """Create a new knowledge document with text content"""
    existing_document = db.scalar(
        select(KnowledgeDocument)
        .where(KnowledgeDocument.organization_id == organization.id)
        .where(KnowledgeDocument.title == payload.title)
    )

    if existing_document:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A knowledge document with this title already exists.",
        )

    document = KnowledgeDocument(
        organization_id=organization.id,
        title=payload.title,
        document_type=payload.document_type.value,
        status=payload.status.value,
        content=payload.content,
        source_url=payload.source_url,
        metadata_json=payload.metadata_json,
        created_by_user_id=current_user.id,
        updated_by_user_id=current_user.id,
        ingestion_status=KnowledgeIngestionStatus.PENDING.value,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return to_document_response(document)


@router.post(
    "/documents/upload",
    response_model=KnowledgeDocumentResponse,
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_CREATE))],
)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    title: str | None = Form(None, description="Document title (uses filename if not provided)"),
    document_type: str = Form("OTHER", description="Document type"),
    doc_status: str = Form("DRAFT", description="Document status"),  # Renamed from 'status'
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a document file to Cloudinary and create a knowledge document.
    Supports: PDF, DOCX, TXT, MD, CSV, JSON, XML
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Upload request: file={file.filename}, title={title}, type={document_type}")
    
    # Check for duplicate title if provided
    if title:
        existing_document = db.scalar(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.organization_id == organization.id)
            .where(KnowledgeDocument.title == title)
        )
        if existing_document:
            raise HTTPException(
                status_code=409,  # Use integer instead of status.HTTP_409_CONFLICT
                detail="A knowledge document with this title already exists.",
            )

    try:
        document = await knowledge_service.create_document_with_file(
            db=db,
            file=file,
            organization_id=organization.id,
            user_id=current_user.id,
            title=title,
            document_type=document_type,
            status=doc_status,  # Use the renamed parameter
        )
        
        logger.info(f"Document created: {document.id}, ingestion_status: {document.ingestion_status}")
        
        return to_document_response(document)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload document: {str(e)}",
        )

@router.get(
    "/documents",
    response_model=KnowledgeDocumentListResponse,
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
)
def list_documents(
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
    status_filter: str | None = Query(default=None, alias="status"),
    document_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all knowledge documents with optional filtering"""
    filters = [KnowledgeDocument.organization_id == organization.id]

    if status_filter:
        filters.append(KnowledgeDocument.status == status_filter)

    if document_type:
        filters.append(KnowledgeDocument.document_type == document_type)

    total = count_documents(
        db=db,
        organization_id=organization.id,
        status_filter=status_filter,
        document_type=document_type,
    )

    documents = db.scalars(
        select(KnowledgeDocument)
        .where(and_(*filters))
        .order_by(desc(KnowledgeDocument.updated_at))
        .limit(limit)
        .offset(offset)
    ).all()

    return KnowledgeDocumentListResponse(
        items=[to_document_list_item(document) for document in documents],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/documents/{document_id}",
    response_model=KnowledgeDocumentResponse,
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
)
def get_document(
    document_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """Get a specific knowledge document by ID"""
    document = get_document_or_404(db, organization.id, document_id)
    return to_document_response(document)


@router.patch(
    "/documents/{document_id}",
    response_model=KnowledgeDocumentResponse,
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_UPDATE))],
)
def update_document(
    document_id: UUID,
    payload: UpdateKnowledgeDocumentRequest,
    organization: Organization = Depends(get_current_organization),
    current_user: User = Depends(get_or_create_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing knowledge document"""
    document = get_document_or_404(db, organization.id, document_id)

    content_changed = False

    if payload.title is not None:
        # Check for duplicate title
        existing = db.scalar(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.organization_id == organization.id)
            .where(KnowledgeDocument.title == payload.title)
            .where(KnowledgeDocument.id != document_id)
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A knowledge document with this title already exists.",
            )
        document.title = payload.title

    if payload.document_type is not None:
        document.document_type = payload.document_type.value

    if payload.status is not None:
        document.status = payload.status.value

    if payload.content is not None:
        document.content = payload.content
        document.version += 1
        document.ingestion_status = KnowledgeIngestionStatus.PENDING.value
        document.ingestion_error = None
        content_changed = True

    if payload.source_url is not None:
        document.source_url = payload.source_url

    if payload.metadata_json is not None:
        document.metadata_json = payload.metadata_json

    document.updated_by_user_id = current_user.id

    if content_changed:
        document.chunk_count = 0

    db.commit()
    db.refresh(document)

    return to_document_response(document)


@router.put(
    "/documents/{document_id}/file",
    response_model=KnowledgeDocumentResponse,
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_UPDATE))],
)
async def update_document_file(
    document_id: UUID,
    file: UploadFile = File(..., description="New file to upload"),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Replace the file associated with an existing document.
    Old file will be deleted from Cloudinary.
    """
    document = get_document_or_404(db, organization.id, document_id)
    
    try:
        document = await knowledge_service.update_document_file(
            db=db,
            document=document,
            file=file,
        )
        return to_document_response(document)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update document file: {str(e)}",
        )


@router.delete(
    "/documents/{document_id}",
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_DELETE))],
)
async def delete_document(
    document_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Delete a knowledge document and its associated file from Cloudinary
    """
    document = get_document_or_404(db, organization.id, document_id)

    try:
        # Use service to handle both DB and Cloudinary deletion
        await knowledge_service.delete_document_with_cloudinary(db, document)
    except Exception as e:
        # Fallback to DB-only deletion if Cloudinary fails
        db.delete(document)
        db.commit()

    return {
        "success": True,
        "message": "Knowledge document deleted successfully.",
    }


@router.get(
    "/documents/{document_id}/download",
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
)
async def get_document_download_url(
    document_id: UUID,
    expiration: int = Query(
        default=3600,
        ge=60,
        le=86400,
        description="URL expiration time in seconds (1 min to 24 hours)"
    ),
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Generate a signed download URL for the document file.
    Only works for documents that have files uploaded via Cloudinary.
    """
    document = get_document_or_404(db, organization.id, document_id)

    if not document.cloudinary_public_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No file associated with this document. Only uploaded documents have downloadable files.",
        )

    try:
        download_url = await cloudinary_service.get_document_url(
            public_id=document.cloudinary_public_id,
            expiration_seconds=expiration,
        )

        return {
            "download_url": download_url,
            "expires_in": expiration,
            "file_name": document.file_name,
            "file_size": document.file_size,
            "file_type": document.file_type,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}",
        )


# ============================================================================
# Ingestion Routes
# ============================================================================

@router.post(
    "/documents/{document_id}/ingest",
    response_model=IngestKnowledgeDocumentResponse,
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_INGEST))],
)
async def ingest_document_route(
    document_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Trigger ingestion for a knowledge document.
    This processes the document content into searchable chunks with embeddings.
    """
    document = get_document_or_404(db, organization.id, document_id)

    try:
        document = await knowledge_service.ingest_document_async(db, document)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(e)}",
        )

    return IngestKnowledgeDocumentResponse(
        document_id=str(document.id),
        ingestion_status=document.ingestion_status,
        chunk_count=document.chunk_count,
    )


@router.get(
    "/documents/{document_id}/chunks",
    response_model=list[KnowledgeChunkResponse],
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
)
def list_document_chunks(
    document_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """List all chunks for a specific document"""
    document = get_document_or_404(db, organization.id, document_id)

    if not document.chunks:
        return []

    return [to_chunk_response(chunk) for chunk in document.chunks]


# ============================================================================
# Search Routes
# ============================================================================

@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
)
def search_knowledge(
    payload: KnowledgeSearchRequest,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Search knowledge base using semantic similarity.
    Returns the most relevant chunks with similarity scores.
    """
    if not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty.",
        )

    try:
        results = search_knowledge_chunks(
            db=db,
            organization_id=organization.id,
            query=payload.query,
            limit=payload.limit,
            document_type=payload.document_type.value if payload.document_type else None,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )

    if not results:
        return KnowledgeSearchResponse(
            query=payload.query,
            results=[],
        )

    return KnowledgeSearchResponse(
        query=payload.query,
        results=[
            KnowledgeSearchResult(
                chunk_id=str(chunk.id),
                document_id=str(document.id),
                document_title=document.title,
                document_type=document.document_type,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=round(score, 4),  # Round score for cleaner output
            )
            for chunk, document, score in results
        ],
    )


@router.post(
    "/tickets/{ticket_id}/search",
    response_model=KnowledgeSearchResponse,
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_READ))],
)
def search_knowledge_for_ticket(
    ticket_id: UUID,
    payload: TicketKnowledgeSearchRequest,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    """
    Search knowledge base using ticket context.
    Automatically constructs a search query from ticket details.
    """
    ticket = db.scalar(
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .where(Ticket.organization_id == organization.id)
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found.",
        )

    # Construct comprehensive search query from ticket
    query_parts = []
    
    if ticket.subject:
        query_parts.append(f"Subject: {ticket.subject}")
    
    if ticket.description:
        # Truncate very long descriptions to avoid embedding issues
        description = ticket.description[:2000] if len(ticket.description) > 2000 else ticket.description
        query_parts.append(f"Description: {description}")
    
    if ticket.category:
        query_parts.append(f"Category: {ticket.category}")
    
    if ticket.external_order_id:
        query_parts.append(f"Order ID: {ticket.external_order_id}")
    
    if ticket.customer_email:
        query_parts.append(f"Customer email: {ticket.customer_email}")

    query = "\n".join(query_parts).strip()

    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket has no searchable content.",
        )

    try:
        results = search_knowledge_chunks(
            db=db,
            organization_id=organization.id,
            query=query,
            limit=payload.limit,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ticket knowledge search failed: {str(e)}",
        )

    if not results:
        return KnowledgeSearchResponse(
            query=query,
            results=[],
        )

    return KnowledgeSearchResponse(
        query=query,
        results=[
            KnowledgeSearchResult(
                chunk_id=str(chunk.id),
                document_id=str(document.id),
                document_title=document.title,
                document_type=document.document_type,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=round(score, 4),
            )
            for chunk, document, score in results
        ],
    )