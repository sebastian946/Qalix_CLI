from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.model import Job, Status
from schemas.schemas import CreateJobRequest
from services.jobs_services import JobService


def make_mock_job(
    job_id: int = 1,
    user_id: int = 1,
    filename: str = "test.py",
    code: str = "print('hello')",
    status: Status = Status.PENDING,
    result: str | None = None,
    error_message: str | None = None,
) -> Job:
    """Create a mock Job object."""
    now = datetime.now(UTC)
    job = Job(
        id=job_id,
        user_id=user_id,
        filename=filename,
        code=code,
        status=status,
        result=result,
        error_message=error_message,
        tokens_used=None,
        created_at=now,
        updated_at=now,
        completed_at=now if status in [Status.COMPLETED, Status.FAILED] else None,
    )
    return job


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Create a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.get = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_job_saves_with_pending_status(mock_db_session: AsyncMock) -> None:
    """Test that create_job saves a job with PENDING status."""
    # Arrange
    service = JobService(mock_db_session)
    job_data = CreateJobRequest(filename="test.py", code="print('hello')")
    user_id = 1

    async def mock_refresh(obj: Job) -> None:
        obj.id = 1

    mock_db_session.refresh = mock_refresh

    # Act
    job = await service.create_job(user_id, job_data)

    # Assert
    assert job.status == Status.PENDING
    assert job.user_id == user_id
    assert job.filename == "test.py"
    assert job.code == "print('hello')"
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_analysis_updates_to_completed_with_result(mock_db_session: AsyncMock) -> None:
    """Test that run_analysis updates status to COMPLETED with result."""
    # Arrange
    service = JobService(mock_db_session)
    job = make_mock_job(job_id=1, status=Status.PENDING)
    mock_db_session.get = AsyncMock(return_value=job)

    expected_result = "# Unit Test\ndef test_hello():\n    assert True"

    with patch("services.jobs_services.chat", AsyncMock(return_value=expected_result)):
        # Act
        await service.run_analysis(1)

        # Assert
        assert job.status == Status.COMPLETED
        assert job.result == expected_result
        assert job.error_message is None
        assert job.completed_at is not None
        assert mock_db_session.commit.await_count == 2  # Once for RUNNING, once for COMPLETED


@pytest.mark.asyncio
async def test_run_analysis_updates_to_failed_on_exception(mock_db_session: AsyncMock) -> None:
    """Test that run_analysis updates status to FAILED if agent raises exception."""
    # Arrange
    service = JobService(mock_db_session)
    job = make_mock_job(job_id=1, status=Status.PENDING)
    mock_db_session.get = AsyncMock(return_value=job)

    error_message = "Agent failed to process code"

    with patch("services.jobs_services.chat", AsyncMock(side_effect=Exception(error_message))):
        # Act
        await service.run_analysis(1)

        # Assert
        assert job.status == Status.FAILED
        assert job.error_message == error_message
        assert job.result is None
        assert job.completed_at is not None
        assert mock_db_session.commit.await_count == 2  # Once for RUNNING, once for FAILED


@pytest.mark.asyncio
async def test_get_job_returns_none_for_nonexistent_id(mock_db_session: AsyncMock) -> None:
    """Test that get_job returns None for a nonexistent job ID."""
    # Arrange
    service = JobService(mock_db_session)
    mock_db_session.get = AsyncMock(return_value=None)

    # Act
    job = await service.get_job(999, user_id=1)

    # Assert
    assert job is None
    mock_db_session.get.assert_awaited_once_with(Job, 999)


@pytest.mark.asyncio
async def test_get_job_raises_403_for_different_user(mock_db_session: AsyncMock) -> None:
    """Test that get_job raises HTTPException 403 when job belongs to different user."""
    # Arrange
    from fastapi import HTTPException

    service = JobService(mock_db_session)
    job = make_mock_job(job_id=1, user_id=2)
    mock_db_session.get = AsyncMock(return_value=job)

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await service.get_job(1, user_id=1)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access forbidden"


@pytest.mark.asyncio
async def test_get_job_returns_job_for_correct_user(mock_db_session: AsyncMock) -> None:
    """Test that get_job returns job when user_id matches."""
    # Arrange
    service = JobService(mock_db_session)
    job = make_mock_job(job_id=1, user_id=1)
    mock_db_session.get = AsyncMock(return_value=job)

    # Act
    result = await service.get_job(1, user_id=1)

    # Assert
    assert result == job
    assert result.id == 1
    assert result.user_id == 1


@pytest.mark.asyncio
async def test_run_analysis_does_nothing_when_job_not_found(mock_db_session: AsyncMock) -> None:
    """Test that run_analysis exits gracefully when job doesn't exist."""
    # Arrange
    service = JobService(mock_db_session)
    mock_db_session.get = AsyncMock(return_value=None)

    # Act
    await service.run_analysis(999)

    # Assert - commit should only be called once by get, not for status updates
    mock_db_session.get.assert_awaited_once_with(Job, 999)
    mock_db_session.commit.assert_not_awaited()
