"""
Unit tests for RateLimitService.

Tests cover:
- Free plan limit (10 analyses/month)
- Pro plan limit (200 analyses/month)
- HTTP 429 when limit exceeded
- Response headers with limit info
- Monthly auto-reset after 30 days
- Remaining counter decrements
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from models.model import Plan, User
from services.rate_limit_service import RateLimitService


@pytest.fixture
def db_session():
    """Mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def free_user():
    """Create a Free plan user."""
    return User(
        id=1,
        clerk_id="clerk_free_user",
        email="free@example.com",
        plan=Plan.FREE,
        job_used_this_month=0,
        month_reset_at=datetime.now(timezone.utc) + timedelta(days=30),
    )


@pytest.fixture
def pro_user():
    """Create a Pro plan user."""
    return User(
        id=2,
        clerk_id="clerk_pro_user",
        email="pro@example.com",
        plan=Plan.PRO,
        job_used_this_month=0,
        month_reset_at=datetime.now(timezone.utc) + timedelta(days=30),
    )


@pytest.mark.asyncio
async def test_free_user_first_request(db_session, free_user):
    """Free user's first request should succeed and increment counter."""
    db_session.get.return_value = free_user
    service = RateLimitService(db_session)

    rate_info = await service.check_and_increment(free_user.id)

    assert rate_info.limit == 10
    assert rate_info.used == 1
    assert rate_info.remaining == 9
    assert free_user.job_used_this_month == 1
    db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_pro_user_first_request(db_session, pro_user):
    """Pro user's first request should succeed and increment counter."""
    db_session.get.return_value = pro_user
    service = RateLimitService(db_session)

    rate_info = await service.check_and_increment(pro_user.id)

    assert rate_info.limit == 200
    assert rate_info.used == 1
    assert rate_info.remaining == 199
    assert pro_user.job_used_this_month == 1
    db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_free_user_at_limit_receives_429(db_session, free_user):
    """Free user at limit (10) should receive 429 on next request."""
    free_user.job_used_this_month = 10  # Already at limit
    db_session.get.return_value = free_user
    service = RateLimitService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.check_and_increment(free_user.id)

    assert exc_info.value.status_code == 429
    assert "Monthly analysis limit exceeded" in exc_info.value.detail
    assert "Plan FREE allows 10 analyses per month" in exc_info.value.detail
    assert "X-RateLimit-Limit" in exc_info.value.headers
    assert exc_info.value.headers["X-RateLimit-Limit"] == "10"
    assert exc_info.value.headers["X-RateLimit-Remaining"] == "0"


@pytest.mark.asyncio
async def test_free_user_exceeds_limit_receives_429(db_session, free_user):
    """Free user beyond limit should receive 429."""
    free_user.job_used_this_month = 15  # Already exceeded
    db_session.get.return_value = free_user
    service = RateLimitService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.check_and_increment(free_user.id)

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers["X-RateLimit-Remaining"] == "0"


@pytest.mark.asyncio
async def test_pro_user_not_blocked_until_their_limit(db_session, pro_user):
    """Pro user should not be blocked until reaching their limit (200)."""
    # Test at various stages
    test_cases = [1, 10, 50, 100, 150, 199]

    for used in test_cases:
        pro_user.job_used_this_month = used
        db_session.get.return_value = pro_user
        db_session.commit.reset_mock()
        service = RateLimitService(db_session)

        rate_info = await service.check_and_increment(pro_user.id)

        assert rate_info.limit == 200
        assert rate_info.used == used + 1
        assert rate_info.remaining == 200 - used - 1
        db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_pro_user_at_limit_receives_429(db_session, pro_user):
    """Pro user at limit (200) should receive 429 on next request."""
    pro_user.job_used_this_month = 200  # At limit
    db_session.get.return_value = pro_user
    service = RateLimitService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.check_and_increment(pro_user.id)

    assert exc_info.value.status_code == 429
    assert "Plan PRO allows 200 analyses per month" in exc_info.value.detail
    assert exc_info.value.headers["X-RateLimit-Limit"] == "200"
    assert exc_info.value.headers["X-RateLimit-Remaining"] == "0"


@pytest.mark.asyncio
async def test_response_headers_indicate_remaining(db_session, free_user):
    """Response should include headers indicating remaining analyses."""
    free_user.job_used_this_month = 7
    db_session.get.return_value = free_user
    service = RateLimitService(db_session)

    rate_info = await service.check_and_increment(free_user.id)

    # After increment, should be 8 used, 2 remaining
    assert rate_info.limit == 10
    assert rate_info.used == 8
    assert rate_info.remaining == 2
    assert rate_info.reset_at is not None


@pytest.mark.asyncio
async def test_monthly_reset_after_30_days(db_session, free_user):
    """Counter should reset after 30 days."""
    # Set reset date to the past
    free_user.month_reset_at = datetime.now(timezone.utc) - timedelta(days=1)
    free_user.job_used_this_month = 10  # Was at limit
    db_session.get.return_value = free_user
    service = RateLimitService(db_session)

    rate_info = await service.check_and_increment(free_user.id)

    # Should have reset to 0, then incremented to 1
    assert free_user.job_used_this_month == 1
    assert rate_info.used == 1
    assert rate_info.remaining == 9
    # Reset date should be ~30 days from now
    assert free_user.month_reset_at > datetime.now(timezone.utc)
    assert db_session.commit.call_count == 2  # Once for reset, once for increment


@pytest.mark.asyncio
async def test_reset_on_first_use(db_session, free_user):
    """Counter should initialize reset date on first use."""
    free_user.month_reset_at = None  # New user
    free_user.job_used_this_month = 0
    db_session.get.return_value = free_user
    service = RateLimitService(db_session)

    rate_info = await service.check_and_increment(free_user.id)

    assert free_user.job_used_this_month == 1
    assert free_user.month_reset_at is not None
    assert free_user.month_reset_at > datetime.now(timezone.utc)


@pytest.mark.asyncio
async def test_user_not_found_raises_404(db_session):
    """Non-existent user should raise 404."""
    db_session.get.return_value = None
    service = RateLimitService(db_session)

    with pytest.raises(HTTPException) as exc_info:
        await service.check_and_increment(999)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "User not found"


@pytest.mark.asyncio
async def test_get_limit_info_without_incrementing(db_session, free_user):
    """get_limit_info should return info without incrementing counter."""
    free_user.job_used_this_month = 5
    db_session.get.return_value = free_user
    service = RateLimitService(db_session)

    rate_info = await service.get_limit_info(free_user.id)

    assert rate_info.limit == 10
    assert rate_info.used == 5
    assert rate_info.remaining == 5
    # Should NOT have incremented
    assert free_user.job_used_this_month == 5
    db_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_remaining_decrements_correctly(db_session, pro_user):
    """Remaining should decrement correctly as usage increases."""
    db_session.get.return_value = pro_user
    service = RateLimitService(db_session)

    # Make multiple requests and track remaining
    for i in range(1, 6):
        db_session.commit.reset_mock()
        pro_user.job_used_this_month = i - 1  # Reset to state before increment

        rate_info = await service.check_and_increment(pro_user.id)

        assert rate_info.used == i
        assert rate_info.remaining == 200 - i