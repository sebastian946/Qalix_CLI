from sqlalchemy.ext.asyncio import AsyncSession

from models.model import Job, Status
from schemas.schemas import CreateJobRequest


async def create_job(db: AsyncSession, user_id: int, job_data: CreateJobRequest) -> Job:
    job = Job(
        user_id=user_id,
        filename=job_data.filename,
        code=job_data.code,
        status=Status.PENDING,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def run_analysis(_job_id: int) -> None:
    pass
