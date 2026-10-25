"""Live PostgreSQL + pgvector integration tests.

These tests execute against a real PostgreSQL instance with the pgvector extension enabled.
They validate that:
1. Vector(1536) persistence and indexing work without type serialization issues.
2. The pgvector <=> cosine distance operator calculates accurate nearest-neighbor ordering in SQL.
3. The SQL WHERE filter `(Chunk.embedding.cosine_distance(vec) <= 1.0 - threshold)` executes natively.

To execute locally or in CI:
  TEST_POSTGRES_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rag_test pytest backend/tests/test_pgvector_integration.py
"""

import os
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.user import User
from app.providers.base import MockEmbeddingProvider
from app.services.retrieval import retrieve_chunks

POSTGRES_URL = os.getenv("TEST_POSTGRES_URL")

pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="Live PostgreSQL with pgvector required (set TEST_POSTGRES_URL to enable)",
)


@pytest.fixture
async def pg_session():
    """Sets up schema and yields an async session against a live PostgreSQL instance."""
    engine = create_async_engine(POSTGRES_URL, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def test_pgvector_native_cosine_distance_query(pg_session: AsyncSession):
    """Validates that PostgreSQL pgvector <=> operator executes natively and correctly orders chunks."""
    provider = MockEmbeddingProvider()

    # Create dummy admin user
    user = User(
        id=uuid.uuid4(),
        email="pg_admin@example.com",
        hashed_password="mockpassword",
        role="admin",
    )
    pg_session.add(user)
    await pg_session.flush()

    # Create completed document
    doc = Document(
        id=uuid.uuid4(),
        uploaded_by_id=user.id,
        filename="pg_policy.pdf",
        title="Postgres Policy Document",
        content_type="application/pdf",
        file_path="/tmp/pg_policy.pdf",
        file_size_bytes=1024,
        checksum_sha256="pgchecksum001",
        status="completed",
    )
    pg_session.add(doc)
    await pg_session.flush()

    # Passages with differing vectors
    passages = [
        "Corporate password complexity requires at least 14 characters.",
        "Remote work reimbursement equipment stipend provides $500.",
        "Annual paid time off gives full-time employees 20 days per calendar year.",
    ]
    vectors = await provider.embed_documents(passages)

    for idx, (content, vec) in enumerate(zip(passages, vectors)):
        chunk = Chunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            chunk_index=idx,
            content=content,
            embedding=vec,
            page_number=idx + 1,
            section_title=f"Section {idx + 1}",
        )
        pg_session.add(chunk)
    await pg_session.commit()

    # Query using retrieve_chunks (which detects PostgreSQL dialect and runs native pgvector <=> operator)
    results = await retrieve_chunks(
        question="What is the password requirement for corporate accounts?",
        db=pg_session,
        top_k=2,
        min_similarity=0.1,
        embedding_provider=provider,
    )

    assert len(results) > 0
    assert "password" in results[0].content.lower()
    assert results[0].document_title == "Postgres Policy Document"
    assert results[0].similarity_score >= 0.1
