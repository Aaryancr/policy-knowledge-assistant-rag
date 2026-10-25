"""Tests for /health and /ready endpoints."""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_check_healthy(async_client: AsyncClient):
    # Mock redis ping to succeed
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_redis.aclose = AsyncMock()

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        response = await async_client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"]["status"] == "healthy"
        assert data["redis"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_check_unhealthy_redis(async_client: AsyncClient):
    # Mock redis ping to fail / raise exception
    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = ConnectionError("Could not connect to Redis")

    with patch("redis.asyncio.from_url", return_value=mock_redis):
        response = await async_client.get("/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["database"]["status"] == "healthy"
        assert data["redis"]["status"] == "unhealthy"
        assert "Could not connect to Redis" in data["redis"]["error"]
