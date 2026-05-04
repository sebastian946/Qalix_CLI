from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from core.config import get_db
from main import app
from models.model import Status
from schemas.schemas import MAX_CODE_SIZE


def make_mock_job(
    job_id: int = 1,
    user_id: int = 1,
    status: Status = Status.PENDING,
    result: str | None = None,
) -> MagicMock:
    now = datetime.now(timezone.utc)
    job = MagicMock()
    job.id = job_id
    job.user_id = user_id
    job.filename = "test.py"
    job.code = "print('hello')"
    job.status = status
    job.result = result
    job.error_message = None
    job.tokens_used = None
    job.created_at = now
    job.updated_at = now
    job.completed_at = now if status == Status.COMPLETED else None
    return job


def make_mock_session(job_id: int = 1) -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    async def mock_refresh(obj: object) -> None:
        obj.id = job_id  # type: ignore[attr-defined]

    session.refresh = mock_refresh
    return session


@pytest.fixture
def override_db() -> None:
    mock_session = make_mock_session()

    async def _get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _get_db
    yield mock_session
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_job_valid_returns_202_and_id(override_db) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs",
            json={"filename": "test.py", "code": "print('hello')"},
        )
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert isinstance(data["job_id"], int)


@pytest.mark.asyncio
async def test_create_job_empty_code_returns_422() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs",
            json={"filename": "test.py", "code": ""},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_job_code_too_large_returns_413(override_db) -> None:
    large_code = "x" * (MAX_CODE_SIZE + 1)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/jobs",
            json={"filename": "test.py", "code": large_code},
        )
    assert response.status_code == 413


# --- GET /jobs/{job_id} ---

def _override_get_db_with_job(mock_job: MagicMock | None) -> None:
    session = AsyncMock()
    session.get = AsyncMock(return_value=mock_job)

    async def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db


@pytest.mark.asyncio
async def test_get_job_pending_returns_200_without_result() -> None:
    _override_get_db_with_job(make_mock_job(status=Status.PENDING, result=None))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/jobs/1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["result"] is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_job_completed_returns_200_with_result() -> None:
    _override_get_db_with_job(make_mock_job(status=Status.COMPLETED, result="No issues found"))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/jobs/1")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"] == "No issues found"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_job_not_found_returns_404() -> None:
    _override_get_db_with_job(None)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/jobs/999")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_job_different_user_returns_403() -> None:
    _override_get_db_with_job(make_mock_job(user_id=2))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/jobs/1")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()


# --- GET /jobs ---

def _override_get_db_with_jobs(jobs: list[MagicMock]) -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = jobs
    session.execute = AsyncMock(return_value=mock_result)

    async def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db


@pytest.mark.asyncio
async def test_get_all_jobs_empty_list_returns_200() -> None:
    _override_get_db_with_jobs([])
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/jobs")
        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_all_jobs_returns_only_authenticated_user_jobs() -> None:
    user_jobs = [make_mock_job(job_id=1, user_id=1), make_mock_job(job_id=2, user_id=1)]
    _override_get_db_with_jobs(user_jobs)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/jobs")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(job["user_id"] == 1 for job in data)
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_all_jobs_pagination_params_accepted() -> None:
    jobs = [make_mock_job(job_id=i, user_id=1) for i in range(1, 4)]
    _override_get_db_with_jobs(jobs[:2])
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/jobs?limit=2&offset=0")
        assert response.status_code == 200
        assert len(response.json()) == 2
    finally:
        app.dependency_overrides.clear()
