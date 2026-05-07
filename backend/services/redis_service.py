import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)



class RedisService:
    """Redis service with graceful degradation and error handling."""

    def __init__(self, redis_client: aioredis.Redis | None = None):
        self.client = redis_client
        self._available = redis_client is not None

    async def get(self, key: str) -> str | None:
        """
        Get a value from Redis cache.
        Returns None if key doesn't exist or Redis is unavailable.
        """
        if not self._available or not self.client:
            logger.debug(f"Redis unavailable, cache miss for key: {key}")
            return None

        try:
            value = await self.client.get(key)
            return value if value else None
        except Exception as e:
            logger.warning(f"Redis GET error for key '{key}': {e}")
            self._available = False
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        Set a value in Redis cache with optional TTL (in seconds).
        Returns True if successful, False if Redis is unavailable.
        """
        if not self._available or not self.client:
            logger.debug(f"Redis unavailable, skipping cache set for key: {key}")
            return False

        try:
            if ttl:
                await self.client.setex(key, ttl, str(value))
            else:
                await self.client.set(key, str(value))
            return True
        except Exception as e:
            logger.warning(f"Redis SET error for key '{key}': {e}")
            self._available = False
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a key from Redis cache.
        Returns True if successful, False if Redis is unavailable.
        """
        if not self._available or not self.client:
            logger.debug(f"Redis unavailable, skipping cache delete for key: {key}")
            return False

        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis DELETE error for key '{key}': {e}")
            self._available = False
            return False

    async def ping(self) -> bool:
        """
        Check if Redis is available.
        Returns True if Redis responds, False otherwise.
        """
        if not self.client:
            return False

        try:
            await self.client.ping()  # type: ignore[misc]
            self._available = True
            return True
        except Exception as e:
            logger.warning(f"Redis PING error: {e}")
            self._available = False
            return False

    async def close(self) -> None:
        """Close the Redis connection gracefully."""
        if self.client:
            try:
                await self.client.close()
            except Exception as e:
                logger.warning(f"Redis CLOSE error: {e}")