import logging
from typing import AsyncGenerator, Optional

import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from langchain_anthropic import ChatAnthropic
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base


from services.redis_service import RedisService

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    ENVIRONMENT: str
    CACHE_TTL: int = 3600  # Default: 1 hour (in seconds)
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with graceful degradation for Redis."""
    redis_client: Optional[aioredis.Redis] = None

    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Running without cache.")
        redis_client = None

    app.state.redis = redis_client
    app.state.redis_service = RedisService(redis_client)

    yield

    if redis_client:
        try:
            await redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {e}")

settings = Settings()  # type: ignore[call-arg]

llm = ChatAnthropic(
    model_name="claude-haiku-4-5-20251001",
    api_key=settings.ANTHROPIC_API_KEY,  # type: ignore[arg-type]
    temperature=0,
    max_retries=2,
)


Base = declarative_base()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "DEV",
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_redis_service(request: Request) -> RedisService:
    """
    Dependency for FastAPI to get RedisService.
    Requires app.state.redis_service to be set in lifespan.
    Usage: redis_service: RedisService = Depends(get_redis_service)
    """
    return request.app.state.redis_service


async def get_redis(app: FastAPI) -> Optional[aioredis.Redis]:
    """Get raw Redis client from app state (for backward compatibility)."""
    return app.state.redis


# Initialize a placeholder redis_client for backward compatibility
# This will be set properly in the lifespan context
redis_client: Optional[aioredis.Redis] = None
