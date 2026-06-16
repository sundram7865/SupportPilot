from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.common.enums import KnowledgeDocumentStatus, KnowledgeIngestionStatus
from app.modules.knowledge.chunker import estimate_token_count, split_text_into_chunks
from app.modules.knowledge.embeddings import embed_text
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument


def ingest_document(
    db: Session,
    document: KnowledgeDocument,
) -> KnowledgeDocument:
    try:
        db.query(KnowledgeChunk).filter(
            KnowledgeChunk.document_id == document.id
        ).delete()

        raw_chunks = split_text_into_chunks(document.content)

        for index, chunk_text in enumerate(raw_chunks):
            chunk = KnowledgeChunk(
                organization_id=document.organization_id,
                document_id=document.id,
                chunk_index=index,
                content=chunk_text,
                token_count=estimate_token_count(chunk_text),
                embedding=embed_text(chunk_text),
                metadata_json={
                    "document_version": document.version,
                    "document_type": document.document_type,
                },
            )

            db.add(chunk)

        document.chunk_count = len(raw_chunks)
        document.ingestion_status = KnowledgeIngestionStatus.INGESTED.value
        document.ingestion_error = None
        document.ingested_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(document)

        return document

    except Exception as exc:
        document.ingestion_status = KnowledgeIngestionStatus.FAILED.value
        document.ingestion_error = str(exc)

        db.commit()
        db.refresh(document)

        raise


def search_knowledge_chunks(
    db: Session,
    organization_id: UUID,
    query: str,
    limit: int = 5,
    document_type: str | None = None,
) -> list[tuple[KnowledgeChunk, KnowledgeDocument, float]]:
    query_embedding = embed_text(query)

    filters = [
        KnowledgeDocument.organization_id == organization_id,
        KnowledgeDocument.status == KnowledgeDocumentStatus.ACTIVE.value,
        KnowledgeDocument.ingestion_status == KnowledgeIngestionStatus.INGESTED.value,
    ]

    if document_type:
        filters.append(KnowledgeDocument.document_type == document_type)

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

    results: list[tuple[KnowledgeChunk, KnowledgeDocument, float]] = []

    for chunk, document, distance in rows:
        score = max(0.0, 1.0 - float(distance))
        results.append((chunk, document, score))

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