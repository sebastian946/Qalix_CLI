# Arquitectura de Redis en Qalix CLI

## 🏗️ Diagrama de Arquitectura Completo

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FASTAPI APPLICATION                           │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    STARTUP (lifespan)                          │ │
│  │                                                                │ │
│  │  1. Lee REDIS_URL del .env                                    │ │
│  │     ├─ redis://localhost:6379                                 │ │
│  │     └─ Variables: host, port, password, db                    │ │
│  │                                                                │ │
│  │  2. Intenta conectar a Redis                                  │ │
│  │     ├─ aioredis.from_url(REDIS_URL)                           │ │
│  │     └─ await redis_client.ping()                              │ │
│  │                                                                │ │
│  │  3. Maneja resultado de conexión                              │ │
│  │     ├─ ✅ Éxito  → RedisService(redis_client)                 │ │
│  │     └─ ❌ Fallo  → RedisService(None) ← Graceful degradation  │ │
│  │                                                                │ │
│  │  4. Guarda en app.state                                       │ │
│  │     ├─ app.state.redis = redis_client                         │ │
│  │     └─ app.state.redis_service = RedisService(...)            │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                 ↓                                    │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │                    TUS ENDPOINTS                               │ │
│  │                                                                │ │
│  │  @router.get("/jobs/{job_id}")                                │ │
│  │  async def get_job(                                           │ │
│  │      job_id: int,                                             │ │
│  │      redis: RedisService = Depends(get_redis_service) ◄──────┼─┼─┐
│  │  ):                                                           │ │ │
│  │      # Tu código usa redis aquí                              │ │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                 ↓                                    │ │
└──────────────────────────────────────────────────────────────────────┘ │
                                  ↓                                      │
        ┌─────────────────────────────────────────────────┐             │
        │         REDIS SERVICE (redis_service.py)        │             │
        │                                                 │             │
        │  ┌───────────────────────────────────────────┐ │             │
        │  │  async def get(key: str)                  │ │             │
        │  │  ┌─────────────────────────────────────┐ │ │             │
        │  │  │ 1. Check if redis available         │ │ │             │
        │  │  │ 2. Try: await client.get(key)       │ │ │             │
        │  │  │ 3. Except: return None              │ │ │             │
        │  │  └─────────────────────────────────────┘ │ │             │
        │  └───────────────────────────────────────────┘ │             │
        │                                                 │             │
        │  ┌───────────────────────────────────────────┐ │             │
        │  │  async def set(key, value, ttl)           │ │             │
        │  │  ┌─────────────────────────────────────┐ │ │             │
        │  │  │ 1. Check if redis available         │ │ │             │
        │  │  │ 2. if ttl:                          │ │ │             │
        │  │  │      await client.setex(key, ttl, v)│ │ │             │
        │  │  │    else:                            │ │ │             │
        │  │  │      await client.set(key, value)   │ │ │             │
        │  │  │ 3. Except: return False             │ │ │             │
        │  │  └─────────────────────────────────────┘ │ │             │
        │  └───────────────────────────────────────────┘ │             │
        │                                                 │             │
        │  ┌───────────────────────────────────────────┐ │             │
        │  │  Graceful Degradation:                    │ │             │
        │  │  • _available flag                        │ │             │
        │  │  • Auto-retry disabled on error           │ │             │
        │  │  • Logging (INFO/WARNING/DEBUG)           │ │             │
        │  └───────────────────────────────────────────┘ │             │
        └─────────────────────────────────────────────────┘             │
                                  ↓                                      │
        ┌─────────────────────────────────────────────────┐             │
        │              REDIS SERVER (puerto 6379)         │ ◄───────────┘
        │                                                 │
        │  ┌───────────────────────────────────────────┐ │
        │  │         MEMORY (RAM)                      │ │
        │  │                                           │ │
        │  │  Hash Table (Diccionario Key-Value):     │ │
        │  │  ┌─────────────────────────────────────┐ │ │
        │  │  │ "job:123:result"  → "test passed"   │ │ │
        │  │  │ TTL: 600 segundos                   │ │ │
        │  │  ├─────────────────────────────────────┤ │ │
        │  │  │ "user:1:jobs:..."  → "[{...}]"      │ │ │
        │  │  │ TTL: 120 segundos                   │ │ │
        │  │  ├─────────────────────────────────────┤ │ │
        │  │  │ "rate_limit:user:1" → "5"           │ │ │
        │  │  │ TTL: 60 segundos                    │ │ │
        │  │  └─────────────────────────────────────┘ │ │
        │  │                                           │ │
        │  │  • Expira claves automáticamente (TTL)   │ │
        │  │  • LRU eviction si se llena la memoria   │ │
        │  │  • Datos volátiles (se pierden al reinicio) │
        │  └───────────────────────────────────────────┘ │
        └─────────────────────────────────────────────────┘
```

---

## 📊 Flujo de una Petición con Caché

```
CLIENTE                 ENDPOINT                REDIS SERVICE         REDIS         DB
  │                        │                         │                 │            │
  │  GET /jobs/123/result  │                         │                 │            │
  ├────────────────────────►                         │                 │            │
  │                        │                         │                 │            │
  │                        │  get("job:123:result")  │                 │            │
  │                        ├─────────────────────────►                 │            │
  │                        │                         │                 │            │
  │                        │                         │  GET job:123... │            │
  │                        │                         ├─────────────────►            │
  │                        │                         │                 │            │
  │                        │                         │ ◄─────────────┐ │            │
  │                        │                         │   "cached_val"  │            │
  │                        │                         │                 │            │
  │                        │ ◄─────────────────────┐ │                 │            │
  │                        │    "cached_val"         │                 │            │
  │                        │                         │                 │            │
  │ ◄──────────────────────┤                         │                 │            │
  │  {result: "...",       │                         │                 │            │
  │   source: "cache"}     │                         │                 │            │
  │                        │                         │                 │            │
                         🎯 Cache HIT - 1-5ms total


CLIENTE                 ENDPOINT                REDIS SERVICE         REDIS         DB
  │                        │                         │                 │            │
  │  GET /jobs/456/result  │                         │                 │            │
  ├────────────────────────►                         │                 │            │
  │                        │                         │                 │            │
  │                        │  get("job:456:result")  │                 │            │
  │                        ├─────────────────────────►                 │            │
  │                        │                         │                 │            │
  │                        │                         │  GET job:456... │            │
  │                        │                         ├─────────────────►            │
  │                        │                         │                 │            │
  │                        │                         │ ◄───────────────┤            │
  │                        │                         │      None        │            │
  │                        │                         │                 │            │
  │                        │ ◄─────────────────────┐ │                 │            │
  │                        │        None             │                 │            │
  │                        │                         │                 │            │
  │                        │                         │                 │  SELECT... │
  │                        ├──────────────────────────────────────────────────────────►
  │                        │                         │                 │            │
  │                        │ ◄──────────────────────────────────────────────────────┤
  │                        │                         │                 │  job_data  │
  │                        │                         │                 │            │
  │                        │ set("job:456...", data, 600)              │            │
  │                        ├─────────────────────────►                 │            │
  │                        │                         │                 │            │
  │                        │                         │  SETEX 600...   │            │
  │                        │                         ├─────────────────►            │
  │                        │                         │                 │            │
  │                        │                         │ ◄───────────────┤            │
  │                        │                         │       OK         │            │
  │                        │                         │                 │            │
  │ ◄──────────────────────┤                         │                 │            │
  │  {result: "...",       │                         │                 │            │
  │   source: "database"}  │                         │                 │            │
  │                        │                         │                 │            │
                        ⚠️ Cache MISS - 100-300ms total
                         (Primera vez, siguiente será CACHE HIT)
```

---

## 🔄 Ciclo de Vida de un Dato en Redis

```
┌──────────────────────────────────────────────────────────────┐
│                    TIMELINE                                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  T=0s   │  SET job:123:result "test passed" EX 600         │
│         │  ┌──────────────────────────────────────────┐    │
│         │  │  Redis almacena en RAM:                  │    │
│         │  │  Key: "job:123:result"                   │    │
│         │  │  Value: "test passed"                    │    │
│         │  │  Expires: T + 600s (10 minutos)          │    │
│         │  └──────────────────────────────────────────┘    │
│         │                                                   │
│  T=5s   │  GET job:123:result                              │
│         │  ← "test passed" ✅ (Cache HIT)                  │
│         │                                                   │
│  T=30s  │  GET job:123:result                              │
│         │  ← "test passed" ✅ (Cache HIT)                  │
│         │                                                   │
│ T=100s  │  GET job:123:result                              │
│         │  ← "test passed" ✅ (Cache HIT)                  │
│         │                                                   │
│ T=599s  │  GET job:123:result                              │
│         │  ← "test passed" ✅ (Cache HIT - 1 segundo para expirar)│
│         │                                                   │
│ T=600s  │  ⏰ TTL expirado - Redis borra automáticamente   │
│         │  ┌──────────────────────────────────────────┐    │
│         │  │  Key deleted from memory                 │    │
│         │  └──────────────────────────────────────────┘    │
│         │                                                   │
│ T=601s  │  GET job:123:result                              │
│         │  ← None ❌ (Cache MISS - clave expirada)         │
│         │                                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎛️ Estados de Redis en la Aplicación

```
┌─────────────────────────────────────────────────────────────┐
│              ESTADO 1: Redis Disponible ✅                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  RedisService._available = True                            │
│                                                             │
│  • get()    → Busca en Redis                               │
│  • set()    → Guarda en Redis                              │
│  • delete() → Borra de Redis                               │
│  • ping()   → True                                          │
│                                                             │
│  Logging: INFO "Redis connected successfully"              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│         ESTADO 2: Redis No Disponible al Inicio ⚠️          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  RedisService._available = False                           │
│  RedisService.client = None                                │
│                                                             │
│  • get()    → Retorna None inmediatamente                  │
│  • set()    → Retorna False inmediatamente                 │
│  • delete() → Retorna False inmediatamente                 │
│  • ping()   → False                                         │
│                                                             │
│  Logging: WARNING "Redis connection failed. Running        │
│                     without cache."                         │
│                                                             │
│  ✅ LA APLICACIÓN SIGUE FUNCIONANDO (sin caché)            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│       ESTADO 3: Redis Falla Durante Operación 🔴            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Inicialmente: _available = True                           │
│                                                             │
│  1. Llamas get("key")                                      │
│  2. Intenta: await client.get("key")                       │
│  3. Exception: ConnectionError                             │
│  4. Cambia: _available = False                             │
│  5. Retorna: None                                          │
│                                                             │
│  Logging: WARNING "Redis GET error for key 'key':          │
│                     Connection timeout"                     │
│                                                             │
│  De ahora en adelante: Se comporta como ESTADO 2           │
│  (No intenta reconectar automáticamente)                   │
│                                                             │
│  ✅ LA APLICACIÓN SIGUE FUNCIONANDO (sin caché)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Comandos Útiles para Inspeccionar Redis

```bash
# Ver TODAS las claves
redis-cli KEYS "*"

# Buscar claves con patrón
redis-cli KEYS "job:*"
redis-cli KEYS "user:123:*"

# Ver valor de una clave
redis-cli GET "job:123:result"

# Ver TTL restante (en segundos)
redis-cli TTL "job:123:result"
# -1: sin TTL
# -2: no existe
# 580: faltan 580 segundos para expirar

# Ver tipo de dato
redis-cli TYPE "job:123:result"

# Borrar una clave específica
redis-cli DEL "job:123:result"

# Ver cuántas claves hay
redis-cli DBSIZE

# Ver uso de memoria
redis-cli INFO memory | grep used_memory_human

# Monitorear en tiempo real (todas las operaciones)
redis-cli MONITOR

# Limpiar TODA la base de datos (¡CUIDADO!)
redis-cli FLUSHDB
```

---

## 📈 Optimizaciones y Best Practices

### 1. Estructura de Claves

```python
# ✅ BIEN - Jerárquico y descriptivo
"user:{user_id}:profile"
"job:{job_id}:result"
"cache:analytics:daily:{date}"
"rate_limit:api:{endpoint}:user:{user_id}"

# ❌ MAL - Plano y ambiguo
"user123"
"result"
"data1"
```

### 2. TTLs Apropiados

```python
# Datos que cambian frecuentemente
await redis_service.set("active_users", data, ttl=30)  # 30 segundos

# Resultados de queries
await redis_service.set("user:123:jobs", data, ttl=300)  # 5 minutos

# Datos casi estáticos
await redis_service.set("config:version", data, ttl=3600)  # 1 hora

# Sesiones
await redis_service.set("session:abc", token, ttl=86400)  # 1 día
```

### 3. Invalidación Proactiva

```python
# Cuando actualizas datos, borra el caché
@router.put("/jobs/{job_id}")
async def update_job(job_id: int, ...):
    # Actualizar DB
    job = await update_in_db(job_id)
    
    # Invalidar caché
    await redis_service.delete(f"job:{job_id}:result")
    await redis_service.delete(f"user:{job.user_id}:jobs:...")
    
    return job
```