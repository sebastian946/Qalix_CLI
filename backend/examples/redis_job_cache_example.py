"""
Ejemplo: Cómo usar Redis para cachear resultados de jobs
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_db, get_redis_service
from services.jobs_services import JobService
from services.redis_service import RedisService

router = APIRouter()


@router.get("/jobs/{job_id}/result")
async def get_job_result_cached(
    job_id: int,
    redis_service: RedisService = Depends(get_redis_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene el resultado de un job.
    1. Primero intenta obtenerlo del caché (Redis)
    2. Si no está en caché, lo busca en la DB y lo guarda en caché
    """

    # 1. Definir la clave del caché
    # Usa un patrón consistente: "tipo:id:campo"
    cache_key = f"job:{job_id}:result"

    # 2. Intentar obtener del caché
    cached_result = await redis_service.get(cache_key)

    if cached_result:
        # ✅ Cache HIT - Respuesta ultra rápida
        return {
            "job_id": job_id,
            "result": cached_result,
            "source": "cache",  # Para debugging
            "cached": True,
        }

    # 3. Cache MISS - Obtener de la base de datos
    job_service = JobService(db)
    job = await job_service.get_job(job_id, user_id=1)  # Reemplaza con el user_id real

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.result:
        # El job aún no tiene resultado
        return {
            "job_id": job_id,
            "status": job.status.value,
            "result": None,
            "source": "database",
            "cached": False,
        }

    # 4. Guardar en caché con TTL de 10 minutos (600 segundos)
    # Si el job está completado, su resultado no cambiará
    ttl = 600 if job.status.value == "completed" else 60  # 1 min si está pending/running

    await redis_service.set(cache_key, job.result, ttl=ttl)

    # 5. Retornar el resultado
    return {
        "job_id": job_id,
        "result": job.result,
        "status": job.status.value,
        "source": "database",
        "cached": False,
        "ttl": ttl,
    }


@router.delete("/jobs/{job_id}/cache")
async def invalidate_job_cache(
    job_id: int,
    redis_service: RedisService = Depends(get_redis_service),
):
    """
    Invalida el caché de un job específico.
    Útil cuando actualizas un job y quieres forzar que se recargue de la DB.
    """
    cache_key = f"job:{job_id}:result"

    success = await redis_service.delete(cache_key)

    return {
        "job_id": job_id,
        "cache_invalidated": success,
        "message": "Cache invalidated successfully" if success else "Redis unavailable",
    }