from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from core.config import engine, redis_client

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    dependencies: dict[str, str] = {"postgres": "ok", "redis": "ok"}

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        dependencies["postgres"] = "error"

    try:
        await redis_client.ping()
    except Exception:
        dependencies["redis"] = "error"

    all_ok = all(v == "ok" for v in dependencies.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ok" if all_ok else "degraded", "dependencies": dependencies},
    )
