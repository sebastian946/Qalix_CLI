from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text

from core.config import engine, get_redis_service
from services.redis_service import RedisService

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check(redis_service: RedisService = Depends(get_redis_service)) -> JSONResponse:
    dependencies: dict[str, str] = {"postgres": "ok", "redis": "ok"}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        dependencies["postgres"] = "error"

    # Use RedisService ping method with graceful degradation
    if not await redis_service.ping():
        dependencies["redis"] = "error"

    all_ok = all(v == "ok" for v in dependencies.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ok" if all_ok else "degraded", "dependencies": dependencies},
    )
