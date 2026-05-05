from typing import cast

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_db, get_redis_service
from schemas.schemas import MAX_CODE_SIZE, CreateJobRequest, CreateJobResponse, JobResponse
from services.jobs_services import JobService, get_job_service
from services.rate_limit_service import RateLimitService, get_rate_limit_service
from services.redis_service import RedisService

router = APIRouter()


@router.post("/jobs", status_code=202, response_model=CreateJobResponse, tags=["Jobs"])
async def create_job_endpoint(
    job_data: CreateJobRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service),
    rate_limit_service: RateLimitService = Depends(get_rate_limit_service),
) -> CreateJobResponse:
    if len(job_data.code) > MAX_CODE_SIZE:
        raise HTTPException(status_code=413, detail="Code exceeds maximum allowed size")

    # TODO: replace with actual user_id from authentication
    user_id = 1

    # Check rate limit and increment counter
    rate_info = await rate_limit_service.check_and_increment(user_id)

    # Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(rate_info.limit)
    response.headers["X-RateLimit-Remaining"] = str(rate_info.remaining)
    response.headers["X-RateLimit-Reset"] = str(int(rate_info.reset_at.timestamp()))

    service = get_job_service(db, redis_service)
    job = await service.create_job(user_id, job_data)
    background_tasks.add_task(service.run_analysis, cast(int, job.id))

    return CreateJobResponse(job_id=cast(int, job.id))

@router.get("/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def get_job_endpoint(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service),
) -> JobResponse:
    if job_id <= 0:
        raise HTTPException(status_code=400, detail="Invalid job ID")

    # TODO: replace with actual user_id from authentication
    service = get_job_service(db, redis_service)
    job = await service.get_job(job_id, user_id=1)  # Raises 403 if forbidden

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse.model_validate(job)

@router.get("/jobs", response_model=list[JobResponse], tags=["Jobs"])
async def get_all_jobs_endpoint(
    db: AsyncSession = Depends(get_db),
    redis_service: RedisService = Depends(get_redis_service),
    limit: int = 100,
    offset: int = 0,
) -> list[JobResponse]:
    # TODO: replace with actual user_id from authentication
    service = get_job_service(db, redis_service)
    jobs = await service.get_all_jobs(user_id=1, limit=limit, offset=offset)
    return [JobResponse.model_validate(job) for job in jobs]
