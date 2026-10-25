"""Integration and unit tests for the background Redis worker process."""

from unittest.mock import AsyncMock, patch
import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk import Chunk
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.models.user import User
from app.providers.base import MockEmbeddingProvider
from app.worker import handle_job_failure, process_job
from tests.helpers import create_test_pdf, create_test_txt


@pytest.mark.asyncio
async def test_worker_successful_job_processing(
    db_session: AsyncSession,
    admin_user: User,
    tmp_path,
):
    # 1. Create test document file on disk
    txt_path = create_test_txt(
        str(tmp_path),
        filename="pto_policy.txt",
        content="Employees receive 20 days PTO per year.\n\nCarryover is permitted up to 5 days.",
    )

    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        title="PTO Policy",
        filename="pto_policy.txt",
        file_path=txt_path,
        file_size_bytes=100,
        content_type="text/plain",
        status="pending",
        uploaded_by_id=admin_user.id,
    )
    job = IngestionJob(
        id=job_id,
        document_id=doc_id,
        status="queued",
        retry_count=0,
        max_retries=3,
    )
    db_session.add(doc)
    db_session.add(job)
    await db_session.commit()

    # 2. Process job with mock embedding provider
    payload = {
        "job_id": str(job_id),
        "document_id": str(doc_id),
        "file_path": txt_path,
    }
    await process_job(payload, db_session, MockEmbeddingProvider(dim=1536))

    # 3. Assert document and job status updated to completed
    await db_session.refresh(doc)
    await db_session.refresh(job)

    assert doc.status == "completed"
    assert doc.total_chunks == 2
    assert job.status == "completed"
    assert job.completed_at is not None

    # 4. Assert chunks and pgvector embeddings stored
    chunks_res = await db_session.execute(
        select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.chunk_index.asc())
    )
    chunks = chunks_res.scalars().all()
    assert len(chunks) == 2
    assert chunks[0].embedding is not None
    assert len(chunks[0].embedding) == 1536
    assert "20 days PTO" in chunks[0].content


@pytest.mark.asyncio
async def test_worker_idempotent_reprocessing(
    db_session: AsyncSession,
    admin_user: User,
    tmp_path,
):
    txt_path = create_test_txt(str(tmp_path), content="Test content for idempotency check.")
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        title="Idempotency Test",
        filename="idempotent.txt",
        file_path=txt_path,
        content_type="text/plain",
        status="pending",
        uploaded_by_id=admin_user.id,
    )
    job = IngestionJob(
        id=job_id,
        document_id=doc_id,
        status="queued",
        retry_count=0,
    )
    db_session.add(doc)
    db_session.add(job)
    await db_session.commit()

    payload = {"job_id": str(job_id), "document_id": str(doc_id), "file_path": txt_path}

    # First execution
    await process_job(payload, db_session)
    chunks_after_first = (await db_session.execute(select(Chunk).where(Chunk.document_id == doc_id))).scalars().all()
    assert len(chunks_after_first) == 1

    # Force re-execution by resetting job status to processing
    job.status = "processing"
    await db_session.commit()

    # Second execution: must not create duplicate chunks
    await process_job(payload, db_session)
    chunks_after_second = (await db_session.execute(select(Chunk).where(Chunk.document_id == doc_id))).scalars().all()
    assert len(chunks_after_second) == 1


@pytest.mark.asyncio
async def test_worker_scanned_or_blank_pdf_handling(
    db_session: AsyncSession,
    admin_user: User,
    tmp_path,
):
    blank_pdf = create_test_pdf(str(tmp_path), blank_pages=2)
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        title="Blank Scanned Doc",
        filename="blank.pdf",
        file_path=blank_pdf,
        content_type="application/pdf",
        status="pending",
        uploaded_by_id=admin_user.id,
    )
    job = IngestionJob(
        id=job_id,
        document_id=doc_id,
        status="queued",
        retry_count=0,
    )
    db_session.add(doc)
    db_session.add(job)
    await db_session.commit()

    payload = {"job_id": str(job_id), "document_id": str(doc_id), "file_path": blank_pdf}
    await process_job(payload, db_session)

    await db_session.refresh(doc)
    await db_session.refresh(job)

    # Worker completes gracefully without crashing or creating empty chunks
    assert doc.status == "completed"
    assert doc.total_chunks == 0
    assert "No extractable text" in doc.error_message
    assert job.status == "completed"


@pytest.mark.asyncio
async def test_worker_transient_failure_and_retry(
    db_session: AsyncSession,
    admin_user: User,
):
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()

    doc = Document(id=doc_id, title="Doc", filename="f.txt", status="processing")
    job = IngestionJob(id=job_id, document_id=doc_id, status="processing", retry_count=0, max_retries=3)
    db_session.add(doc)
    db_session.add(job)
    await db_session.commit()

    mock_redis = AsyncMock()
    payload = {"job_id": str(job_id), "document_id": str(doc_id), "file_path": "/fake/path.txt"}

    # Mock AsyncSessionLocal to yield the test db_session
    with patch("app.worker.AsyncSessionLocal") as mock_session_maker, patch("asyncio.sleep", new_callable=AsyncMock):
        mock_session_maker.return_value.__aenter__.return_value = db_session
        mock_session_maker.return_value.__aexit__.return_value = None

        await handle_job_failure(payload, ConnectionError("Provider API timeout"), mock_redis)

    await db_session.refresh(job)
    await db_session.refresh(doc)

    assert job.retry_count == 1
    assert job.status == "queued"
    assert "Transient failure (attempt 1/3)" in job.error_message
    assert doc.status == "processing"
    # Redis re-enqueue called
    assert mock_redis.rpush.called


@pytest.mark.asyncio
async def test_worker_retry_exhaustion_permanent_failure(
    db_session: AsyncSession,
    admin_user: User,
):
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()

    doc = Document(id=doc_id, title="Doc", filename="f.txt", status="processing")
    # Already at max_retries
    job = IngestionJob(id=job_id, document_id=doc_id, status="processing", retry_count=3, max_retries=3)
    db_session.add(doc)
    db_session.add(job)
    await db_session.commit()

    mock_redis = AsyncMock()
    payload = {"job_id": str(job_id), "document_id": str(doc_id), "file_path": "/fake/path.txt"}

    with patch("app.worker.AsyncSessionLocal") as mock_session_maker, patch("asyncio.sleep", new_callable=AsyncMock):
        mock_session_maker.return_value.__aenter__.return_value = db_session
        mock_session_maker.return_value.__aexit__.return_value = None

        await handle_job_failure(payload, ValueError("Corrupt file content"), mock_redis)

    await db_session.refresh(job)
    await db_session.refresh(doc)

    assert job.retry_count == 4
    assert job.status == "failed"
    assert "Max retries (3) exhausted" in job.error_message
    assert doc.status == "failed"
    assert "Corrupt file content" in doc.error_message
    # No further re-enqueue
    assert not mock_redis.rpush.called
