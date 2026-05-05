"""
EJEMPLO COMPLETO END-TO-END: Cómo usar Redis en tu endpoint

Este archivo muestra un flujo completo de cómo integrar Redis
en tus endpoints de forma práctica y real.
"""

import json
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_db, get_redis_service
from models.model import Job, Status
from schemas.schemas import CreateJobRequest, CreateJobResponse, JobResponse
from services.jobs_services import JobService
from services.redis_service import RedisService

router = APIRouter()


# ============================================================================
# EJEMPLO 1: GET con Caché Simple
# ============================================================================


@router.get("/jobs/{job_id}/cached")
async def get_job_with_cache(
    job_id: int,
    redis_service: RedisService = Depends(get_redis_service),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """
    Endpoint que demuestra el patrón básico de caché:
    1. Intentar obtener del caché
    2. Si no está, obtener de DB
    3. Guardar en caché para la próxima vez
    """

    # PASO 1: Definir clave de caché
    # Patrón: tipo:id:campo
    cache_key = f"job:{job_id}:full"

    # PASO 2: Intentar obtener del caché
    print(f"🔍 Buscando en caché: {cache_key}")
    cached_data = await redis_service.get(cache_key)

    if cached_data:
        # ✅ CACHE HIT - Respuesta ultra rápida (1-5ms)
        print(f"✅ Cache HIT para {cache_key}")
        job_dict = json.loads(cached_data)
        return JobResponse(**job_dict)

    # ❌ CACHE MISS - Obtener de DB
    print(f"❌ Cache MISS para {cache_key}, consultando DB...")

    # PASO 3: Obtener de la base de datos
    job_service = JobService(db)
    job = await job_service.get_job(job_id, user_id=1)  # TODO: user_id real

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # PASO 4: Convertir a formato serializable
    job_response = JobResponse.model_validate(job)
    job_dict = job_response.model_dump(mode="json")

    # PASO 5: Guardar en caché
    # TTL: 10 minutos para jobs completados, 1 minuto para otros
    ttl = 600 if job.status == Status.COMPLETED else 60

    success = await redis_service.set(cache_key, json.dumps(job_dict), ttl=ttl)

    if success:
        print(f"💾 Guardado en caché con TTL={ttl}s")
    else:
        print(f"⚠️  Redis no disponible, no se guardó en caché")

    return job_response


# ============================================================================
# EJEMPLO 2: POST con Invalidación de Caché
# ============================================================================


@router.post("/jobs/cached", status_code=202)
async def create_job_with_cache_invalidation(
    job_data: CreateJobRequest,
    background_tasks: BackgroundTasks,
    redis_service: RedisService = Depends(get_redis_service),
    db: AsyncSession = Depends(get_db),
) -> CreateJobResponse:
    """
    Cuando creas un job nuevo, debes invalidar el caché de la lista de jobs.
    """

    user_id = 1  # TODO: Obtener del token

    # Crear el job
    job_service = JobService(db)
    job = await job_service.create_job(user_id, job_data)

    # ⚠️ IMPORTANTE: Invalidar caché de listas de jobs
    # Porque ahora hay un nuevo job que no está en las listas cacheadas
    await invalidate_user_jobs_cache(user_id, redis_service)

    # Ejecutar análisis en background
    background_tasks.add_task(job_service.run_analysis, job.id)

    return CreateJobResponse(job_id=job.id)


async def invalidate_user_jobs_cache(user_id: int, redis_service: RedisService):
    """Helper para invalidar todos los cachés relacionados con jobs de un usuario."""
    # Invalidar diferentes variaciones de paginación
    for limit in [10, 50, 100]:
        for offset in [0, 10, 20, 50]:
            cache_key = f"user:{user_id}:jobs:limit={limit}:offset={offset}"
            await redis_service.delete(cache_key)

    print(f"🗑️  Caché de jobs invalidado para user_id={user_id}")


# ============================================================================
# EJEMPLO 3: Lista con Caché (con Paginación)
# ============================================================================


@router.get("/users/{user_id}/jobs/cached")
async def get_user_jobs_cached(
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    redis_service: RedisService = Depends(get_redis_service),
    db: AsyncSession = Depends(get_db),
) -> List[JobResponse]:
    """
    Cachear listas requiere:
    1. Incluir parámetros de paginación en la clave
    2. Serializar a JSON (porque son objetos complejos)
    3. TTL más corto (listas cambian más frecuentemente)
    """

    # PASO 1: Clave incluye paginación
    cache_key = f"user:{user_id}:jobs:limit={limit}:offset={offset}"

    # PASO 2: Intentar del caché
    cached_data = await redis_service.get(cache_key)

    if cached_data:
        print(f"✅ Cache HIT - Lista de jobs para user {user_id}")
        jobs_list = json.loads(cached_data)
        return [JobResponse(**job) for job in jobs_list]

    # PASO 3: Obtener de DB
    print(f"❌ Cache MISS - Consultando DB para user {user_id}")
    job_service = JobService(db)
    jobs = await job_service.get_all_jobs(user_id, limit=limit, offset=offset)

    # PASO 4: Serializar
    jobs_list = [
        JobResponse.model_validate(job).model_dump(mode="json") for job in jobs
    ]

    # PASO 5: Guardar en caché con TTL corto (listas cambian frecuentemente)
    await redis_service.set(cache_key, json.dumps(jobs_list), ttl=120)  # 2 minutos

    return [JobResponse(**job) for job in jobs_list]


# ============================================================================
# EJEMPLO 4: Estadísticas Agregadas (Query Pesado)
# ============================================================================


@router.get("/analytics/dashboard/{user_id}")
async def get_user_analytics(
    user_id: int,
    redis_service: RedisService = Depends(get_redis_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Para queries pesados (muchos joins, agregaciones),
    el caché puede ahorrar MUCHÍSIMO tiempo.
    """

    cache_key = f"analytics:dashboard:user:{user_id}"

    # Intentar del caché
    cached = await redis_service.get(cache_key)
    if cached:
        analytics = json.loads(cached)
        analytics["cached"] = True
        analytics["cached_at"] = "just now"
        return analytics

    # Query pesado a la DB (simulado)
    print(f"🔨 Ejecutando query pesado para analytics de user {user_id}...")

    # En la realidad, esto sería un query complejo
    # SELECT COUNT(*), AVG(...), etc. con múltiples joins
    from sqlalchemy import func, select

    result = await db.execute(
        select(
            func.count(Job.id).label("total_jobs"),
            func.sum(
                func.case((Job.status == Status.COMPLETED, 1), else_=0)
            ).label("completed_jobs"),
            func.sum(
                func.case((Job.status == Status.FAILED, 1), else_=0)
            ).label("failed_jobs"),
        ).where(Job.user_id == user_id)
    )

    row = result.first()

    analytics = {
        "user_id": user_id,
        "total_jobs": row.total_jobs or 0,
        "completed_jobs": row.completed_jobs or 0,
        "failed_jobs": row.failed_jobs or 0,
        "success_rate": (
            (row.completed_jobs / row.total_jobs * 100)
            if row.total_jobs > 0
            else 0
        ),
        "generated_at": datetime.utcnow().isoformat(),
        "cached": False,
    }

    # Guardar en caché por 5 minutos
    await redis_service.set(cache_key, json.dumps(analytics), ttl=300)

    return analytics


# ============================================================================
# EJEMPLO 5: Rate Limiting
# ============================================================================


@router.post("/jobs/rate-limited")
async def create_job_rate_limited(
    job_data: CreateJobRequest,
    redis_service: RedisService = Depends(get_redis_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Usa Redis para limitar cuántos jobs puede crear un usuario por minuto.
    """

    user_id = 1  # TODO: Obtener del token

    # Verificar rate limit
    rate_key = f"rate_limit:create_job:user:{user_id}"
    current_count = await redis_service.get(rate_key)

    MAX_JOBS_PER_MINUTE = 10

    if current_count is None:
        # Primera petición en esta ventana
        await redis_service.set(rate_key, "1", ttl=60)
    else:
        count = int(current_count)

        if count >= MAX_JOBS_PER_MINUTE:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Max {MAX_JOBS_PER_MINUTE} jobs per minute.",
                headers={"Retry-After": "60"},
            )

        # Incrementar contador
        await redis_service.set(rate_key, str(count + 1), ttl=60)

    # Crear job normalmente
    job_service = JobService(db)
    job = await job_service.create_job(user_id, job_data)

    return CreateJobResponse(job_id=job.id)


# ============================================================================
# EJEMPLO 6: Endpoint de Utilidades (Debugging)
# ============================================================================


@router.get("/cache/stats")
async def get_cache_stats(redis_service: RedisService = Depends(get_redis_service)):
    """
    Endpoint útil para ver el estado del caché en desarrollo.
    """

    is_available = await redis_service.ping()

    return {
        "redis_available": is_available,
        "message": (
            "Redis is operational" if is_available else "Redis is not available"
        ),
        "note": (
            "Cache is working"
            if is_available
            else "Application running without cache (graceful degradation)"
        ),
    }


@router.delete("/cache/flush/{pattern}")
async def flush_cache_pattern(
    pattern: str, redis_service: RedisService = Depends(get_redis_service)
):
    """
    ⚠️ USAR SOLO EN DESARROLLO
    Borra cachés que coincidan con un patrón.

    Ejemplos:
    - /cache/flush/job:123:* → Borra todos los cachés del job 123
    - /cache/flush/user:1:* → Borra todos los cachés del user 1
    """

    # En un sistema real, usarías SCAN para encontrar claves por patrón
    # Aquí simplificamos asumiendo que conoces las claves exactas

    deleted = 0

    # Ejemplo: Si el patrón es "job:123:*"
    if pattern.startswith("job:") and pattern.endswith(":*"):
        job_id = pattern.split(":")[1]
        keys_to_delete = [
            f"job:{job_id}:full",
            f"job:{job_id}:result",
        ]

        for key in keys_to_delete:
            if await redis_service.delete(key):
                deleted += 1

    return {
        "pattern": pattern,
        "keys_deleted": deleted,
        "message": f"Deleted {deleted} cache entries",
    }


# ============================================================================
# RESUMEN DE PATRONES
# ============================================================================

"""
PATRONES PRINCIPALES:

1. GET Simple:
   cache_key = f"tipo:{id}"
   cached = await redis.get(cache_key)
   if cached: return cached
   data = get_from_db()
   await redis.set(cache_key, data, ttl=300)
   return data

2. GET Lista:
   cache_key = f"tipo:{id}:lista:limit={l}:offset={o}"
   cached = await redis.get(cache_key)
   if cached: return json.loads(cached)
   data = get_list_from_db()
   await redis.set(cache_key, json.dumps(data), ttl=120)
   return data

3. POST/PUT/DELETE (Invalidación):
   update_in_db()
   await redis.delete(f"tipo:{id}")
   await redis.delete(f"user:{user_id}:lista:*")  # Invalidar listas

4. Rate Limiting:
   count = await redis.get(f"rate:{user_id}")
   if count >= MAX: raise 429
   await redis.set(f"rate:{user_id}", count+1, ttl=60)

5. Queries Pesados:
   cache_key = f"analytics:tipo:{id}"
   cached = await redis.get(cache_key)
   if cached: return json.loads(cached)
   heavy_query = expensive_computation()
   await redis.set(cache_key, json.dumps(heavy_query), ttl=600)
   return heavy_query

RECUERDA:
✅ Usa TTLs apropiados
✅ Invalida al actualizar
✅ Serializa objetos complejos con JSON
✅ Nombres de claves descriptivos
✅ Graceful degradation automático
"""