import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, cast

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.qa_agent import chat
from core.config import settings
from models.model import Job, Status
from schemas.schemas import CreateJobRequest
from services.redis_service import RedisService

logger = logging.getLogger(__name__)


class JobService:
    def __init__(self, db: AsyncSession, redis_service: Optional[RedisService] = None):
        self.db = db
        self.redis_service = redis_service

    @staticmethod
    def _compute_code_hash(code: str, filename: str) -> str:
        """
        Compute a deterministic hash for the code and filename.
        Same code + filename = same hash.
        """
        content = f"{filename}:{code}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def create_job(self, user_id: int, job_data: CreateJobRequest) -> Job:
        """Create a new job with PENDING status."""
        job = Job(
            user_id=user_id,
            filename=job_data.filename,
            code=job_data.code,
            status=Status.PENDING,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def run_analysis(self, job_id: int) -> None:
        """Execute the agent analysis and update job status with cache support."""
        job = await self.db.get(Job, job_id)
        if not job:
            return

        # Compute hash of the code for cache key
        code_hash = self._compute_code_hash(cast(str, job.code), cast(str, job.filename))
        cache_key = f"agent_result:{code_hash}"

        # Try to get from cache
        cached_result = None
        if self.redis_service:
            cached_result = await self.redis_service.get(cache_key)

        if cached_result:
            # CACHE HIT - Use cached result without calling the agent
            logger.info(
                f"Cache HIT for job_id={job_id}, hash={code_hash[:8]}... "
                f"(skipping LLM call)"
            )

            job.status = Status.COMPLETED
            job.result = cached_result
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()
            return

        # CACHE MISS - Execute the agent
        logger.info(
            f"Cache MISS for job_id={job_id}, hash={code_hash[:8]}... "
            f"(executing LLM)"
        )

        # Update status to RUNNING
        job.status = Status.RUNNING
        await self.db.commit()

        try:
            # Execute the agent
            result = await chat(code=cast(str, job.code), filename=cast(str, job.filename))

            # Save to cache for future requests
            if self.redis_service:
                cache_saved = await self.redis_service.set(
                    cache_key, result, ttl=settings.CACHE_TTL
                )
                if cache_saved:
                    logger.info(
                        f"Result cached for hash={code_hash[:8]}... "
                        f"with TTL={settings.CACHE_TTL}s"
                    )

            # Update to COMPLETED with result
            job.status = Status.COMPLETED
            job.result = result
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()

        except Exception as e:
            # Update to FAILED with error message
            job.status = Status.FAILED
            job.error_message = str(e)
            job.completed_at = datetime.now(timezone.utc)
            await self.db.commit()

    async def get_job(self, job_id: int, user_id: int) -> Job | None:
        """Get a job by ID, verifying it belongs to the user."""
        job = await self.db.get(Job, job_id)
        if not job:
            return None
        if cast(int, job.user_id) != user_id:
            raise HTTPException(status_code=403, detail="Access forbidden")
        return job

    async def get_all_jobs(self, user_id: int, limit: int = 100, offset: int = 0) -> list[Job]:
        """Get all jobs for a user with pagination."""
        query = (
            select(Job)
            .where(Job.user_id == user_id)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())


# Dependency for FastAPI
def get_job_service(
    db: AsyncSession, redis_service: Optional[RedisService] = None
) -> JobService:
    return JobService(db, redis_service)