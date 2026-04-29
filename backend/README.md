# Qalix — Backend

**QA Intelligence Platform** — AI-powered SaaS for automated software testing.

Qalix helps teams generate, execute, and maintain test suites using AI agents, reducing manual QA effort and catching regressions faster.

---

## Tech Stack

| Layer      | Technology                                  |
| ---------- | ------------------------------------------- |
| API        | FastAPI + Uvicorn                           |
| Database   | PostgreSQL (async via asyncpg + SQLAlchemy) |
| Migrations | Alembic                                     |
| AI Agents  | LangGraph + LangChain                       |
| LLM        | Anthropic Claude (langchain-anthropic)      |
| Vector DB  | ChromaDB                                    |
| Cache      | Redis                                       |
| Validation | Pydantic + pydantic-settings                |

---

## Project Structure

```
backend/
├── .github/
│   └── workflows/
│       └── pipeline.yml  # CI: ruff → mypy → pytest (coverage ≥ 70%)
├── api/          # HTTP endpoints and routers (FastAPI) — pending
├── agents/       # AI agents built with LangGraph — pending
├── chains/       # LangChain pipelines and prompt chains — pending
├── core/
│   └── config.py # App settings, async SQLAlchemy engine and session
├── models/
│   ├── __init__.py
│   └── model.py  # SQLAlchemy models: User, Job, JobStep, Subscription, Integration
├── alembic/
│   └── env.py    # Alembic env configured for async SQLAlchemy
├── alembic.ini   # Alembic configuration (script_location, logging)
├── routes/       # Route registration — pending
├── schemas/      # Pydantic schemas for request/response validation — pending
├── services/     # Business logic layer — pending
├── test/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker-compose.yaml  # Backend + PostgreSQL + Redis (healthchecks + hot reload)
├── Dockerfile           # Multi-stage production image (uv + python:3.12-slim)
├── pyproject.toml
└── main.py       # Application entry point (FastAPI app factory + /health)
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker + Docker Compose (para levantar PostgreSQL, Redis y el backend)

### Installation

```bash
uv sync --all-groups
```

### Environment Variables

Create or update the `.env` file in the `backend/` root:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DATABASE_URL=postgresql+asyncpg://user123:password123@localhost:5433/qalix_db
REDIS_URL=your_redis_url_here
ENVIRONMENT=DEV
```

> **Note:** The port is `5433` (not the default `5432`) to avoid conflicts with a local PostgreSQL installation. Adjust if your environment is different.

Settings are loaded via `core/config.py` using `pydantic-settings`. Access them like:

```python
from core.config import settings

print(settings.DATABASE_URL)
```

### Start the Full Stack

Levanta backend, PostgreSQL y Redis con un solo comando:

```bash
docker compose up --build
```

| Servicio  | Host local         | Descripción                        |
| --------- | ------------------ | ---------------------------------- |
| backend   | `localhost:8000`   | FastAPI con hot reload activo      |
| postgres  | `localhost:5433`   | PostgreSQL 16 (user123/qalix_db)   |
| redis     | `localhost:6379`   | Redis 7                            |

El backend espera a que PostgreSQL pase su healthcheck (`pg_isready`) antes de iniciar.

El código local se monta como volumen — cualquier cambio en archivos `.py` recarga el servidor automáticamente sin reconstruir la imagen.

> Para reiniciar desde cero (borrar volúmenes):
> ```bash
> docker compose down -v
> docker compose up --build
> ```

### Run the Server (without Docker)

```bash
uv run uvicorn main:app --reload --port 8000
```

Requiere PostgreSQL y Redis corriendo localmente (o vía `docker compose up -d db redis`).

---

## Available Endpoints

| Method | Path      | Description  |
| ------ | --------- | ------------ |
| GET    | `/health` | Health check |
| GET    | `/docs`   | Swagger UI   |
| GET    | `/redoc`  | ReDoc        |

Verify the server is running:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

---

## CI/CD

El pipeline de GitHub Actions corre automáticamente en cada push y pull request.

**Archivo:** [`.github/workflows/pipeline.yml`](.github/workflows/pipeline.yml)

### Pasos del pipeline

| Paso | Herramienta | Qué verifica |
| ---- | ----------- | ------------ |
| Lint | `ruff check .` | Errores de estilo, imports, bugs comunes |
| Format | `ruff format --check .` | Formato consistente sin modificar archivos |
| Type check | `mypy . --ignore-missing-imports` | Anotaciones de tipos |
| Tests | `pytest --cov-fail-under=70` | Tests + cobertura mínima del 70% |

Las dependencias se cachean con `astral-sh/setup-uv` usando `uv.lock` como clave — el pipeline solo reinstala si cambia el lock file.

---

## Development

### Code Quality

```bash
uv run ruff check .          # lint
uv run ruff check . --fix    # lint and auto-fix
uv run ruff format .         # format
uv run mypy .                # type checking
```

### Database Migrations

Alembic is configured with async SQLAlchemy support. The `alembic/env.py` reads `DATABASE_URL` from `core/config.py` (via `.env`) and registers all models from `models/model.py` automatically for autogenerate support.

```bash
# Generate a migration from model changes
uv run alembic revision --autogenerate -m "description"

# Apply all pending migrations
uv run alembic upgrade head

# Rollback one step
uv run alembic downgrade -1

# Show migration history
uv run alembic history

# Show current applied revision
uv run alembic current
```

#### Database Tables

| Table           | Model          | Description                                        |
| --------------- | -------------- | -------------------------------------------------- |
| `users`         | `User`         | Registered users with plan and monthly usage       |
| `jobs`          | `Job`          | Code analysis jobs submitted by users              |
| `jobs_steps`    | `JobStep`      | Individual LangGraph agent steps per job           |
| `subscriptions` | `Subscription` | Active Stripe subscriptions linked to users        |
| `integrations`  | `Integration`  | Optional third-party integrations (Jira, Slack, GitHub) |

### Tests

```bash
uv run pytest                            # run all tests
uv run pytest test/unit                  # unit tests only
uv run pytest test/integration           # integration tests only
uv run pytest --cov=. --cov-report=html  # with coverage report
```

#### Pytest Configuration (`pyproject.toml`)

```toml
[tool.pytest.ini_options]
addopts    = "-ra -q --cov=."
testpaths  = ["test"]
pythonpath = ["."]
```

> `pythonpath = ["."]` is required because source lives in `backend/` root (no `src/` layout). Without it, pytest cannot resolve imports like `from main import app`.
