"""Health and readiness check endpoints."""

import time
from fastapi import APIRouter, Depends, Response, status
import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.schemas.health import HealthResponse, ReadinessResponse, ServiceCheck

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe: verifies that the web service process is alive and receiving requests."""
    return HealthResponse()


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> ReadinessResponse:
    """Readiness probe: verifies connectivity to PostgreSQL and Redis before traffic routing."""
    overall_ready = True

    # 1. Check PostgreSQL Database Connectivity
    db_start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        db_latency = round((time.perf_counter() - db_start) * 1000, 2)
        db_check = ServiceCheck(
            status="healthy",
            latency_ms=db_latency,
            details={"database": settings.POSTGRES_DB},
        )
    except Exception as exc:
        overall_ready = False
        db_check = ServiceCheck(
            status="unhealthy",
            latency_ms=round((time.perf_counter() - db_start) * 1000, 2),
            error=str(exc),
        )

    # 2. Check Redis Connectivity
    redis_start = time.perf_counter()
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        ping_res = await redis_client.ping()
        await redis_client.aclose()
        redis_latency = round((time.perf_counter() - redis_start) * 1000, 2)
        redis_check = ServiceCheck(
            status="healthy" if ping_res else "unhealthy",
            latency_ms=redis_latency,
        )
    except Exception as exc:
        overall_ready = False
        redis_check = ServiceCheck(
            status="unhealthy",
            latency_ms=round((time.perf_counter() - redis_start) * 1000, 2),
            error=str(exc),
        )

    if not overall_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="not_ready",
            database=db_check,
            redis=redis_check,
        )

    return ReadinessResponse(
        status="ready",
        database=db_check,
        redis=redis_check,
    )
