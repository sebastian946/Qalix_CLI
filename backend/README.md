# Qalix — Backend

**QA Intelligence Platform** — AI-powered SaaS for automated software testing.

Qalix helps teams generate, execute, and maintain test suites using AI agents, reducing manual QA effort and catching regressions faster.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Database | PostgreSQL (async via asyncpg + SQLAlchemy) |
| Migrations | Alembic |
| AI Agents | LangGraph + LangChain |
| LLM | Anthropic Claude (langchain-anthropic) |
| Vector DB | ChromaDB |
| Cache | Redis |
| Validation | Pydantic + pydantic-settings |

---

## Project Structure

```
backend/
├── api/          # HTTP endpoints and routers (FastAPI)
├── agents/       # AI agents built with LangGraph
├── chains/       # LangChain pipelines and prompt chains
├── core/         # Central config, settings, and DB connection
├── models/       # SQLAlchemy database models
├── schemas/      # Pydantic schemas for request/response validation
├── services/     # Business logic layer
├── alembic/      # Database migrations
├── test/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── main.py       # Application entry point
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- PostgreSQL
- Redis

### Installation

```bash
uv sync --all-groups
```

### Environment Variables

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

### Run the Server

```bash
uv run uvicorn main:app --reload
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
uv run pytest                          # run all tests
uv run pytest test/unit                # unit tests only
uv run pytest test/integration         # integration tests only
uv run pytest --cov=. --cov-report=html  # with coverage report
```
