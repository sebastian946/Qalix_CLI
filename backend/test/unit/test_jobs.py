from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from core.config import get_db
from main import app
from schemas.schemas import MAX_CODE_SIZE


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
