import enum
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, EmailStr, Field, PositiveInt

from models.model import Status

# Use schema example user = CreateUserSchema(**external_data_user) to create a user schema instance from external data.

class CreateUserSchema(BaseModel):
    id: int
    clerk_id: str
    email: EmailStr
    plan: Optional[str]
    job_used_this_month: int
    month_reset_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

class ResponseUserSchema(BaseModel):
    id: int
    email: EmailStr
    plan: Optional[str]
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
    result: Optional[str]
    error_message: Optional[str]
    tokens_used: Optional[int]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

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

class JobStatus(str, enum.Enum):
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
    result: Optional[str] = None
    error_message: Optional[str] = None
    tokens_used: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class JobStepSchema(BaseModel):
    id: int
    job_id: int
    step_name: str
    step_order: int
    input: Optional[str]
    output: Optional[str]
    tokens_used: Optional[int]
    duration_ms: Optional[int]
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
    canceled_at: Optional[datetime]

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
