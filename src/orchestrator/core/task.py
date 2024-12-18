from datetime import datetime
from typing import Any, Dict, Optional, Set
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from orchestrator.core.models import TaskPriority, TaskStatus
from orchestrator.policies import RecoveryPolicy, RetryPolicy


class TaskResult(BaseModel):
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class Task(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=256)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: Set[UUID] = set()
    retry_policy: Optional[RetryPolicy] = None
    timeout_seconds: Optional[int] = Field(None, ge=1, le=86400)
    attempts: int = 0
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[TaskResult] = None
    cache_key: Optional[str] = None
    cache_ttl: Optional[int] = Field(None, ge=1, le=86400)
    recovery_policy: Optional[RecoveryPolicy] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("dependencies")
    def validate_dependencies(cls, v):
        if len(v) > 100:
            raise ValueError("Too many dependencies")
        return v

    class Config:
        arbitrary_types_allowed = True
