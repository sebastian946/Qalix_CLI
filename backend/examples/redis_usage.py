"""
Example usage of RedisService in FastAPI endpoints.

This demonstrates how to use the centralized Redis configuration
with graceful degradation.
"""

from fastapi import APIRouter, Depends

from core.config import get_redis_service
from services.redis_service import RedisService

router = APIRouter()


@router.get("/example/cache")
async def example_with_cache(redis_service: RedisService = Depends(get_redis_service)):
    """
    Example endpoint showing how to use Redis cache with graceful degradation.
    """
    # Try to get from cache
    cached_value = await redis_service.get("example_key")

    if cached_value:
        return {"source": "cache", "value": cached_value}

    # If not in cache, compute the value
    computed_value = "expensive_computation_result"

    # Try to cache the result (TTL: 5 minutes)
    await redis_service.set("example_key", computed_value, ttl=300)

    return {"source": "computed", "value": computed_value}


@router.post("/example/invalidate")
async def example_invalidate_cache(
    redis_service: RedisService = Depends(get_redis_service),
):
    """
    Example endpoint showing how to invalidate cache.
    """
    success = await redis_service.delete("example_key")

    return {
        "invalidated": success,
        "message": "Cache invalidated" if success else "Cache not available",
    }


@router.get("/example/health")
async def example_health_check(redis_service: RedisService = Depends(get_redis_service)):
    """
    Example endpoint showing how to check Redis availability.
    """
    is_available = await redis_service.ping()

    return {
        "redis_available": is_available,
        "message": "Redis is available" if is_available else "Redis is unavailable",
    }
