from typing import cast

from fastapi import HTTPException
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

async def get_job(db: AsyncSession, job_id: int, user_id: int) -> Job:
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if cast(int, job.user_id) != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    return job