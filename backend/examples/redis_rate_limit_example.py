"""
Ejemplo: Usar Redis para Rate Limiting
Limita cuántas veces un usuario puede hacer una acción en un período de tiempo
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_db, get_redis_service
from services.redis_service import RedisService
from schemas.schemas import CreateJobRequest, CreateJobResponse

router = APIRouter()


async def check_rate_limit(
    user_id: int,
    redis_service: RedisService,
    max_requests: int = 10,
    window_seconds: int = 60,
) -> bool:
    """
    Verifica si el usuario ha excedido el límite de peticiones.

    Args:
        user_id: ID del usuario
        redis_service: Servicio de Redis
        max_requests: Máximo de peticiones permitidas
        window_seconds: Ventana de tiempo en segundos

    Returns:
        True si puede continuar, False si excedió el límite
    """
    # Clave para tracking
    rate_key = f"rate_limit:user:{user_id}"

    # Obtener el contador actual
    current_count = await redis_service.get(rate_key)

    if current_count is None:
        # Primera petición en esta ventana
        # Guardar con el TTL igual a la ventana
        await redis_service.set(rate_key, "1", ttl=window_seconds)
        return True

    # Convertir a entero
    count = int(current_count)

    if count >= max_requests:
        # Excedió el límite
        return False

    # Incrementar el contador
    # Nota: En producción real usarías INCR de Redis que es atómico
    # Aquí lo hacemos simple
    await redis_service.set(rate_key, str(count + 1), ttl=window_seconds)
    return True


@router.post("/jobs-with-rate-limit")
async def create_job_with_rate_limit(
    job_data: CreateJobRequest,
    redis_service: RedisService = Depends(get_redis_service),
    db: AsyncSession = Depends(get_db),
) -> CreateJobResponse:
    """
    Endpoint para crear jobs con rate limiting.
    Máximo 10 jobs por minuto por usuario.
    """
    user_id = 1  # TODO: Obtener del token de autenticación

    # Verificar rate limit
    can_proceed = await check_rate_limit(
        user_id=user_id,
        redis_service=redis_service,
        max_requests=10,  # 10 jobs
        window_seconds=60,  # por minuto
    )

    if not can_proceed:
        raise HTTPException(
            status_code=429,  # Too Many Requests
            detail="Rate limit exceeded. Maximum 10 jobs per minute.",
            headers={"Retry-After": "60"},
        )

    # Crear el job normalmente
    from services.jobs_services import JobService

    job_service = JobService(db)
    job = await job_service.create_job(user_id, job_data)

    return CreateJobResponse(job_id=job.id)


@router.get("/rate-limit/status/{user_id}")
async def get_rate_limit_status(
    user_id: int,
    redis_service: RedisService = Depends(get_redis_service),
):
    """
    Consulta el estado del rate limit de un usuario.
    """
    rate_key = f"rate_limit:user:{user_id}"
    current_count = await redis_service.get(rate_key)

    if current_count is None:
        return {
            "user_id": user_id,
            "requests_made": 0,
            "max_requests": 10,
            "remaining": 10,
            "window_seconds": 60,
            "reset_in": 60,
        }

    count = int(current_count)

    return {
        "user_id": user_id,
        "requests_made": count,
        "max_requests": 10,
        "remaining": max(0, 10 - count),
        "window_seconds": 60,
        "status": "limited" if count >= 10 else "ok",
    }