"""Unit tests for grounded answering, citation verification, prompt sandboxing, and abstention."""

from typing import Any
import uuid
from unittest.mock import AsyncMock
import pytest

from app.providers.base import LLMProvider, MockLLMProvider
from app.services.answering import (
    ABSTENTION_MESSAGE,
    build_evidence_prompt,
    generate_grounded_answer,
    parse_and_validate_citations,
)
from app.services.retrieval import RetrievedChunk


def _make_retrieved_chunk(
    chunk_id: uuid.UUID | None = None,
    doc_id: uuid.UUID | None = None,
    doc_title: str = "Leave Policy",
    doc_filename: str = "leave_policy.pdf",
    content: str = "Full-time employees accrue 20 days of PTO per calendar year.",
    page: int = 2,
    section: str = "Annual PTO",
    similarity: float = 0.88,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=doc_id or uuid.uuid4(),
        document_title=doc_title,
        document_filename=doc_filename,
        chunk_index=0,
        page_number=page,
        section_title=section,
        content=content,
        similarity_score=similarity,
    )


def test_prompt_construction_and_evidence_boundaries():
    """Validates clear delimiter fences and metadata in LLM evidence context."""
    chunk1 = _make_retrieved_chunk(
        content="Remote workers receive $500 home office equipment stipend.",
        doc_title="Remote Work Guidelines",
        doc_filename="remote.pdf",
        page=1,
        section="Stipend",
    )
    prompt = build_evidence_prompt("What is the equipment stipend?", [chunk1])

    # Assert clear delimiter fences
    assert "--- EVIDENCE EXCERPTS BEGIN ---" in prompt
    assert "--- EVIDENCE EXCERPTS END ---" in prompt
    assert f"[Chunk {chunk1.chunk_id}]" in prompt
    assert "Remote Work Guidelines" in prompt
    assert "remote.pdf" in prompt
    assert "Employee Question: What is the equipment stipend?" in prompt


def test_citation_parsing_and_valid_resolution():
    """Extracts valid chunk IDs from LLM output and resolves provenance from DB metadata."""
    chunk = _make_retrieved_chunk(
        doc_title="IT Security Policy",
        doc_filename="it_security.pdf",
        content="All passwords must be at least 14 characters.",
        page=3,
        section="Passwords",
    )

    llm_output = f"Corporate passwords require at least 14 characters. [Chunk {chunk.chunk_id}]"
    raw_answer, citations = parse_and_validate_citations(llm_output, [chunk])

    assert len(citations) == 1
    c = citations[0]
    assert c.chunk_id == chunk.chunk_id
    assert c.document_title == "IT Security Policy"
    assert c.document_filename == "it_security.pdf"
    assert c.page_number == 3
    assert c.section_title == "Passwords"
    assert "14 characters" in c.snippet


def test_rejection_of_fabricated_or_unretrieved_citations():
    """Rejects fabricated or hallucinated chunk IDs that do not exist in the retrieved set."""
    chunk = _make_retrieved_chunk()
    fabricated_id = uuid.uuid4()

    llm_output = f"Employees receive unlimited snacks. [Chunk {fabricated_id}]"
    _, citations = parse_and_validate_citations(llm_output, [chunk])

    # Fabricated ID must be discarded
    assert len(citations) == 0


async def test_abstention_on_empty_retrieved_chunks():
    """When retrieval finds no evidence above threshold, abstains immediately with 0 LLM calls."""
    mock_llm = AsyncMock(spec=LLMProvider)

    result = await generate_grounded_answer(
        question="What is the pet insurance policy?",
        retrieved_chunks=[],
        llm_provider=mock_llm,
    )

    assert result.answer == ABSTENTION_MESSAGE
    assert result.is_unanswerable is True
    assert len(result.citations) == 0
    # LLM generate MUST NOT be called when retrieval yields no evidence
    mock_llm.generate.assert_not_called()


async def test_abstention_when_model_cannot_answer():
    """When the LLM explicitly indicates insufficient evidence, returns canonical abstention message."""
    chunk = _make_retrieved_chunk()

    class AbstainingLLM(LLMProvider):
        async def generate(self, prompt: str, **kwargs: Any) -> str:
            return "I don't know based on the provided documents."

    result = await generate_grounded_answer(
        question="Can employees bring dogs to work?",
        retrieved_chunks=[chunk],
        llm_provider=AbstainingLLM(),
    )

    assert result.answer == ABSTENTION_MESSAGE
    assert result.is_unanswerable is True
    assert len(result.citations) == 0


async def test_abstention_when_all_citations_are_invalid():
    """If the LLM provides an answer but only cites invalid/fabricated chunk IDs, abstain."""
    chunk = _make_retrieved_chunk()
    fake_chunk_id = uuid.uuid4()

    class HallucinatingCitationLLM(LLMProvider):
        async def generate(self, prompt: str, **kwargs: Any) -> str:
            return f"The bonus is 20 percent. [Chunk {fake_chunk_id}]"

    result = await generate_grounded_answer(
        question="What is the bonus percentage?",
        retrieved_chunks=[chunk],
        llm_provider=HallucinatingCitationLLM(),
    )

    # Must abstain because provenance cannot be verified against retrieved sources
    assert result.answer == ABSTENTION_MESSAGE
    assert result.is_unanswerable is True
    assert len(result.citations) == 0


async def test_successful_grounded_answer_with_real_citations():
    """Successfully answers with evidence-grounded facts and verified citations."""
    chunk = _make_retrieved_chunk(
        content="Corporate account passwords must be at least 14 characters long and changed every 90 days.",
        page=2,
        section="Password Rotation",
    )

    mock_llm = MockLLMProvider()
    result = await generate_grounded_answer(
        question="What is the password requirement?",
        retrieved_chunks=[chunk],
        llm_provider=mock_llm,
    )

    assert result.is_unanswerable is False
    assert result.answer != ABSTENTION_MESSAGE
    assert len(result.citations) == 1
    assert result.citations[0].chunk_id == chunk.chunk_id
    assert result.citations[0].page_number == 2
    assert result.citations[0].section_title == "Password Rotation"
    assert result.confidence_score == chunk.similarity_score
    assert result.latency_ms >= 0
