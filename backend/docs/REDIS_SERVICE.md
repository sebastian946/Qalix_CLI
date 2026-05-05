# RedisService - Configuración y Uso

## Descripción

El `RedisService` proporciona una abstracción centralizada para interactuar con Redis, implementando **graceful degradation** para que la aplicación funcione correctamente incluso cuando Redis no está disponible.

## Características

✅ **Inicialización centralizada** desde `REDIS_URL` en el archivo `.env`  
✅ **Helpers para get/set/delete** con manejo de errores  
✅ **Graceful degradation** - la aplicación funciona sin caché si Redis no está disponible  
✅ **Logging automático** de errores y estado de conexión  
✅ **Inyección de dependencias** compatible con FastAPI  

## Configuración

### Variables de Entorno

Agrega la URL de Redis en tu archivo `.env`:

```env
REDIS_URL=redis://localhost:6379
```

### Inicialización

El cliente Redis se inicializa automáticamente en el `lifespan` de la aplicación FastAPI:

```python
# En core/config.py - ya configurado
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}. Running without cache.")
        redis_client = None

    app.state.redis_service = RedisService(redis_client)
    yield
    
    if redis_client:
        await redis_client.close()
```

## Uso en Endpoints

### Inyección de Dependencias

```python
from fastapi import APIRouter, Depends
from core.config import get_redis_service
from services.redis_service import RedisService

router = APIRouter()

@router.get("/my-endpoint")
async def my_endpoint(redis_service: RedisService = Depends(get_redis_service)):
    # Usa el servicio aquí
    pass
```

### Métodos Disponibles

#### 1. `get(key: str) -> Optional[str]`

Obtiene un valor del caché. Devuelve `None` si la clave no existe o Redis no está disponible.

```python
cached_data = await redis_service.get("user:123")
if cached_data:
    return {"source": "cache", "data": cached_data}
```

#### 2. `set(key: str, value: Any, ttl: Optional[int] = None) -> bool`

Guarda un valor en el caché con TTL opcional (en segundos). Devuelve `True` si tuvo éxito.

```python
# Sin TTL (permanente)
success = await redis_service.set("config:version", "1.0.0")

# Con TTL de 5 minutos
success = await redis_service.set("session:abc123", user_data, ttl=300)
```

#### 3. `delete(key: str) -> bool`

Elimina una clave del caché. Devuelve `True` si tuvo éxito.

```python
success = await redis_service.delete("cache:outdated_key")
```

#### 4. `ping() -> bool`

Verifica si Redis está disponible. Devuelve `True` si responde.

```python
if await redis_service.ping():
    logger.info("Redis is healthy")
```

#### 5. `close() -> None`

Cierra la conexión de Redis (se llama automáticamente en el `lifespan`).

```python
await redis_service.close()
```

## Ejemplo Completo

```python
from fastapi import APIRouter, Depends
from core.config import get_redis_service
from services.redis_service import RedisService

router = APIRouter()

@router.get("/jobs/{job_id}")
async def get_job(
    job_id: int,
    redis_service: RedisService = Depends(get_redis_service)
):
    # Intentar obtener del caché
    cache_key = f"job:{job_id}"
    cached_job = await redis_service.get(cache_key)
    
    if cached_job:
        return {"source": "cache", "job": cached_job}
    
    # Si no está en caché, consultar la DB
    job = await get_job_from_db(job_id)
    
    # Guardar en caché por 10 minutos
    await redis_service.set(cache_key, job, ttl=600)
    
    return {"source": "database", "job": job}
```

## Graceful Degradation

El servicio está diseñado para degradarse gracefully:

1. **Redis no disponible al inicio**: La aplicación arranca normalmente, pero sin caché
2. **Redis falla durante operación**: Los métodos devuelven `None` o `False` y loguean el error
3. **Estado de disponibilidad**: Se rastrea internamente y se actualiza con `ping()`

```python
# Ejemplo de patrón con fallback
cached_result = await redis_service.get("expensive_computation")

if cached_result:
    result = cached_result
else:
    # Computar sin importar si Redis está o no disponible
    result = expensive_computation()
    
    # Intentar guardar en caché (falla silenciosamente si Redis no está)
    await redis_service.set("expensive_computation", result, ttl=3600)

return result
```

## Testing

Para tests unitarios, puedes mocear el `RedisService`:

```python
from unittest.mock import AsyncMock
import pytest
from services.redis_service import RedisService

@pytest.fixture
def mock_redis_service():
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)
    mock_redis.get = AsyncMock(return_value="cached_value")
    return RedisService(mock_redis)

@pytest.mark.asyncio
async def test_with_cache(mock_redis_service):
    result = await mock_redis_service.get("test_key")
    assert result == "cached_value"
```

## Logging

El servicio incluye logging automático:

- **INFO**: Conexión exitosa, cierre de conexión
- **WARNING**: Fallos de conexión, errores en operaciones (con graceful degradation)
- **DEBUG**: Cache miss cuando Redis no está disponible

```python
# Logs de ejemplo
INFO: Redis connected successfully
WARNING: Redis connection failed: Connection refused. Running without cache.
DEBUG: Redis unavailable, cache miss for key: user:123
WARNING: Redis GET error for key 'user:123': Connection timeout
```

## Mejores Prácticas

1. **Usa TTL apropiados**: Define tiempos de expiración según la naturaleza de los datos
2. **Prefijos de claves**: Usa patrones como `job:{id}`, `user:{id}:sessions` para organizar
3. **No dependas de Redis**: Diseña tu código para funcionar sin caché
4. **Monitorea disponibilidad**: Usa el endpoint `/health` para monitorear el estado de Redis
5. **Invalidación explícita**: Usa `delete()` cuando actualices datos que están en caché

## Ver También

- [Ejemplo de uso](../examples/redis_usage.py)
- [Tests unitarios](../test/unit/test_redis_service.py)
- [Documentación de redis-py](https://redis-py.readthedocs.io/)