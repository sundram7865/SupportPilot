from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.common.enums import KnowledgeDocumentStatus, KnowledgeDocumentType


class CreateKnowledgeDocumentRequest(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    document_type: KnowledgeDocumentType = KnowledgeDocumentType.OTHER
    status: KnowledgeDocumentStatus = KnowledgeDocumentStatus.DRAFT
    content: str = Field(min_length=10)
    source_url: str | None = Field(default=None, max_length=1000)
    metadata_json: dict | None = None


class UpdateKnowledgeDocumentRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    document_type: KnowledgeDocumentType | None = None
    status: KnowledgeDocumentStatus | None = None
    content: str | None = Field(default=None, min_length=10)
    source_url: str | None = Field(default=None, max_length=1000)
    metadata_json: dict | None = None


class KnowledgeDocumentResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    document_type: str
    status: str
    content: str
    source_url: str | None
    version: int
    ingestion_status: str
    ingestion_error: str | None
    chunk_count: int
    metadata_json: dict | None
    created_by_user_id: str | None
    updated_by_user_id: str | None
    ingested_at: datetime | None
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentListItemResponse(BaseModel):
    id: str
    title: str
    document_type: str
    status: str
    version: int
    ingestion_status: str
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class KnowledgeDocumentListResponse(BaseModel):
    items: list[KnowledgeDocumentListItemResponse]
    total: int
    limit: int
    offset: int


class IngestKnowledgeDocumentResponse(BaseModel):
    document_id: str
    ingestion_status: str
    chunk_count: int


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)
    document_type: KnowledgeDocumentType | None = None
    limit: int = Field(default=5, ge=1, le=20)


class TicketKnowledgeSearchRequest(BaseModel):
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    document_type: str
    chunk_index: int
    content: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: list[KnowledgeSearchResult]


class KnowledgeChunkResponse(BaseModel):
    id: str
    document_id: str
    chunk_index: int
    content: str
    token_count: int
    created_at: datetime