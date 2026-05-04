from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_db
from schemas.schemas import MAX_CODE_SIZE, CreateJobRequest, CreateJobResponse
from services.jobs_services import create_job, run_analysis

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
    background_tasks.add_task(run_analysis, job.id)

    return CreateJobResponse(job_id=job.id)
