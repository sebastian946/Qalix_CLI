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
├── agents/
│   └── qa_agent.py       # LangChain agent: generates unit tests via Claude
├── chains/               # LangChain pipelines and prompt chains
├── core/
│   └── config.py         # Settings, SQLAlchemy engine/session, Redis client, LLM client
├── models/
│   ├── __init__.py
│   └── model.py          # SQLAlchemy models: User, Job, JobStep, Subscription, Integration
├── alembic/
│   └── env.py            # Alembic env configured for async SQLAlchemy
├── alembic.ini           # Alembic configuration (script_location, logging)
├── routes/
│   ├── health_routes.py  # GET /health — checks PostgreSQL and Redis
│   ├── jobs_routes.py    # POST /jobs, GET /jobs, GET /jobs/{job_id}
│   └── user_routes.py    # POST /register_user
├── schemas/
│   └── schemas.py        # Pydantic schemas for request/response validation
├── services/
│   └── jobs_services.py  # Business logic: create_job, get_job, get_all_jobs, run_analysis
├── test/
│   ├── conftest.py       # Shared fixtures: mock_llm
│   ├── unit/
│   │   ├── test_jobs.py
│   │   ├── test_main.py
│   │   └── test_qa_agent.py
│   ├── integration/
│   └── e2e/
├── docker-compose.yaml   # Backend + PostgreSQL + Redis (healthchecks + hot reload)
├── Dockerfile            # Multi-stage production image (uv + python:3.12-slim)
├── pyproject.toml
└── main.py               # Application entry point (FastAPI app factory)
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker + Docker Compose (to run PostgreSQL, Redis, and the backend)

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

Settings are loaded via `core/config.py` using `pydantic-settings`. The module also exposes shared clients:

```python
from core.config import settings, llm, redis_client

print(settings.DATABASE_URL)  # PostgreSQL URL
# llm          → ChatAnthropic instance (Claude Haiku)
# redis_client → aioredis client
```

> **Note:** If `ANTHROPIC_API_KEY` is missing or empty, the app fails at startup with a clear Pydantic validation error.

### Start the Full Stack

Start the backend, PostgreSQL, and Redis with a single command:

```bash
docker compose up --build
```

| Service  | Local host         | Description                             |
| -------- | ------------------ | --------------------------------------- |
| backend  | `localhost:8000`   | FastAPI with hot reload enabled         |
| postgres | `localhost:5433`   | PostgreSQL 16 (user123/qalix_db)        |
| redis    | `localhost:6379`   | Redis 7                                 |

The backend waits for PostgreSQL to pass its healthcheck (`pg_isready`) before starting.

Local source code is mounted as a volume — any change to `.py` files reloads the server automatically without rebuilding the image.

> To reset from scratch (delete volumes):
> ```bash
> docker compose down -v
> docker compose up --build
> ```

### Run the Server (without Docker)

```bash
uv run uvicorn main:app --reload --port 8000
```

Requires PostgreSQL and Redis running locally (or via `docker compose up -d db redis`).

---

## Available Endpoints

| Method | Path                    | Status | Description                              |
| ------ | ----------------------- | ------ | ---------------------------------------- |
| GET    | `/health`               | ✅     | Health check (PostgreSQL + Redis)        |
| GET    | `/docs`                 | ✅     | Swagger UI                               |
| GET    | `/redoc`                | ✅     | ReDoc                                    |
| POST   | `/api/v1/jobs`          | ✅     | Submit a code analysis job (async, 202)  |
| GET    | `/api/v1/jobs`          | ✅     | List jobs for the current user (paginated) |
| GET    | `/api/v1/jobs/{job_id}` | ✅     | Get status and result of a specific job  |
| POST   | `/api/v1/register_user` | 🚧     | Register a new user (not yet implemented) |

### Health check response

```bash
curl http://localhost:8000/health
# 200 — all dependencies healthy
{"status": "ok", "dependencies": {"postgres": "ok", "redis": "ok"}}

# 503 — one or more dependencies unreachable
{"status": "degraded", "dependencies": {"postgres": "ok", "redis": "error"}}
```

### Job endpoints

```bash
# Create a job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"filename": "math.py", "code": "def add(a, b): return a + b"}'
# {"job_id": 1}

# Get job status
curl http://localhost:8000/api/v1/jobs/1

# List jobs (supports ?limit=100&offset=0)
curl "http://localhost:8000/api/v1/jobs?limit=10&offset=0"
```

---

## AI Agent

The QA agent lives in `agents/qa_agent.py` and uses `ChatAnthropic` (Claude Haiku) via LangChain to generate unit tests from code.

```python
from agents.qa_agent import chat

result = await chat(code="def add(a, b): return a + b", filename="math.py")
```

The LLM client is initialized once in `core/config.py` and imported from there to avoid multiple instances. In tests, it is mocked using the `mock_llm` fixture from `test/conftest.py`:

```python
async def test_something(mock_llm) -> None:
    # mock_llm.ainvoke returns MagicMock(content="mocked response")
    ...
```

---

## CI/CD

The GitHub Actions pipeline runs automatically on every push and pull request.

**File:** [`.github/workflows/pipeline.yml`](.github/workflows/pipeline.yml)

### Pipeline steps

| Step        | Tool                              | What it checks                              |
| ----------- | --------------------------------- | ------------------------------------------- |
| Lint        | `ruff check .`                    | Style errors, imports, common bugs          |
| Format      | `ruff format --check .`           | Consistent formatting without file changes  |
| Type check  | `mypy . --ignore-missing-imports` | Type annotations                            |
| Tests       | `pytest --cov-fail-under=70`      | Test suite + minimum 70% coverage           |

Dependencies are cached with `astral-sh/setup-uv` using `uv.lock` as the cache key — the pipeline only reinstalls when the lock file changes.

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
