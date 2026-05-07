"""
Ejemplo: Cómo cachear listas de datos con Redis
"""

import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_db, get_redis_service
from schemas.schemas import JobResponse
from services.jobs_services import JobService
from services.redis_service import RedisService

router = APIRouter()


@router.get("/users/{user_id}/jobs")
async def get_user_jobs_cached(
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    redis_service: RedisService = Depends(get_redis_service),
    db: AsyncSession = Depends(get_db),
) -> list[JobResponse]:
    """
    Obtiene los jobs de un usuario con caché.

    IMPORTANTE: Para listas, necesitas serializar a JSON
    """

    # 1. Clave del caché con paginación
    cache_key = f"user:{user_id}:jobs:limit={limit}:offset={offset}"

    # 2. Intentar obtener del caché
    cached_data = await redis_service.get(cache_key)

    if cached_data:
        # Deserializar de JSON
        jobs_data = json.loads(cached_data)
        # Convertir a JobResponse (Pydantic models)
        jobs = [JobResponse(**job) for job in jobs_data]
        return jobs

    # 3. Obtener de la base de datos
    job_service = JobService(db)
    jobs = await job_service.get_all_jobs(user_id, limit=limit, offset=offset)

    # Convertir a diccionarios para serializar
    jobs_data = [JobResponse.model_validate(job).model_dump(mode="json") for job in jobs]

    # 4. Guardar en caché (TTL: 2 minutos - las listas cambian frecuentemente)
    await redis_service.set(cache_key, json.dumps(jobs_data), ttl=120)

    # 5. Retornar
    return [JobResponse.model_validate(job) for job in jobs]


@router.post("/users/{user_id}/jobs/invalidate-cache")
async def invalidate_user_jobs_cache(
    user_id: int,
    redis_service: RedisService = Depends(get_redis_service),
):
    """
    Invalida TODOS los cachés de jobs de un usuario.

    Problema: Si tienes diferentes paginaciones, necesitas invalidar todas.
    Solución 1: Usar un patrón de clave y escanear (no implementado aquí)
    Solución 2: Invalidar solo cuando creas/actualizas un job (recomendado)
    """

    # Invalidar las combinaciones más comunes
    deleted = 0
    for limit in [10, 50, 100]:
        for offset in [0, 10, 20, 50, 100]:
            cache_key = f"user:{user_id}:jobs:limit={limit}:offset={offset}"
            if await redis_service.delete(cache_key):
                deleted += 1

    return {
        "user_id": user_id,
        "cache_keys_deleted": deleted,
        "message": f"Invalidated {deleted} cache entries",
    }