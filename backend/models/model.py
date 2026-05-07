import enum
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.config import Base


class Plan(enum.Enum):
    FREE = "free"
    PRO = "pro"


class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    CANCELED = "canceled"


class Status(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepName(enum.Enum):
    ANALYZE = "analyze"
    GENERATE = "generate"
    REVIEW = "review"


class IntegrationType(enum.Enum):
    JIRA = "jira"
    SLACK = "slack"
    GITHUB = "github"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    clerk_id: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[str] = mapped_column(String, unique=True)
    plan: Mapped[Plan] = mapped_column(Enum(Plan), default=Plan.FREE)
    job_used_this_month: Mapped[int] = mapped_column(default=0)
    month_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    filename: Mapped[str] = mapped_column(String)
    code: Mapped[str] = mapped_column(Text)
    status: Mapped[Status] = mapped_column(Enum(Status), default=Status.PENDING)
    result: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    tokens_used: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class JobStep(Base):
    __tablename__ = "jobs_steps"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    step_name: Mapped[StepName] = mapped_column(Enum(StepName))
    step_order: Mapped[int] = mapped_column()
    input: Mapped[str | None] = mapped_column(Text)
    output: Mapped[str | None] = mapped_column(Text)
    tokens_used: Mapped[int | None] = mapped_column()
    duration_ms: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    stripe_customer_id: Mapped[str] = mapped_column(String, unique=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String, unique=True)
    plan: Mapped[Plan] = mapped_column(Enum(Plan))
    status: Mapped[SubscriptionStatus] = mapped_column(Enum(SubscriptionStatus))
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[IntegrationType] = mapped_column(Enum(IntegrationType))
    is_active: Mapped[int] = mapped_column(default=1)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)
