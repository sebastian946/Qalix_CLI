from unittest.mock import AsyncMock

import pytest

from services.redis_service import RedisService


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    """Create a mock Redis client."""
    client = AsyncMock()
    client.get = AsyncMock(return_value="test_value")
    client.set = AsyncMock()
    client.setex = AsyncMock()
    client.delete = AsyncMock()
    client.ping = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_get_returns_value_when_redis_available(mock_redis_client: AsyncMock) -> None:
    """Test that get returns value when Redis is available."""
    # Arrange
    service = RedisService(mock_redis_client)
    mock_redis_client.get.return_value = "cached_value"

    # Act
    result = await service.get("test_key")

    # Assert
    assert result == "cached_value"
    mock_redis_client.get.assert_awaited_once_with("test_key")


@pytest.mark.asyncio
async def test_get_returns_none_when_key_not_exists(mock_redis_client: AsyncMock) -> None:
    """Test that get returns None when key doesn't exist."""
    # Arrange
    service = RedisService(mock_redis_client)
    mock_redis_client.get.return_value = None

    # Act
    result = await service.get("nonexistent_key")

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_returns_none_when_redis_unavailable() -> None:
    """Test graceful degradation when Redis is unavailable."""
    # Arrange
    service = RedisService(None)

    # Act
    result = await service.get("test_key")

    # Assert
    assert result is None


@pytest.mark.asyncio
async def test_get_handles_redis_error(mock_redis_client: AsyncMock) -> None:
    """Test that get handles Redis errors gracefully."""
    # Arrange
    service = RedisService(mock_redis_client)
    mock_redis_client.get.side_effect = Exception("Redis connection error")

    # Act
    result = await service.get("test_key")

    # Assert
    assert result is None
    assert service._available is False


@pytest.mark.asyncio
async def test_set_stores_value_with_ttl(mock_redis_client: AsyncMock) -> None:
    """Test that set stores value with TTL."""
    # Arrange
    service = RedisService(mock_redis_client)

    # Act
    result = await service.set("test_key", "test_value", ttl=300)

    # Assert
    assert result is True
    mock_redis_client.setex.assert_awaited_once_with("test_key", 300, "test_value")


@pytest.mark.asyncio
async def test_set_stores_value_without_ttl(mock_redis_client: AsyncMock) -> None:
    """Test that set stores value without TTL."""
    # Arrange
    service = RedisService(mock_redis_client)

    # Act
    result = await service.set("test_key", "test_value")

    # Assert
    assert result is True
    mock_redis_client.set.assert_awaited_once_with("test_key", "test_value")


@pytest.mark.asyncio
async def test_set_returns_false_when_redis_unavailable() -> None:
    """Test that set returns False when Redis is unavailable."""
    # Arrange
    service = RedisService(None)

    # Act
    result = await service.set("test_key", "test_value")

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_set_handles_redis_error(mock_redis_client: AsyncMock) -> None:
    """Test that set handles Redis errors gracefully."""
    # Arrange
    service = RedisService(mock_redis_client)
    mock_redis_client.set.side_effect = Exception("Redis connection error")

    # Act
    result = await service.set("test_key", "test_value")

    # Assert
    assert result is False
    assert service._available is False


@pytest.mark.asyncio
async def test_delete_removes_key(mock_redis_client: AsyncMock) -> None:
    """Test that delete removes key from Redis."""
    # Arrange
    service = RedisService(mock_redis_client)

    # Act
    result = await service.delete("test_key")

    # Assert
    assert result is True
    mock_redis_client.delete.assert_awaited_once_with("test_key")


@pytest.mark.asyncio
async def test_delete_returns_false_when_redis_unavailable() -> None:
    """Test that delete returns False when Redis is unavailable."""
    # Arrange
    service = RedisService(None)

    # Act
    result = await service.delete("test_key")

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_ping_returns_true_when_redis_available(mock_redis_client: AsyncMock) -> None:
    """Test that ping returns True when Redis is available."""
    # Arrange
    service = RedisService(mock_redis_client)

    # Act
    result = await service.ping()

    # Assert
    assert result is True
    assert service._available is True
    mock_redis_client.ping.assert_awaited_once()


@pytest.mark.asyncio
async def test_ping_returns_false_when_redis_unavailable() -> None:
    """Test that ping returns False when Redis client is None."""
    # Arrange
    service = RedisService(None)

    # Act
    result = await service.ping()

    # Assert
    assert result is False


@pytest.mark.asyncio
async def test_ping_handles_redis_error(mock_redis_client: AsyncMock) -> None:
    """Test that ping handles Redis errors gracefully."""
    # Arrange
    service = RedisService(mock_redis_client)
    mock_redis_client.ping.side_effect = Exception("Redis connection error")

    # Act
    result = await service.ping()

    # Assert
    assert result is False
    assert service._available is False


@pytest.mark.asyncio
async def test_close_closes_connection(mock_redis_client: AsyncMock) -> None:
    """Test that close properly closes Redis connection."""
    # Arrange
    service = RedisService(mock_redis_client)

    # Act
    await service.close()

    # Assert
    mock_redis_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_handles_error_gracefully(mock_redis_client: AsyncMock) -> None:
    """Test that close handles errors gracefully."""
    # Arrange
    service = RedisService(mock_redis_client)
    mock_redis_client.close.side_effect = Exception("Close error")

    # Act - should not raise
    await service.close()

    # Assert
    mock_redis_client.close.assert_awaited_once()
