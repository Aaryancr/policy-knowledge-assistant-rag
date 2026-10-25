"""Pydantic schemas for RAG query requests, grounded answers, citations, and chat logs."""

from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="The employee's policy or knowledge question.",
        examples=["What is the company policy on remote work?"],
    )
    top_k: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="Optional override for number of chunks to retrieve.",
    )
    min_similarity: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional override for cosine similarity threshold.",
    )


class CitationResponse(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    document_filename: str
    page_number: int | None
    section_title: str | None
    snippet: str


class QueryResponse(BaseModel):
    question: str
    answer: str
    is_unanswerable: bool
    citations: list[CitationResponse]
    confidence_score: float | None
    latency_ms: int
    chat_log_id: uuid.UUID


class ChatLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    query: str
    retrieved_chunk_ids: list[str]
    answer: str
    is_unanswerable: bool
    confidence_score: float | None
    latency_ms: int | None
    created_at: datetime
