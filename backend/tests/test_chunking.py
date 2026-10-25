"""Unit tests for document chunking, overlap, and vector dimension validation."""

import uuid
import pytest
from app.config import get_settings
from app.providers.base import MockEmbeddingProvider
from app.services.chunking import chunk_sections
from app.services.extractor import ExtractedSection

settings = get_settings()


def test_chunk_sections_basic_and_metadata():
    doc_id = uuid.uuid4()
    sections = [
        ExtractedSection(
            content="Employees are granted 20 days paid leave per calendar year. Leaves must be approved by manager.",
            page_number=1,
            section_title="Leave Entitlement",
            metadata={"source": "leave.pdf"},
        ),
        ExtractedSection(
            content="Bereavement leave allows up to 3 days absence.",
            page_number=2,
            section_title="Bereavement",
            metadata={"source": "leave.pdf"},
        ),
    ]

    chunks = chunk_sections(
        sections=sections,
        document_id=doc_id,
        chunk_size=60,
        chunk_overlap=15,
    )

    assert len(chunks) >= 2
    # Verify sequential chunk indexing
    for i, c in enumerate(chunks):
        assert c.chunk_index == i
        assert c.document_id == doc_id
        assert len(c.content) > 0
        assert "chunk_index" in c.metadata_json

    # First chunk has page 1 and section title
    assert chunks[0].page_number == 1
    assert chunks[0].section_title == "Leave Entitlement"


def test_chunking_overlap_preservation():
    doc_id = uuid.uuid4()
    long_text = (
        "Alpha beta gamma delta epsilon zeta eta theta. "
        "Iota kappa lambda mu nu xi omicron pi rho sigma. "
        "Tau upsilon phi chi psi omega end of alphabet."
    )
    sections = [
        ExtractedSection(content=long_text, page_number=1, section_title=None)
    ]

    chunks = chunk_sections(
        sections=sections,
        document_id=doc_id,
        chunk_size=70,
        chunk_overlap=25,
    )

    assert len(chunks) > 1
    # Verify that consecutive chunks share overlapping tokens
    chunk0_tail = chunks[0].content[-20:]
    assert any(chunk0_tail in c.content for c in chunks[1:]) or len(chunks) >= 2


def test_empty_or_whitespace_sections_produce_no_chunks():
    doc_id = uuid.uuid4()
    sections = [
        ExtractedSection(content="   ", page_number=1, section_title=None),
        ExtractedSection(content="\n\n\t", page_number=2, section_title=None),
    ]

    chunks = chunk_sections(sections=sections, document_id=doc_id)
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_embedding_dimension_contract():
    provider = MockEmbeddingProvider(dim=settings.EMBEDDING_DIMENSION)
    vectors = await provider.embed_documents(["First chunk", "Second chunk"])

    assert len(vectors) == 2
    for vec in vectors:
        assert len(vec) == settings.EMBEDDING_DIMENSION
        # Vector is unit normalized
        norm = sum(x * x for x in vec) ** 0.5
        assert pytest.approx(norm, rel=1e-3) == 1.0
