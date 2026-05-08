# Qalix — Backend

**QA Intelligence Platform** — AI-powered SaaS for automated software testing.

Qalix helps teams generate, execute, and maintain test suites using AI agents, reducing manual QA effort and catching regressions faster.

---

## Tech Stack

| Layer      | Technology                                    |
| ---------- | --------------------------------------------- |
| API        | FastAPI + Uvicorn                             |
| Database   | PostgreSQL (async via asyncpg + SQLAlchemy)   |
| Migrations | Alembic                                       |
| AI Agents  | LangGraph + LangChain                         |
| LLM        | Anthropic Claude Haiku                        |
| Vector DB  | ChromaDB                                      |
| Cache      | Redis                                         |
| Validation | Pydantic + pydantic-settings                  |
| Logging    | structlog (JSON in prod, colored in dev)      |

---

## Project Structure

```
Qalix_CLI/
├── backend/               ← API + AI agents
│   ├── agents/
│   │   ├── prompt_sanitizer.py   # Validation: extension, prompt injection, size
│   │   ├── qa_agent.py           # LangChain: language-aware test generation via Claude
│   │   └── node_agent.py         # LangGraph: analyze → generate → review pipeline
│   ├── core/
│   │   ├── config.py             # Settings, SQLAlchemy, Redis, LLM
│   │   └── logger.py             # Structured logging + HTTP middleware
│   ├── models/model.py           # SQLAlchemy: User, Job, JobStep, Subscription
│   ├── routes/
│   │   ├── health_routes.py      # GET /health
│   │   ├── jobs_routes.py        # POST/GET /jobs
│   │   └── user_routes.py        # POST /register_user
│   ├── schemas/schemas.py        # Pydantic schemas + input validation
│   ├── services/
│   │   ├── jobs_services.py      # Job business logic with caching
│   │   ├── rate_limit_service.py # Per-plan monthly limits (Free/Pro)
│   │   └── redis_service.py      # Cache with graceful degradation
│   ├── alembic/                  # Database migrations
│   ├── test/unit/                # Unit tests
│   ├── docker-compose.yaml
│   ├── Dockerfile
│   └── pyproject.toml
└── cli/                   ← Node.js CLI
    ├── bin/qalix.js              # Entry point for the `qalix` command
    ├── src/
    │   ├── commands/analyze.js   # analyze command logic
    │   ├── api/client.js         # HTTP client for the backend
    │   └── utils/language.js     # Language detection by extension or --lang
    └── package.json
```

---

## Running the Project

### Prerequisites

| Tool           | Min version | Purpose                         |
| -------------- | ----------- | ------------------------------- |
| Docker Desktop | any         | PostgreSQL + Redis + Backend    |
| Python         | 3.12+       | Local backend development       |
| uv             | any         | Python package manager          |
| Node.js        | 18+         | CLI                             |

---

### Step 1 — Environment variables

Create or edit `backend/.env`:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key
DATABASE_URL=postgresql+asyncpg://user123:password123@localhost:5433/qalix_db
REDIS_URL=redis://localhost:6379
ENVIRONMENT=DEV
LOG_LEVEL=INFO
CACHE_TTL=3600
```

> `ANTHROPIC_API_KEY` is required. The backend fails to start without it.

---

### Step 2 — Start the backend

**Option A — Full Docker (recommended)**

```bash
cd backend
docker compose up --build
```

Starts PostgreSQL, Redis, and the backend together. Hot reload is enabled.

**Option B — Docker for infrastructure only, backend runs locally**

```bash
# Terminal 1 — infrastructure
cd backend
docker compose up db redis -d

# Terminal 2 — backend
cd backend
uv sync --all-groups
uv run uvicorn main:app --reload --port 8000
```

| Service  | URL                         |
| -------- | --------------------------- |
| Backend  | http://localhost:8000        |
| Swagger  | http://localhost:8000/docs   |
| Postgres | localhost:5433               |
| Redis    | localhost:6379               |

---

### Step 3 — Run database migrations

Creates all tables. Must be run before using any endpoint:

```bash
cd backend
uv run alembic upgrade head
```

Other useful commands:

```bash
uv run alembic current      # show applied revision
uv run alembic history      # show migration history
uv run alembic downgrade -1 # roll back one migration
uv run alembic revision --autogenerate -m "description"  # generate new migration
```

---

### Step 4 — Seed the database

> **Important:** job endpoints use a hardcoded `user_id = 1` until Clerk authentication is implemented. Without this user you get `404 User not found`.

Connect to the database:

```bash
docker exec -it qalix_postgres psql -U user123 -d qalix_db
```

Insert the test user:

```sql
INSERT INTO users (clerk_id, email, plan, job_used_this_month, created_at, updated_at)
VALUES ('clerk_test_001', 'test@qalix.com', 'free', 0, NOW(), NOW());
```

Verify (id must be 1):

```sql
SELECT id, email, plan FROM users;
```

Exit: `\q`

---

### Step 5 — Install and link the CLI

```bash
cd cli
npm install
npm link          # registers "qalix" as a global command
```

Verify:

```bash
qalix --version   # 1.0.0
qalix --help
```

---

### Step 6 — Test the full flow

With the backend running and the seed user in the database:

```bash
# Analyze a Python file
qalix analyze src/calculator.py

# Analyze a JavaScript file
qalix analyze app.js

# Override language detection
qalix analyze mycode --lang go

# Save generated tests to a file
qalix analyze calculator.py --output tests/test_calculator.py

# Point to a remote backend
qalix analyze app.ts --url https://api.qalix.com
```

---

## Database

### Tables

| Table           | Description                                      |
| --------------- | ------------------------------------------------ |
| `users`         | Users with plan and monthly usage counter        |
| `jobs`          | Code analysis jobs submitted by users            |
| `jobs_steps`    | Individual LangGraph agent steps per job         |
| `subscriptions` | Stripe subscriptions                             |
| `integrations`  | Jira, Slack, GitHub integrations                 |

### Useful queries during development

```sql
-- List all jobs with their status
SELECT id, filename, status, created_at FROM jobs ORDER BY created_at DESC;

-- Get the result of a specific job
SELECT id, status, result, error_message FROM jobs WHERE id = 1;

-- Reset user's monthly usage counter
UPDATE users SET job_used_this_month = 0 WHERE id = 1;
```

---

## Available Endpoints

| Method | Path                    | Status | Description                                      |
| ------ | ----------------------- | ------ | ------------------------------------------------ |
| GET    | `/health`               | ✅     | PostgreSQL and Redis health check                |
| GET    | `/docs`                 | ✅     | Swagger UI                                       |
| POST   | `/api/v1/jobs`          | ✅     | Submit a code analysis job (async, 202)          |
| GET    | `/api/v1/jobs`          | ✅     | List jobs (paginated: `?limit=10&offset=0`)      |
| GET    | `/api/v1/jobs/{job_id}` | ✅     | Get status and result of a specific job          |
| POST   | `/api/v1/register_user` | 🚧     | User registration (not yet implemented)          |

### Response codes

| Code | Situation                                                    |
| ---- | ------------------------------------------------------------ |
| 202  | Job created successfully                                     |
| 400  | Invalid job ID (≤ 0)                                         |
| 404  | Job or user not found                                        |
| 413  | Code exceeds 100 000 characters                              |
| 422  | Validation failed (extension, prompt injection, empty field) |
| 429  | Monthly plan limit reached                                   |

---

## Input Validation

| Rule                  | Details                                                                |
| --------------------- | ---------------------------------------------------------------------- |
| Allowed extensions    | `.py .js .ts .go .java .rb .php .cs .cpp .rs .kt .swift .txt .md`     |
| Max code size         | 100 000 characters                                                     |
| Prompt injection      | Rejects patterns like `ignore all previous instructions`, `DAN mode`   |

---

## Supported Languages and Test Frameworks

| Language   | Extension | Generated test framework   |
| ---------- | --------- | -------------------------- |
| Python     | `.py`     | pytest                     |
| JavaScript | `.js`     | Jest                       |
| TypeScript | `.ts`     | Jest + ts-jest             |
| Go         | `.go`     | go test                    |
| Java       | `.java`   | JUnit 5                    |
| Ruby       | `.rb`     | RSpec                      |
| PHP        | `.php`    | PHPUnit                    |
| C#         | `.cs`     | xUnit                      |
| C++        | `.cpp`    | Google Test                |
| Rust       | `.rs`     | cargo test                 |
| Kotlin     | `.kt`     | JUnit 5 + Kotlin           |
| Swift      | `.swift`  | XCTest                     |

---

## Structured Logging

| `ENVIRONMENT` | Format  | Use case                              |
| ------------- | ------- | ------------------------------------- |
| `DEV`         | Colored | Readable in local console             |
| `PROD`        | JSON    | Datadog, CloudWatch, etc.             |

Every request produces 3 automatic logs:

```jsonc
// 1. Middleware — on every HTTP request
{"event": "request_processed", "method": "POST", "status_code": 202, "duration_ms": 45.3, "correlation_id": "abc-123"}

// 2. Service — cache state
{"event": "cache_miss", "job_id": 1, "code_hash": "a3f9b2c1"}

// 3. Agent — LLM execution metrics (arrives after, runs in background)
{"event": "agent_execution_completed", "language": "JavaScript", "framework": "Jest",
 "tokens_total": 1062, "duration_ms": 2341.5, "cost_usd": 0.003249}
```

---

## Tests

```bash
cd backend

uv run pytest                              # all tests
uv run pytest test/unit/test_jobs.py -v   # single file
uv run pytest -v -s                        # with log output visible
uv run pytest --cov=. --cov-report=html   # with HTML coverage report
```

**Current status:** 12/12 tests passing ✅

---

## Code Quality

```bash
uv run ruff check .           # lint
uv run ruff check . --fix     # lint with auto-fix
uv run ruff format .          # format
uv run mypy .                 # type checking
```

---

## CI/CD

Pipeline defined in `.github/workflows/pipeline.yml`. Runs on every push and pull request.

| Step       | Tool                              | What it checks                       |
| ---------- | --------------------------------- | ------------------------------------ |
| Lint       | `ruff check .`                    | Style errors and imports             |
| Format     | `ruff format --check .`           | Consistent formatting                |
| Type check | `mypy . --ignore-missing-imports` | Type annotations                     |
| Tests      | `pytest --cov-fail-under=70`      | Full suite + minimum 70% coverage    |
