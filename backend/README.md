# Qalix — Backend

**QA Intelligence Platform** — AI-powered SaaS for automated software testing.

Qalix helps teams generate, execute, and maintain test suites using AI agents, reducing manual QA effort and catching regressions faster.

---

## Tech Stack

| Layer       | Technology                                  |
| ----------- | ------------------------------------------- |
| API         | FastAPI + Uvicorn                           |
| Database    | PostgreSQL (async via asyncpg + SQLAlchemy) |
| Migrations  | Alembic                                     |
| AI Agents   | LangGraph + LangChain                       |
| LLM         | Anthropic Claude Haiku                      |
| Vector DB   | ChromaDB                                    |
| Cache       | Redis                                       |
| Validation  | Pydantic + pydantic-settings                |
| Logging     | structlog (JSON en prod, colores en dev)    |

---

## Project Structure

```
backend/
├── .github/workflows/pipeline.yml  # CI: ruff → mypy → pytest (coverage ≥ 70%)
├── agents/
│   ├── prompt_sanitizer.py  # Validación: extensión, prompt injection, tamaño
│   ├── qa_agent.py          # LangChain: generación de tests via Claude
│   └── node_agent.py        # LangGraph: análisis → generación → revisión
├── chains/                  # LangChain pipelines
├── core/
│   ├── config.py            # Settings, SQLAlchemy, Redis, LLM
│   └── logger.py            # Logging estructurado + middleware de requests
├── models/model.py          # SQLAlchemy: User, Job, JobStep, Subscription, Integration
├── alembic/                 # Migraciones de base de datos
├── routes/
│   ├── health_routes.py     # GET /health
│   ├── jobs_routes.py       # POST/GET /jobs
│   └── user_routes.py       # POST /register_user
├── schemas/schemas.py       # Pydantic schemas + validaciones
├── services/
│   ├── jobs_services.py     # Lógica de jobs con cache
│   ├── rate_limit_service.py
│   └── redis_service.py     # RedisService con degradación graceful
├── test/
│   ├── conftest.py
│   └── unit/
├── docker-compose.yaml
├── Dockerfile
├── pyproject.toml
└── main.py
```

---

## Levantando la aplicación

### Opción A — Docker Compose (recomendado)

Levanta el backend, PostgreSQL y Redis con un solo comando:

```bash
docker compose up --build
```

| Servicio | URL local        | Descripción                      |
| -------- | ---------------- | -------------------------------- |
| backend  | localhost:8000   | FastAPI con hot reload           |
| postgres | localhost:5433   | PostgreSQL 16                    |
| redis    | localhost:6379   | Redis 7                          |

El backend espera que PostgreSQL pase su healthcheck antes de arrancar. El código fuente está montado como volumen — cualquier cambio en `.py` recarga el servidor sin reconstruir la imagen.

Para resetear todo desde cero (borra volúmenes):

```bash
docker compose down -v
docker compose up --build
```

---

### Opción B — Local (sin Docker para el backend)

Requiere PostgreSQL y Redis corriendo (puedes levantarlos solo con Docker):

```bash
# 1. Instalar dependencias
uv sync --all-groups

# 2. Levantar solo los servicios de infraestructura
docker compose up db redis -d

# 3. Levantar el servidor
uv run uvicorn main:app --reload --port 8000
```

---

## Variables de entorno

Crea o edita el archivo `.env` en la raíz del proyecto:

```env
# LLM
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Base de datos (puerto 5433 para no chocar con Postgres local)
DATABASE_URL=postgresql+asyncpg://user123:password123@localhost:5433/qalix_db

# Redis
REDIS_URL=redis://localhost:6379

# Entorno: DEV (logs con colores) o PROD (logs en JSON)
ENVIRONMENT=DEV

# Nivel de log: DEBUG, INFO, WARNING, ERROR
LOG_LEVEL=INFO

# TTL del cache en segundos (default: 1 hora)
CACHE_TTL=3600
```

> El `ANTHROPIC_API_KEY` es obligatorio. Si falta, la app falla al arrancar con un error claro de Pydantic.

---

## Base de datos

### 1. Correr migraciones

Las migraciones crean todas las tablas. Deben correrse **antes de usar cualquier endpoint**:

```bash
# Con Docker activo
uv run alembic upgrade head

# Ver el estado actual
uv run alembic current

# Ver el historial de migraciones
uv run alembic history
```

Otros comandos útiles:

```bash
# Generar una nueva migración desde cambios en los modelos
uv run alembic revision --autogenerate -m "descripcion"

# Revertir una migración
uv run alembic downgrade -1
```

### Tablas disponibles

| Tabla           | Modelo         | Descripción                                         |
| --------------- | -------------- | --------------------------------------------------- |
| `users`         | `User`         | Usuarios con plan y contador mensual de uso         |
| `jobs`          | `Job`          | Jobs de análisis enviados por usuarios              |
| `jobs_steps`    | `JobStep`      | Pasos individuales del agente LangGraph por job     |
| `subscriptions` | `Subscription` | Suscripciones activas de Stripe                     |
| `integrations`  | `Integration`  | Integraciones con Jira, Slack, GitHub               |

---

### 2. Agregar datos iniciales (seed)

> **Importante:** Los endpoints de jobs usan `user_id = 1` hardcodeado hasta que se implemente autenticación con Clerk. Si no existe ese usuario en la DB, los endpoints devuelven `404 User not found`.

#### Conectarse a la base de datos

```bash
docker exec -it qalix_postgres psql -U user123 -d qalix_db
```

#### Insertar un usuario de prueba

```sql
INSERT INTO users (clerk_id, email, plan, job_used_this_month, created_at, updated_at)
VALUES (
  'clerk_test_001',
  'test@qalix.com',
  'free',
  0,
  NOW(),
  NOW()
);
```

Verificar que quedó creado con `id = 1`:

```sql
SELECT id, email, plan, job_used_this_month FROM users;
```

#### Consultas útiles durante el desarrollo

```sql
-- Ver todos los jobs con su estado
SELECT id, filename, status, created_at, completed_at FROM jobs ORDER BY created_at DESC;

-- Ver el resultado de un job específico
SELECT id, status, result, error_message FROM jobs WHERE id = 1;

-- Resetear el contador de uso mensual del usuario
UPDATE users SET job_used_this_month = 0 WHERE id = 1;

-- Ver cuántos jobs tiene cada usuario
SELECT user_id, COUNT(*) as total, status FROM jobs GROUP BY user_id, status;
```

Salir del psql:

```sql
\q
```

---

## Endpoints disponibles

| Método | Path                    | Estado | Descripción                                    |
| ------ | ----------------------- | ------ | ---------------------------------------------- |
| GET    | `/health`               | ✅     | Estado de PostgreSQL y Redis                   |
| GET    | `/docs`                 | ✅     | Swagger UI interactivo                         |
| GET    | `/redoc`                | ✅     | ReDoc                                          |
| POST   | `/api/v1/jobs`          | ✅     | Crear un job de análisis (async, 202)          |
| GET    | `/api/v1/jobs`          | ✅     | Listar jobs del usuario (paginado)             |
| GET    | `/api/v1/jobs/{job_id}` | ✅     | Obtener estado y resultado de un job           |
| POST   | `/api/v1/register_user` | 🚧     | Registro de usuarios (pendiente)               |

### Ejemplos de requests

```bash
# Health check
curl http://localhost:8000/health

# Crear job válido → 202
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"filename": "calculator.py", "code": "def add(a, b):\n    return a + b"}'

# Ver estado del job (reemplaza 1 con el job_id devuelto)
curl http://localhost:8000/api/v1/jobs/1

# Listar jobs con paginación
curl "http://localhost:8000/api/v1/jobs?limit=10&offset=0"
```

### Códigos de respuesta

| Código | Situación                                              |
| ------ | ------------------------------------------------------ |
| 202    | Job creado correctamente                               |
| 400    | Job ID inválido (≤ 0)                                  |
| 404    | Job o usuario no encontrado                            |
| 413    | Código excede el tamaño máximo (100 000 caracteres)    |
| 422    | Validación fallida (extensión inválida, prompt injection, campo vacío) |
| 429    | Límite mensual del plan alcanzado                      |

---

## Validación de inputs

Implementada en `agents/prompt_sanitizer.py` e integrada via Pydantic en `schemas/schemas.py`.

### Extensiones de archivo permitidas

Solo se aceptan: `.py`, `.txt`, `.md`

```bash
# Extensión inválida → 422
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"filename": "virus.exe", "code": "print(1)"}'
```

### Detección de prompt injection

Los siguientes patrones son rechazados automáticamente:

| Patrón detectado                                    |
| --------------------------------------------------- |
| `ignore all/any previous/prior/above instructions`  |
| `you are now`                                       |
| `system override`                                   |
| `reveal you/the prompt`                             |
| `[SYSTEM]`                                          |
| `DAN mode`                                          |
| `import os`                                         |

```bash
# Prompt injection → 422
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.py", "code": "ignore all previous instructions"}'
```

---

## Logging estructurado

Configurado en `core/logger.py` con `structlog`.

### Formato por entorno

| `ENVIRONMENT` | Formato       | Uso                              |
| ------------- | ------------- | -------------------------------- |
| `DEV`         | Colores       | Legible en consola local         |
| `PROD`        | JSON puro     | Para Datadog, CloudWatch, etc.   |

### Logs que genera cada request

```jsonc
// 1. Middleware — al finalizar cada HTTP request
{"level": "info", "event": "request_processed", "method": "POST",
 "path": "/api/v1/jobs", "status_code": 202, "duration_ms": 45.3,
 "correlation_id": "abc-123"}

// 2. Service — estado del cache
{"level": "info", "event": "cache_miss", "job_id": 1, "code_hash": "a3f9b2c1"}

// 3. Agente — métricas del LLM (llega después, es background task)
{"level": "info", "event": "agent_execution_completed", "filename": "calculator.py",
 "tokens_input": 312, "tokens_output": 750, "tokens_total": 1062,
 "duration_ms": 2341.5, "cost_usd": 0.003249}
```

### Correlation ID

Cada request recibe un `correlation_id` único (UUID v4). Puedes enviarlo manualmente para rastrear requests en producción:

```bash
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "X-Correlation-ID: mi-request-debug-123" \
  -H "Content-Type: application/json" \
  -d '{"filename": "app.py", "code": "def hello(): pass"}'
```

El mismo ID aparece en todos los logs de esa request y se devuelve en el header de respuesta.

---

## Cache (Redis)

El sistema cachea resultados del agente usando hashing SHA-256 del código:

- **Cache HIT** → respuesta en ~5ms (sin llamada al LLM) ⚡
- **Cache MISS** → primera ejecución (~2-10s) + guardado para reutilizar
- **TTL configurable** via `CACHE_TTL` en `.env`

Si Redis no está disponible, la app sigue funcionando normalmente (degradación graceful) pero sin cache.

---

## Tests

```bash
# Todos los tests
uv run pytest

# Solo unit tests
uv run pytest test/unit -v

# Un archivo específico
uv run pytest test/unit/test_jobs.py -v

# Con output de logs visible
uv run pytest test/unit/test_jobs.py -v -s

# Con reporte de cobertura HTML
uv run pytest --cov=. --cov-report=html
```

**Estado actual:** 12/12 tests pasando ✅

---

## Calidad de código

```bash
uv run ruff check .           # lint
uv run ruff check . --fix     # lint con auto-corrección
uv run ruff format .          # formateo
uv run mypy .                 # type checking
```

---

## CI/CD

Pipeline en `.github/workflows/pipeline.yml`. Corre en cada push y pull request.

| Paso        | Herramienta                       | Qué verifica                          |
| ----------- | --------------------------------- | ------------------------------------- |
| Lint        | `ruff check .`                    | Errores de estilo e imports           |
| Format      | `ruff format --check .`           | Formato consistente                   |
| Type check  | `mypy . --ignore-missing-imports` | Anotaciones de tipos                  |
| Tests       | `pytest --cov-fail-under=70`      | Suite completa + cobertura mínima 70% |

Las dependencias se cachean con `uv.lock` como cache key — solo se reinstalan cuando cambia el lock file.

---

## AI Agent

El cliente LLM (`ChatAnthropic` / Claude Haiku) se inicializa una vez en `core/config.py` y se importa desde ahí en todos los agentes.

### Agente simple — `agents/qa_agent.py`

Llamada single-turn: recibe código y filename, devuelve tests generados como string. Loggea tokens usados, duración y costo estimado.

### Pipeline LangGraph — `agents/node_agent.py`

Pipeline de tres nodos donde cada uno lee y escribe en `AgentState`:

```
[analysis_node] → [generate_test_node] → [review_test_node]
```

| Nodo                 | Input del estado   | Output al estado | Modelo estructurado  |
| -------------------- | ------------------ | ---------------- | -------------------- |
| `analysis_node`      | `code`, `filename` | `analysis`       | `CodeAnalysis`       |
| `generate_test_node` | `analysis`         | `test_cases`     | `list[TestCase]`     |
| `review_test_node`   | `test_cases`       | `final_tests`    | `ReviewTestFeedback` |

`final_tests` contiene el código pytest corregido que se guarda como resultado del job.
