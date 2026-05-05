from datetime import datetime, timezone
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agents.qa_agent import chat
from models.model import Job, Status
from schemas.schemas import CreateJobRequest


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db

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
        """Execute the agent analysis and update job status."""
        job = await self.db.get(Job, job_id)
        if not job:
            return

        # Update status to RUNNING
        job.status = Status.RUNNING
        await self.db.commit()

        try:
            # Execute the agent
            result = await chat(code=cast(str, job.code), filename=cast(str, job.filename))

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
            return None
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
def get_job_service(db: AsyncSession) -> JobService:
    return JobService(db)