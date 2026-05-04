from typing import cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_db
from schemas.schemas import MAX_CODE_SIZE, CreateJobRequest, CreateJobResponse, JobResponse
from services.jobs_services import create_job, get_job, run_analysis

router = APIRouter()


@router.post("/jobs", status_code=202, response_model=CreateJobResponse, tags=["Jobs"])
async def create_job_endpoint(
    job_data: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> CreateJobResponse:
    if len(job_data.code) > MAX_CODE_SIZE:
        raise HTTPException(status_code=413, detail="Code exceeds maximum allowed size")

    # TODO: replace with actual user_id from authentication
    user_id = 1

    job = await create_job(db, user_id, job_data)
    background_tasks.add_task(run_analysis, cast(int, job.id))

    return CreateJobResponse(job_id=cast(int, job.id))

@router.get("/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def get_job_endpoint(job_id: int, db: AsyncSession = Depends(get_db)) -> JobResponse:
    if job_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    # TODO: replace with actual user_id from authentication
    job = await get_job(db, job_id, user_id=1)

    return JobResponse.model_validate(job)
