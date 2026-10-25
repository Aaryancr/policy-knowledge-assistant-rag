"""Retrieval service for dense semantic vector search with pgvector."""

from dataclasses import dataclass, field
import math
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.providers.base import EmbeddingProvider, get_embedding_provider

settings = get_settings()


@dataclass
class RetrievedChunk:
    """Represents a passage retrieved from vector search with similarity and provenance metadata."""
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    document_filename: str
    chunk_index: int
    page_number: int | None
    section_title: str | None
    content: str
    similarity_score: float
    metadata_json: dict[str, Any] = field(default_factory=dict)


def compute_cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Computes cosine similarity between two float vectors in [-1.0, 1.0]."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


async def retrieve_chunks(
    question: str,
    db: AsyncSession,
    top_k: int | None = None,
    min_similarity: float | None = None,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[RetrievedChunk]:
    """Retrieves the top-k most relevant chunks for a question matching the similarity threshold.
    
    Excludes chunks from non-completed documents. Uses PostgreSQL pgvector cosine distance
    when running against PostgreSQL, and an in-memory cosine fallback when running unit tests
    against in-memory SQLite.
    """
    clean_question = question.strip()
    if not clean_question:
        raise ValueError("Search question cannot be empty or solely whitespace.")

    if len(clean_question) > settings.MAX_QUESTION_LENGTH:
        raise ValueError(
            f"Question exceeds maximum length of {settings.MAX_QUESTION_LENGTH} characters."
        )

    k = top_k if (top_k is not None and top_k > 0) else settings.TOP_K_RETRIEVAL
    threshold = min_similarity if min_similarity is not None else settings.MIN_SIMILARITY_THRESHOLD

    # 1. Embed query vector and validate dimensions
    provider = embedding_provider or get_embedding_provider()
    query_vec = await provider.embed_query(clean_question)

    expected_dim = settings.EMBEDDING_DIMENSION
    if len(query_vec) != expected_dim:
        raise ValueError(
            f"Query embedding dimension mismatch: got {len(query_vec)}, expected {expected_dim}"
        )

    # 2. Database dialect detection: PostgreSQL pgvector vs SQLite unit testing
    is_sqlite = False
    try:
        bind = db.get_bind()
        if bind and bind.dialect.name == "sqlite":
            is_sqlite = True
    except Exception:
        pass

    retrieved: list[RetrievedChunk] = []

    if not is_sqlite:
        # Native PostgreSQL execution with pgvector <=> cosine distance operator
        cosine_dist = Chunk.embedding.cosine_distance(query_vec)
        stmt = (
            select(
                Chunk,
                Document.title.label("document_title"),
                Document.filename.label("document_filename"),
                cosine_dist.label("distance"),
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.status == "completed")
            .where(Chunk.embedding.is_not(None))
            .where(cosine_dist <= (1.0 - threshold))
            .order_by(cosine_dist.asc())
            .limit(k)
        )
        rows = (await db.execute(stmt)).all()

        for chunk_obj, doc_title, doc_filename, dist in rows:
            # Cosine distance d in [0, 2]; cosine similarity s = 1.0 - d
            sim = 1.0 - float(dist) if dist is not None else 0.0
            retrieved.append(
                RetrievedChunk(
                    chunk_id=chunk_obj.id,
                    document_id=chunk_obj.document_id,
                    document_title=doc_title,
                    document_filename=doc_filename,
                    chunk_index=chunk_obj.chunk_index,
                    page_number=chunk_obj.page_number,
                    section_title=chunk_obj.section_title,
                    content=chunk_obj.content,
                    similarity_score=round(sim, 4),
                    metadata_json=chunk_obj.metadata_json or {},
                )
            )
    else:
        # In-memory cosine calculation fallback for SQLite unit tests
        stmt = (
            select(
                Chunk,
                Document.title.label("document_title"),
                Document.filename.label("document_filename"),
            )
            .join(Document, Chunk.document_id == Document.id)
            .where(Document.status == "completed")
            .where(Chunk.embedding.is_not(None))
        )
        rows = (await db.execute(stmt)).all()

        candidates: list[RetrievedChunk] = []
        for chunk_obj, doc_title, doc_filename in rows:
            if not chunk_obj.embedding:
                continue
            sim = compute_cosine_similarity(query_vec, chunk_obj.embedding)
            if sim >= threshold:
                candidates.append(
                    RetrievedChunk(
                        chunk_id=chunk_obj.id,
                        document_id=chunk_obj.document_id,
                        document_title=doc_title,
                        document_filename=doc_filename,
                        chunk_index=chunk_obj.chunk_index,
                        page_number=chunk_obj.page_number,
                        section_title=chunk_obj.section_title,
                        content=chunk_obj.content,
                        similarity_score=round(sim, 4),
                        metadata_json=chunk_obj.metadata_json or {},
                    )
                )

        candidates.sort(key=lambda x: x.similarity_score, reverse=True)
        retrieved = candidates[:k]

    return retrieved
