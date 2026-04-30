import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB

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

    id = Column(Integer, primary_key=True)
    clerk_id = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    plan = Column(Enum(Plan), nullable=False, default=Plan.FREE)
    job_used_this_month = Column(Integer, default=0)
    month_reset_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    code = Column(Text, nullable=False)
    status = Column(Enum(Status), default=Status.PENDING)
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)


class JobStep(Base):
    __tablename__ = "jobs_steps"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    step_name = Column(Enum(StepName), nullable=False)
    step_order = Column(Integer, nullable=False)
    input = Column(Text, nullable=True)
    output = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Subscription(Base):
    __tablename__ = "subscriptions"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    stripe_customer_id = Column(String, nullable=False, unique=True)
    stripe_subscription_id = Column(String, nullable=False, unique=True)
    plan = Column(Enum(Plan), nullable=False)
    status = Column(Enum(SubscriptionStatus), nullable=False)
    current_period_start = Column(DateTime(timezone=True), nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    canceled_at = Column(DateTime(timezone=True), nullable=True)


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(IntegrationType), nullable=False)
    is_active = Column(Integer, default=1)
    config = Column(JSONB, nullable=False)
