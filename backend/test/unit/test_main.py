from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from services.redis_service import RedisService


@pytest.mark.asyncio
async def test_health_check() -> None:
    # Mock redis_service in app.state for testing
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    app.state.redis_service = RedisService(mock_redis)

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")

        # The response might be 200 (all ok) or 503 (degraded)
        # depending on whether PostgreSQL is available
        assert response.status_code in [200, 503]
        data = response.json()
        assert data["status"] in ["ok", "degraded"]
        assert "dependencies" in data
        assert "redis" in data["dependencies"]
        assert "postgres" in data["dependencies"]
    finally:
        # Cleanup
        delattr(app.state, "redis_service")
