from typing import AsyncGenerator

import redis.asyncio as aioredis
from langchain_anthropic import ChatAnthropic
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str
    DATABASE_URL: str
    REDIS_URL: str
    ENVIRONMENT: str
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()  # type: ignore[call-arg]

llm = ChatAnthropic(
    model_name="claude-haiku-4-5-20251001",
    api_key=settings.ANTHROPIC_API_KEY,  # type: ignore[arg-type]
    temperature=0,
    max_retries=2,
)

redis_client: aioredis.Redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

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
