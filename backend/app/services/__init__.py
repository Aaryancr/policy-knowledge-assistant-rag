"""Services package exports."""

from app.services.extractor import ExtractedSection, extract_text, DocumentExtractionError
from app.services.chunking import ProcessedChunk, chunk_sections
from app.services.queue import enqueue_ingestion_job, QueueError
from app.services.retrieval import RetrievedChunk, retrieve_chunks
from app.services.answering import (
    ABSTENTION_MESSAGE,
    Citation,
    AnswerResult,
    build_evidence_prompt,
    parse_and_validate_citations,
    generate_grounded_answer,
)

__all__ = [
    "ExtractedSection",
    "extract_text",
    "DocumentExtractionError",
    "ProcessedChunk",
    "chunk_sections",
    "enqueue_ingestion_job",
    "QueueError",
    "RetrievedChunk",
    "retrieve_chunks",
    "ABSTENTION_MESSAGE",
    "Citation",
    "AnswerResult",
    "build_evidence_prompt",
    "parse_and_validate_citations",
    "generate_grounded_answer",
]
