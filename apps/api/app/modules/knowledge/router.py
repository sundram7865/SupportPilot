from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session, selectinload

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
    count_documents,
    ingest_document,
    search_knowledge_chunks,
)
from app.modules.organizations.models import Organization
from app.modules.tickets.models import Ticket
from app.modules.users.models import User

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


def get_document_or_404(
    db: Session,
    organization_id: UUID,
    document_id: UUID,
) -> KnowledgeDocument:
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
    return KnowledgeDocumentListItemResponse(
        id=str(document.id),
        title=document.title,
        document_type=document.document_type,
        status=document.status,
        version=document.version,
        ingestion_status=document.ingestion_status,
        chunk_count=document.chunk_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def to_chunk_response(chunk: KnowledgeChunk) -> KnowledgeChunkResponse:
    return KnowledgeChunkResponse(
        id=str(chunk.id),
        document_id=str(chunk.document_id),
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        token_count=chunk.token_count,
        created_at=chunk.created_at,
    )


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
    document = get_document_or_404(db, organization.id, document_id)

    content_changed = False

    if payload.title is not None:
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


@router.delete(
    "/documents/{document_id}",
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_DELETE))],
)
def delete_document(
    document_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    document = get_document_or_404(db, organization.id, document_id)

    db.delete(document)
    db.commit()

    return {
        "success": True,
        "message": "Knowledge document deleted successfully.",
    }


@router.post(
    "/documents/{document_id}/ingest",
    response_model=IngestKnowledgeDocumentResponse,
    dependencies=[Depends(require_permission(Permission.KNOWLEDGE_INGEST))],
)
def ingest_document_route(
    document_id: UUID,
    organization: Organization = Depends(get_current_organization),
    db: Session = Depends(get_db),
):
    document = get_document_or_404(db, organization.id, document_id)

    document = ingest_document(db, document)

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
    document = get_document_or_404(db, organization.id, document_id)

    return [to_chunk_response(chunk) for chunk in document.chunks]


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
    results = search_knowledge_chunks(
        db=db,
        organization_id=organization.id,
        query=payload.query,
        limit=payload.limit,
        document_type=payload.document_type.value if payload.document_type else None,
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
                score=score,
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

    query = f"""
Subject: {ticket.subject}
Description: {ticket.description}
Category: {ticket.category}
Order ID: {ticket.external_order_id or ""}
Customer email: {ticket.customer_email}
""".strip()

    results = search_knowledge_chunks(
        db=db,
        organization_id=organization.id,
        query=query,
        limit=payload.limit,
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
                score=score,
            )
            for chunk, document, score in results
        ],
    )