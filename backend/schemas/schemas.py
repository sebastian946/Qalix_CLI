import enum
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)

from agents.prompt_sanitizer import PromptSanitizer
from models.model import Status

MAX_CODE_SIZE = 100_000  # ~100KB in characters

_sanitizer = PromptSanitizer()

# Use schema example user = CreateUserSchema(**external_data_user) to create a user schema instance from external data.

class CreateUserSchema(BaseModel):
    id: int
    clerk_id: str
    email: EmailStr
    plan: str | None
    job_used_this_month: int
    month_reset_at: datetime | None
    created_at: datetime
    updated_at: datetime

class ResponseUserSchema(BaseModel):
    id: int
    email: EmailStr
    plan: str | None
    created_at: datetime
    updated_at: datetime

external_data_user = {
    "id": 1,
    "clerk_id": "clerk_123",
    "email": "user@example.com",
    "plan": "premium",
    "job_used_this_month": 5,
    "month_reset_at": datetime.now(),
    "created_at": datetime.now(),
    "updated_at": datetime.now()
}

class JobSchema(BaseModel):
    id: int
    user_id: int
    filename: str
    code: str
    status: Status
    result: str | None
    error_message: str | None
    tokens_used: int | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None

external_data_job = {
    "id": 1,
    "user_id": 1,
    "filename": "script.py",
    "code": "print('Hello, World!')",
    "status": Status.PENDING,
    "result": None,
    "error_message": None,
    "tokens_used": None,
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
    "completed_at": None
}

class JobStatus(enum.StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreate(BaseModel):
    filename: str
    code: str


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    filename: str
    code: str
    status: JobStatus
    result: str | None = None
    error_message: str | None = None
    tokens_used: int | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class JobStepSchema(BaseModel):
    id: int
    job_id: int
    step_name: str
    step_order: int
    input: str | None
    output: str | None
    tokens_used: int | None
    duration_ms: int | None
    created_at: datetime

external_data_job_step = {
    "id": 1,
    "job_id": 1,
    "step_name": "code_execution",
    "step_order": 1,
    "input": "print('Hello, World!')",
    "output": "Hello, World!",
    "tokens_used": 10,
    "duration_ms": 500,
    "created_at": datetime.now()
}

class SubscriptionSchema(BaseModel):
    user_id: int
    stripe_customer_id: str
    stripe_subscription_id: str
    plan: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    created_at: datetime
    updated_at: datetime
    canceled_at: datetime | None

external_data_subscription = {
    "user_id": 1,
    "stripe_customer_id": "cus_123",
    "stripe_subscription_id": "sub_123",
    "plan": "premium",
    "status": "active",
    "current_period_start": datetime.now(),
    "current_period_end": datetime.now(),
    "created_at": datetime.now(),
    "updated_at": datetime.now(),
    "canceled_at": None
}

class IntegrationSchema(BaseModel):
    id: int
    user_id: int
    type: str
    is_active: bool

external_data_integration = {
    "id": 1,
    "user_id": 1,
    "type": "github",
    "is_active": True
}


class CreateJobRequest(BaseModel):
    filename: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)

    @field_validator("filename")
    @classmethod
    def filename_must_have_valid_extension(cls, v: str) -> str:
        if not _sanitizer.validate_extension_file(v):
            raise ValueError("Filename must have a valid extension: .py, .txt, .md")
        return v

    @field_validator("code")
    @classmethod
    def code_must_be_safe(cls, v: str) -> str:
        if not _sanitizer.is_safe(v):
            raise ValueError("Code contains potentially unsafe or prompt injection patterns")
        return v


class CreateJobResponse(BaseModel):
    job_id: int
