"""Redis queue operations for asynchronous ingestion jobs."""

import json
import logging
import uuid
import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger("app.queue")


class QueueError(Exception):
    """Raised when an error occurs during queue enqueue/dequeue operations."""
    pass


async def enqueue_ingestion_job(job_id: uuid.UUID, document_id: uuid.UUID, file_path: str) -> None:
    """Enqueues an ingestion task payload into Redis.
    
    Raises QueueError on connection or command failure.
    """
    payload = json.dumps({
        "job_id": str(job_id),
        "document_id": str(document_id),
        "file_path": str(file_path),
    })

    client = None
    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=3.0,
            socket_timeout=3.0,
        )
        await client.rpush(settings.REDIS_INGESTION_QUEUE, payload)
        logger.info(
            "Enqueued ingestion job into Redis",
            extra={"job_id": str(job_id), "document_id": str(document_id)},
        )
    except Exception as exc:
        logger.error(
            f"Failed to enqueue job {job_id} to Redis: {exc}",
            extra={"job_id": str(job_id), "error": str(exc)},
        )
        raise QueueError(f"Redis enqueue failed: {exc}") from exc
    finally:
        if client:
            await client.aclose()
