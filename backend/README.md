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
├── api/          # HTTP endpoints and routers (FastAPI) — pending
├── agents/       # AI agents built with LangGraph — pending
├── chains/       # LangChain pipelines and prompt chains — pending
├── core/
│   └── config.py # App settings via pydantic-settings (.env)
├── models/       # SQLAlchemy database models — pending
├── routes/       # Route registration — pending
├── schemas/      # Pydantic schemas for request/response validation — pending
├── services/     # Business logic layer — pending
├── alembic/      # Database migrations
├── test/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker-compose.yaml  # PostgreSQL service
├── pyproject.toml
└── main.py       # Application entry point (FastAPI app factory + /health)
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker (for PostgreSQL via docker-compose)

### Installation

```bash
uv sync --all-groups
```

### Environment Variables

The `.env` file is already present. Update the values before running:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DATABASE_URL=your_database_url_here
REDIS_URL=your_redis_url_here
ENVIRONMENT=DEV
```

Settings are loaded via `core/config.py` using `pydantic-settings`. Access them like:

```python
from core.config import Settings

settings = Settings()
print(settings.ANTHROPIC_API_KEY)
```

### Start the Database

```bash
docker compose up -d
```

This starts PostgreSQL on `localhost:5432`:

- User: `user123`
- Password: `password123`
- DB: `my_database`

### Run the Server

```bash
uv run uvicorn main:app --reload --port 8000
```

The server starts on `http://localhost:8000`.

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

## Development

### Code Quality

```bash
uv run ruff check .          # lint
uv run ruff check . --fix    # lint and auto-fix
uv run ruff format .         # format
uv run mypy .                # type checking
```

### Database Migrations

```bash
uv run alembic revision --autogenerate -m "description"  # create migration
uv run alembic upgrade head                              # apply migrations
uv run alembic downgrade -1                              # rollback one step
```

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
