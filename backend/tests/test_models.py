"""Tests for SQLAlchemy ORM models, relationships, foreign keys, cascades, and constraints."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat_log import ChatLog
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.models.user import User


@pytest.mark.asyncio
async def test_document_and_chunk_lifecycle(
    db_session: AsyncSession,
    admin_user: User,
):
    # 1. Create document
    doc = Document(
        title="Remote Work Policy",
        filename="remote_work_policy.pdf",
        file_path="/uploads/remote_work_policy.pdf",
        file_size_bytes=10240,
        content_type="application/pdf",
        checksum_sha256="abc123sha256test",
        status="completed",
        uploaded_by_id=admin_user.id,
        total_chunks=1,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    assert doc.id is not None
    assert doc.uploaded_by_id == admin_user.id

    # 2. Add chunk with embedding and metadata
    dummy_vec = [0.0] * 1536
    dummy_vec[0] = 0.5
    dummy_vec[1] = -0.5

    chunk = Chunk(
        document_id=doc.id,
        chunk_index=0,
        content="Employees may work remotely up to 2 days per week upon manager approval.",
        page_number=1,
        section_title="Eligibility",
        metadata_json={"source": "remote_work_policy.pdf", "page": 1},
        embedding=dummy_vec,
    )
    db_session.add(chunk)
    await db_session.commit()
    await db_session.refresh(chunk)

    assert chunk.id is not None
    assert chunk.document_id == doc.id
    assert chunk.page_number == 1
    assert chunk.metadata_json["source"] == "remote_work_policy.pdf"

    # 3. Add ingestion job
    job = IngestionJob(
        document_id=doc.id,
        status="completed",
        retry_count=0,
        max_retries=3,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    assert job.id is not None
    assert job.status == "completed"

    # 4. Add chat log
    chat = ChatLog(
        user_id=admin_user.id,
        query="Can I work remotely?",
        retrieved_chunk_ids=[str(chunk.id)],
        answer="Yes, up to 2 days per week with manager approval.",
        is_unanswerable=False,
        latency_ms=120,
    )
    db_session.add(chat)
    await db_session.commit()
    await db_session.refresh(chat)

    assert chat.id is not None
    assert chat.retrieved_chunk_ids == [str(chunk.id)]

    # 5. Test Cascade Delete: deleting the document must cascade-delete chunks and jobs
    await db_session.delete(doc)
    await db_session.commit()

    chunk_check = await db_session.execute(select(Chunk).where(Chunk.document_id == doc.id))
    assert chunk_check.scalar_one_or_none() is None

    job_check = await db_session.execute(select(IngestionJob).where(IngestionJob.document_id == doc.id))
    assert job_check.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_chunk_unique_constraint(
    db_session: AsyncSession,
    admin_user: User,
):
    doc = Document(
        title="Leave Policy",
        filename="leave_policy.pdf",
        status="completed",
        uploaded_by_id=admin_user.id,
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    chunk1 = Chunk(
        document_id=doc.id,
        chunk_index=0,
        content="First chunk content",
        metadata_json={},
    )
    db_session.add(chunk1)
    await db_session.commit()

    # Attempt to insert a second chunk with identical (document_id, chunk_index)
    chunk2 = Chunk(
        document_id=doc.id,
        chunk_index=0,
        content="Duplicate chunk index content",
        metadata_json={},
    )
    db_session.add(chunk2)

    with pytest.raises(IntegrityError):
        await db_session.commit()

    await db_session.rollback()
