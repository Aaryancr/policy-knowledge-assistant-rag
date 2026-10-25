"""Pydantic schemas for health and readiness endpoints."""

from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ServiceCheck(BaseModel):
    status: str  # "healthy" or "unhealthy"
    latency_ms: float | None = None
    details: dict[str, Any] | None = None
    error: str | None = None


class ReadinessResponse(BaseModel):
    status: str  # "ready" or "not_ready"
    database: ServiceCheck
    redis: ServiceCheck
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
