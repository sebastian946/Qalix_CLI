# Redis - Guía Rápida de Inicio

## 🚀 Setup Inicial (Solo una vez)

### 1. Instalar Redis en tu máquina

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
```

**Windows:**
- Descarga desde: https://redis.io/download
- O usa Docker: `docker run -d -p 6379:6379 redis`

### 2. Verificar que Redis está corriendo

```bash
redis-cli ping
# Debería responder: PONG
```

### 3. Agregar al archivo `.env`

```env
REDIS_URL=redis://localhost:6379
```

---

## 📖 Cómo Usar Redis en tus Endpoints

### Template Básico

```python
from fastapi import APIRouter, Depends
from core.config import get_redis_service
from services.redis_service import RedisService

router = APIRouter()

@router.get("/mi-endpoint")
async def mi_endpoint(
    redis_service: RedisService = Depends(get_redis_service)
):
    # 1. Intentar obtener del caché
    cached_data = await redis_service.get("mi_clave")
    
    if cached_data:
        return {"data": cached_data, "from": "cache"}
    
    # 2. Si no está en caché, computar/obtener
    data = obtener_datos_de_db()  # Tu lógica aquí
    
    # 3. Guardar en caché (TTL en segundos)
    await redis_service.set("mi_clave", data, ttl=300)  # 5 minutos
    
    return {"data": data, "from": "database"}
```

---

## 🎯 Métodos del RedisService

### 1. `get(key)` - Obtener un valor

```python
value = await redis_service.get("user:123")
# Retorna: el valor como string, o None si no existe
```

### 2. `set(key, value, ttl)` - Guardar un valor

```python
# Sin TTL (permanente hasta que lo borres)
await redis_service.set("config:version", "1.0.0")

# Con TTL (se borra automáticamente después de X segundos)
await redis_service.set("session:abc", "token", ttl=3600)  # 1 hora
```

**TTLs comunes:**
- `ttl=60` - 1 minuto
- `ttl=300` - 5 minutos
- `ttl=3600` - 1 hora
- `ttl=86400` - 1 día

### 3. `delete(key)` - Borrar un valor

```python
success = await redis_service.delete("old_cache")
# Retorna: True si tuvo éxito, False si Redis no disponible
```

### 4. `ping()` - Verificar disponibilidad

```python
if await redis_service.ping():
    print("Redis está disponible")
else:
    print("Redis no está disponible")
```

---

## 🔑 Patrones de Nombres de Claves

Usa nombres descriptivos y consistentes:

```python
# ✅ BIEN - Descriptivo y jerárquico
"user:{user_id}:profile"
"job:{job_id}:result"
"cache:users:list:page={page}"
"rate_limit:user:{user_id}"
"session:{session_id}"

# ❌ MAL - Difícil de entender
"u123"
"data"
"cache1"
```

**Patrón recomendado:** `tipo:identificador:campo`

---

## 💾 Tipos de Datos que Puedes Guardar

### String Simple

```python
await redis_service.set("status", "active")
```

### Números

```python
await redis_service.set("counter", "100")
count = int(await redis_service.get("counter"))
```

### JSON (Objetos/Listas)

```python
import json

# Guardar
data = {"name": "Juan", "age": 30}
await redis_service.set("user:123", json.dumps(data))

# Obtener
cached = await redis_service.get("user:123")
if cached:
    user_data = json.loads(cached)
```

---

## 📊 Ejemplos de Casos de Uso

### 1️⃣ Cachear resultado de un query pesado

```python
@router.get("/analytics")
async def get_analytics(redis_service: RedisService = Depends(get_redis_service)):
    cache_key = "analytics:dashboard"
    
    # Intentar del caché
    cached = await redis_service.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query pesado a la DB
    analytics = compute_expensive_analytics()
    
    # Cachear por 10 minutos
    await redis_service.set(cache_key, json.dumps(analytics), ttl=600)
    
    return analytics
```

### 2️⃣ Cachear por usuario

```python
@router.get("/users/{user_id}/dashboard")
async def get_user_dashboard(
    user_id: int,
    redis_service: RedisService = Depends(get_redis_service)
):
    cache_key = f"user:{user_id}:dashboard"
    
    cached = await redis_service.get(cache_key)
    if cached:
        return json.loads(cached)
    
    dashboard = build_user_dashboard(user_id)
    await redis_service.set(cache_key, json.dumps(dashboard), ttl=300)
    
    return dashboard
```

### 3️⃣ Invalidar caché después de actualizar

```python
@router.put("/jobs/{job_id}")
async def update_job(
    job_id: int,
    data: UpdateJobRequest,
    redis_service: RedisService = Depends(get_redis_service)
):
    # Actualizar en la DB
    job = update_job_in_db(job_id, data)
    
    # ⚠️ IMPORTANTE: Invalidar el caché
    cache_key = f"job:{job_id}:result"
    await redis_service.delete(cache_key)
    
    return job
```

---

## 🐛 Debugging Redis

### Ver todas las claves (en desarrollo)

```bash
redis-cli KEYS "*"
```

### Ver el valor de una clave

```bash
redis-cli GET "job:1:result"
```

### Ver el TTL de una clave

```bash
redis-cli TTL "session:abc"
# -1: sin TTL (permanente)
# -2: la clave no existe
# número positivo: segundos hasta que expire
```

### Borrar todas las claves (¡CUIDADO!)

```bash
redis-cli FLUSHALL
```

### Ver estadísticas

```bash
redis-cli INFO stats
```

---

## ⚠️ Cosas Importantes a Recordar

1. **Redis es volátil**: Los datos están en RAM y se pierden si Redis se reinicia (a menos que configures persistencia)

2. **No guardes datos críticos**: Redis es para caché, no para datos que no puedes perder

3. **Usa TTLs siempre**: Si no pones TTL, los datos quedan para siempre y puedes llenar la memoria

4. **Invalida cuando actualizas**: Si actualizas datos en la DB, borra el caché correspondiente

5. **Redis falla = App sigue funcionando**: El RedisService está configurado con graceful degradation

---

## 🔥 Comandos Redis Útiles (redis-cli)

```bash
# Ver cantidad de claves
redis-cli DBSIZE

# Monitorear en tiempo real
redis-cli MONITOR

# Ver uso de memoria
redis-cli INFO memory

# Verificar conexión
redis-cli PING

# Limpiar base de datos actual
redis-cli FLUSHDB

# Ver configuración
redis-cli CONFIG GET maxmemory
```

---

## 📈 Métricas de Performance

**Sin Redis (directo a DB):**
- Query complejo: ~200-500ms
- Lista de usuarios: ~100-300ms

**Con Redis:**
- Cache HIT: ~1-5ms 🚀
- Cache MISS: igual que sin Redis + 1-2ms (guardar en caché)

**Ahorro típico:** 50-100x más rápido con cache hit

---

## 🎓 Recursos para Aprender Más

- [Redis Documentation](https://redis.io/docs/)
- [Redis Commands](https://redis.io/commands/)
- [Redis University](https://university.redis.com/)
- [Try Redis](https://try.redis.io/)

---

## 🆘 Troubleshooting

### "Connection refused"
```bash
# Verificar que Redis está corriendo
redis-cli ping

# Si no responde, iniciarlo
# macOS: brew services start redis
# Linux: sudo systemctl start redis
```

### "Redis unavailable, skipping cache"
- Esto es normal si Redis no está instalado
- La app sigue funcionando sin caché
- Instala Redis para tener caché

### "TTL no está funcionando"
```bash
# Verificar el TTL de una clave
redis-cli TTL "tu_clave"

# Si retorna -1, la clave no tiene TTL
# Agrégalo al hacer SET
```