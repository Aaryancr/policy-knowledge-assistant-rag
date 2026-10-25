"""Background Redis worker consuming and executing asynchronous document ingestion tasks."""

import asyncio
from datetime import datetime, timezone
import json
import logging
import signal
from typing import Any
import uuid

import redis.asyncio as aioredis
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import setup_logging
from app.database import AsyncSessionLocal
from app.models.chunk import Chunk
from app.models.document import Document
from app.models.ingestion_job import IngestionJob
from app.providers.base import EmbeddingProvider, get_embedding_provider
from app.services.chunking import chunk_sections
from app.services.extractor import extract_text

settings = get_settings()
logger = logging.getLogger("app.worker")


async def process_job(
    job_payload: dict[str, Any],
    db: AsyncSession,
    embedding_provider: EmbeddingProvider | None = None,
) -> None:
    """Processes a single ingestion job idempotently from disk read to vector storage."""
    job_id = uuid.UUID(job_payload["job_id"])
    doc_id = uuid.UUID(job_payload["document_id"])
    file_path = job_payload["file_path"]

    # 1. Load job and document records
    job_res = await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))
    job = job_res.scalar_one_or_none()

    doc_res = await db.execute(select(Document).where(Document.id == doc_id))
    doc = doc_res.scalar_one_or_none()

    if not job or not doc:
        logger.error(f"Job {job_id} or Document {doc_id} not found in database. Aborting.")
        return

    # Idempotency check: if already completed and has chunks, avoid redundant processing
    if job.status == "completed" and doc.status == "completed" and doc.total_chunks > 0:
        logger.info(f"Job {job_id} is already completed. Skipping idempotent execution.")
        return

    # 2. Claim job and update status to processing
    job.status = "processing"
    job.started_at = datetime.now(timezone.utc)
    job.error_message = None
    doc.status = "processing"
    doc.error_message = None
    await db.commit()

    logger.info(f"Starting ingestion processing for doc '{doc.filename}' (Job {job_id})")

    # 3. Extract text from file
    sections = extract_text(file_path, doc.content_type)

    # 4. Chunk sections into indexed passages
    chunks = chunk_sections(
        sections=sections,
        document_id=doc.id,
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
    )

    # Handle empty or unscanned text documents gracefully
    if not chunks:
        logger.warning(f"No extractable text chunks found in '{doc.filename}' (Job {job_id})")
        await db.execute(delete(Chunk).where(Chunk.document_id == doc.id))
        doc.total_chunks = 0
        doc.status = "completed"
        doc.error_message = "No extractable text found (e.g. image-only PDF)"
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        await db.commit()
        return

    # 5. Generate dense vector embeddings
    provider = embedding_provider or get_embedding_provider()
    texts = [c.content for c in chunks]
    vectors = await provider.embed_documents(texts)

    # 6. Validate vector dimensions
    expected_dim = settings.EMBEDDING_DIMENSION
    for i, vec in enumerate(vectors):
        if len(vec) != expected_dim:
            raise ValueError(
                f"Generated vector dimension mismatch at chunk {i}: got {len(vec)}, expected {expected_dim}"
            )

    # 7. Atomically persist chunks and update document & job status
    # Idempotently remove any prior chunks for this document
    await db.execute(delete(Chunk).where(Chunk.document_id == doc.id))

    for c, vec in zip(chunks, vectors):
        db_chunk = Chunk(
            id=uuid.uuid4(),
            document_id=doc.id,
            chunk_index=c.chunk_index,
            content=c.content,
            page_number=c.page_number,
            section_title=c.section_title,
            metadata_json=c.metadata_json,
            embedding=vec,
        )
        db.add(db_chunk)

    doc.total_chunks = len(chunks)
    doc.status = "completed"
    doc.error_message = None

    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)
    job.error_message = None

    await db.commit()
    logger.info(
        f"Successfully completed ingestion for doc '{doc.filename}': "
        f"{len(chunks)} chunks embedded and persisted to PostgreSQL with pgvector."
    )


async def handle_job_failure(
    job_payload: dict[str, Any],
    exc: Exception,
    redis_client: aioredis.Redis,
) -> None:
    """Handles transient and permanent job failures with bounded exponential backoff retries."""
    job_id = uuid.UUID(job_payload["job_id"])
    doc_id = uuid.UUID(job_payload["document_id"])

    async with AsyncSessionLocal() as db:
        job = (await db.execute(select(IngestionJob).where(IngestionJob.id == job_id))).scalar_one_or_none()
        doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()

        if not job or not doc:
            return

        job.retry_count += 1
        err_msg = str(exc)

        if job.retry_count <= job.max_retries:
            # Schedule retry with bounded exponential backoff
            backoff_secs = min(30, 2 ** job.retry_count)
            job.status = "queued"
            job.error_message = f"Transient failure (attempt {job.retry_count}/{job.max_retries}): {err_msg}"
            doc.status = "processing"
            doc.error_message = f"Retrying ingestion ({job.retry_count}/{job.max_retries})"
            await db.commit()

            logger.warning(
                f"Job {job_id} encountered transient error: {err_msg}. "
                f"Retrying ({job.retry_count}/{job.max_retries}) in {backoff_secs}s..."
            )
            await asyncio.sleep(backoff_secs)
            await redis_client.rpush(settings.REDIS_INGESTION_QUEUE, json.dumps(job_payload))
        else:
            # Permanent failure after exhausting all retries
            job.status = "failed"
            job.error_message = f"Max retries ({job.max_retries}) exhausted. Final error: {err_msg}"
            doc.status = "failed"
            doc.error_message = f"Ingestion permanently failed: {err_msg}"
            await db.commit()

            logger.error(
                f"Job {job_id} permanently failed after {job.max_retries} attempts. Error: {err_msg}"
            )


async def run_worker() -> None:
    """Main worker loop pulling ingestion jobs from Redis and delegating execution."""
    setup_logging(level=settings.LOG_LEVEL)
    logger.info("Background ingestion worker starting up. Connecting to Redis queue...")

    stop_event = asyncio.Event()

    def handle_stop():
        logger.info("Worker termination signal received. Initiating graceful shutdown...")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_stop)
        except NotImplementedError:
            pass

    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=5.0,
        socket_timeout=5.0,
    )

    logger.info(f"Worker listening on Redis queue '{settings.REDIS_INGESTION_QUEUE}'")

    try:
        while not stop_event.is_set():
            try:
                # BLPOP with a 2-second timeout allows loop to check stop_event regularly
                item = await redis_client.blpop(settings.REDIS_INGESTION_QUEUE, timeout=2.0)
                if not item:
                    continue

                _, raw_payload = item
                job_payload = json.loads(raw_payload)

                async with AsyncSessionLocal() as db:
                    try:
                        await process_job(job_payload, db)
                    except Exception as job_exc:
                        await db.rollback()
                        logger.exception(f"Error processing job {job_payload.get('job_id')}: {job_exc}")
                        await handle_job_failure(job_payload, job_exc, redis_client)

            except (aioredis.ConnectionError, aioredis.TimeoutError) as conn_exc:
                if not stop_event.is_set():
                    logger.warning(f"Redis connection issue: {conn_exc}. Retrying in 3 seconds...")
                    await asyncio.sleep(3.0)
            except Exception as loop_exc:
                if not stop_event.is_set():
                    logger.error(f"Unexpected worker loop exception: {loop_exc}")
                    await asyncio.sleep(1.0)
    finally:
        await redis_client.aclose()
        logger.info("Ingestion worker shut down cleanly.")


def main() -> None:
    try:
        asyncio.run(run_worker())
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    main()
