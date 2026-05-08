"""
Rate limiting service based on user plan.

Implements monthly usage limits:
- Free plan: 10 analyses per month
- Pro plan: 200 analyses per month
"""

from datetime import UTC, datetime

import structlog
from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_db
from models.model import Plan, User

logger = structlog.get_logger()

# Plan limits (analyses per month)
PLAN_LIMITS = {
    Plan.FREE: 10,
    Plan.PRO: 200,
}


class RateLimitInfo:
    """Information about rate limit status."""

    def __init__(
        self,
        limit: int,
        used: int,
        remaining: int,
        reset_at: datetime,
    ):
        self.limit = limit
        self.used = used
        self.remaining = remaining
        self.reset_at = reset_at

    @property
    def is_exceeded(self) -> bool:
        """Check if the limit has been exceeded."""
        return self.used >= self.limit


class RateLimitService:
    """Service for managing user rate limits based on their plan."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_and_increment(self, user_id: int) -> RateLimitInfo:
        """
        Check if user can make a request and increment their usage counter.

        Returns RateLimitInfo with current usage stats.
        Raises HTTPException(429) if limit exceeded.
        """
        # Get user
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Reset counter if month has passed
        await self._reset_if_needed(user)

        # Get limit for user's plan
        limit = PLAN_LIMITS.get(user.plan, PLAN_LIMITS[Plan.FREE])

        # Calculate remaining
        remaining = max(0, limit - user.job_used_this_month)

        # Check if limit exceeded
        if user.job_used_this_month >= limit:
            logger.warning(
                "rate_limit_exceeded",
                user_id=user_id,
                plan=user.plan.value,
                used=user.job_used_this_month,
                limit=limit,
            )

            rate_info = RateLimitInfo(
                limit=limit,
                used=user.job_used_this_month,
                remaining=0,
                reset_at=user.month_reset_at or datetime.now(UTC),
            )

            raise HTTPException(
                status_code=429,
                detail=f"Monthly analysis limit exceeded. "
                f"Plan {user.plan.value.upper()} allows {limit} analyses per month. "
                f"Limit resets on {rate_info.reset_at.strftime('%Y-%m-%d')}.",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(rate_info.reset_at.timestamp())),
                },
            )

        # Increment usage counter
        user.job_used_this_month += 1
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(
            "rate_limit_passed",
            user_id=user_id,
            plan=user.plan.value,
            used=user.job_used_this_month,
            limit=limit,
        )

        return RateLimitInfo(
            limit=limit,
            used=user.job_used_this_month,
            remaining=remaining - 1,  # Already incremented
            reset_at=user.month_reset_at or datetime.now(UTC),
        )

    async def get_limit_info(self, user_id: int) -> RateLimitInfo:
        """
        Get current rate limit information without incrementing.

        Useful for checking limits without consuming quota.
        """
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Reset counter if month has passed
        await self._reset_if_needed(user)

        limit = PLAN_LIMITS.get(user.plan, PLAN_LIMITS[Plan.FREE])
        remaining = max(0, limit - user.job_used_this_month)

        return RateLimitInfo(
            limit=limit,
            used=user.job_used_this_month,
            remaining=remaining,
            reset_at=user.month_reset_at or datetime.now(UTC),
        )

    async def _reset_if_needed(self, user: User) -> None:
        """
        Reset monthly counter if the reset date has passed.

        Sets month_reset_at to 30 days from now on first use or after reset.
        """
        now = datetime.now(UTC)

        # If no reset date set, or reset date has passed
        if not user.month_reset_at or now >= user.month_reset_at:
            logger.info(
                "monthly_counter_reset",
                user_id=user.id,
                previous_count=user.job_used_this_month,
            )

            user.job_used_this_month = 0

            # Set next reset date to 30 days from now
            from datetime import timedelta

            user.month_reset_at = now + timedelta(days=30)

            await self.db.commit()


# Dependency for FastAPI
async def get_rate_limit_service(db: AsyncSession = Depends(get_db)) -> RateLimitService:
    """FastAPI dependency to get RateLimitService."""
    return RateLimitService(db)