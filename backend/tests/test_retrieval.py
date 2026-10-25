"""Unit tests for the vector retrieval pipeline and pgvector similarity search."""

import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.user import User
from app.providers.base import EmbeddingProvider, MockEmbeddingProvider
from app.services.retrieval import compute_cosine_similarity, retrieve_chunks

settings = get_settings()


class BadDimensionEmbeddingProvider(EmbeddingProvider):
    """Provider returning vectors with incorrect dimensions to test validation."""

    @property
    def dimension(self) -> int:
        return 768

    async def embed_query(self, text: str) -> list[float]:
        return [0.1] * 768

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 768 for _ in texts]


def test_compute_cosine_similarity_edge_cases():
    """Validates vector cosine similarity calculation for known geometric relationships."""
    # 1. Identical normalized vectors -> similarity == 1.0
    v1 = [1.0, 0.0, 0.0]
    assert pytest.approx(compute_cosine_similarity(v1, v1), rel=1e-5) == 1.0

    # 2. Orthogonal vectors -> similarity == 0.0
    v2 = [0.0, 1.0, 0.0]
    assert pytest.approx(compute_cosine_similarity(v1, v2), abs=1e-5) == 0.0

    # 3. Opposite vectors -> similarity == -1.0
    v3 = [-1.0, 0.0, 0.0]
    assert pytest.approx(compute_cosine_similarity(v1, v3), rel=1e-5) == -1.0

    # 4. Zero vector handling -> returns 0.0 without ZeroDivisionError
    v_zero = [0.0, 0.0, 0.0]
    assert compute_cosine_similarity(v1, v_zero) == 0.0

    # 5. Dimension mismatch or empty input -> returns 0.0
    assert compute_cosine_similarity([1.0, 2.0], [1.0]) == 0.0
    assert compute_cosine_similarity([], []) == 0.0


async def test_question_validation_empty_and_whitespace(db_session: AsyncSession):
    """Empty or solely whitespace questions must be rejected before vector embedding."""
    with pytest.raises(ValueError, match="cannot be empty"):
        await retrieve_chunks("", db=db_session)

    with pytest.raises(ValueError, match="cannot be empty"):
        await retrieve_chunks("    \n\t  ", db=db_session)


async def test_question_validation_length_limit(db_session: AsyncSession):
    """Questions exceeding configurable maximum length must be rejected with ValueError."""
    oversized = "a" * (settings.MAX_QUESTION_LENGTH + 1)
    with pytest.raises(ValueError, match=f"maximum length of {settings.MAX_QUESTION_LENGTH}"):
        await retrieve_chunks(oversized, db=db_session)


async def test_question_embedding_dimension_validation(db_session: AsyncSession):
    """Vectors that do not match configured EMBEDDING_DIMENSION must be rejected."""
    bad_provider = BadDimensionEmbeddingProvider()
    with pytest.raises(ValueError, match="Query embedding dimension mismatch"):
        await retrieve_chunks("Valid test question", db=db_session, embedding_provider=bad_provider)


async def test_cosine_distance_ordering_and_top_k(
    db_session: AsyncSession,
    admin_user: User,
):
    """Retrieval returns chunks ordered by highest similarity score, capped at top-k."""
    provider = MockEmbeddingProvider()

    # Create completed test document
    doc = Document(
        id=uuid.uuid4(),
        uploaded_by_id=admin_user.id,
        filename="company_policy.pdf",
        title="Company Policy",
        content_type="application/pdf",
        file_path="/tmp/mock_company_policy.pdf",
        file_size_bytes=1024,
        checksum_sha256="mockchecksum001",
        status="completed",
    )
    db_session.add(doc)
    await db_session.flush()

    # Passages with differing relevance
    passages = [
        "Corporate password complexity requires at least 14 characters and rotation every 90 days.",
        "Password complexity rules mandate uppercase, lowercase, numbers and symbols.",
        "Remote work reimbursement equipment stipend provides $500 for home office setup.",
        "Annual paid time off gives full-time employees 20 days per calendar year.",
    ]
    vectors = await provider.embed_documents(passages)

    for idx, (text, vec) in enumerate(zip(passages, vectors)):
        chunk = Chunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            chunk_index=idx,
            content=text,
            embedding=vec,
            page_number=1,
            section_title=f"Section {idx}",
        )
        db_session.add(chunk)
    await db_session.commit()

    # Query specifically about passwords
    query = "What is the corporate password length requirement?"
    results = await retrieve_chunks(
        question=query,
        db=db_session,
        top_k=2,
        min_similarity=0.1,
        embedding_provider=provider,
    )

    assert len(results) == 2
    # The top retrieved chunk should be the password chunk
    assert "password" in results[0].content.lower()
    # Results must be in strictly descending order of similarity score
    assert results[0].similarity_score >= results[1].similarity_score
    # Provenance fields must be populated
    assert results[0].document_title == "Company Policy"
    assert results[0].document_filename == "company_policy.pdf"
    assert results[0].page_number == 1


async def test_similarity_threshold_filtering(
    db_session: AsyncSession,
    admin_user: User,
):
    """Chunks below minimum similarity threshold must be excluded from results."""
    provider = MockEmbeddingProvider()

    doc = Document(
        id=uuid.uuid4(),
        uploaded_by_id=admin_user.id,
        filename="security_guidelines.txt",
        title="Security Guidelines",
        content_type="text/plain",
        file_path="/tmp/mock_security.txt",
        file_size_bytes=512,
        checksum_sha256="mockchecksum002",
        status="completed",
    )
    db_session.add(doc)
    await db_session.flush()

    vec = await provider.embed_query("Corporate password requirements 14 characters")
    chunk = Chunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        chunk_index=0,
        content="Corporate password requirements 14 characters",
        embedding=vec,
    )
    db_session.add(chunk)
    await db_session.commit()

    # Query with high threshold that is not satisfied by unrelated query
    unrelated_query = "What is the company policy on parental and maternity leave benefits?"
    results = await retrieve_chunks(
        question=unrelated_query,
        db=db_session,
        top_k=5,
        min_similarity=0.5,
        embedding_provider=provider,
    )
    assert len(results) == 0


async def test_exclusion_of_unusable_or_unprocessed_document_chunks(
    db_session: AsyncSession,
    admin_user: User,
):
    """Chunks from documents with status != 'completed' (pending, failed, processing) must never be retrieved."""
    provider = MockEmbeddingProvider()
    shared_text = "Corporate password requirements mandate at least 14 characters."
    vec = await provider.embed_query(shared_text)

    # 1. Pending document
    pending_doc = Document(
        id=uuid.uuid4(),
        uploaded_by_id=admin_user.id,
        filename="pending_doc.pdf",
        title="Pending Doc",
        content_type="application/pdf",
        file_path="/tmp/mock_pending.pdf",
        file_size_bytes=512,
        checksum_sha256="mockchecksum_pending",
        status="pending",
    )
    # 2. Failed document
    failed_doc = Document(
        id=uuid.uuid4(),
        uploaded_by_id=admin_user.id,
        filename="failed_doc.pdf",
        title="Failed Doc",
        content_type="application/pdf",
        file_path="/tmp/mock_failed.pdf",
        file_size_bytes=512,
        checksum_sha256="mockchecksum_failed",
        status="failed",
    )
    # 3. Processing document
    proc_doc = Document(
        id=uuid.uuid4(),
        uploaded_by_id=admin_user.id,
        filename="proc_doc.pdf",
        title="Processing Doc",
        content_type="application/pdf",
        file_path="/tmp/mock_proc.pdf",
        file_size_bytes=512,
        checksum_sha256="mockchecksum_proc",
        status="processing",
    )
    # 4. Completed document
    completed_doc = Document(
        id=uuid.uuid4(),
        uploaded_by_id=admin_user.id,
        filename="completed_doc.pdf",
        title="Completed Doc",
        content_type="application/pdf",
        file_path="/tmp/mock_completed.pdf",
        file_size_bytes=512,
        checksum_sha256="mockchecksum_completed",
        status="completed",
    )

    db_session.add_all([pending_doc, failed_doc, proc_doc, completed_doc])
    await db_session.flush()

    for d in [pending_doc, failed_doc, proc_doc, completed_doc]:
        c = Chunk(
            id=uuid.uuid4(),
            document_id=d.id,
            chunk_index=0,
            content=shared_text,
            embedding=vec,
        )
        db_session.add(c)
    await db_session.commit()

    # Query matching all chunks
    results = await retrieve_chunks(
        question="Corporate password requirements 14 characters",
        db=db_session,
        top_k=10,
        min_similarity=0.1,
        embedding_provider=provider,
    )

    # Only chunks from the completed document must be returned
    assert len(results) == 1
    assert results[0].document_id == completed_doc.id
    assert results[0].document_title == "Completed Doc"
