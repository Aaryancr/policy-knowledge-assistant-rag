"""Pydantic schemas for document upload, metadata retrieval, chunks, and ingestion jobs."""

from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    job_id: uuid.UUID | None
    status: str
    title: str
    filename: str
    file_size_bytes: int
    checksum_sha256: str | None
    is_duplicate: bool = False
    message: str | None = None
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    filename: str
    file_size_bytes: int
    content_type: str
    status: str
    total_chunks: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int


class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    content: str
    page_number: int | None
    section_title: str | None
    metadata_json: dict[str, Any]
    has_embedding: bool = False


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    status: str
    retry_count: int
    max_retries: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
