from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator

from orchestrator.core.models import TaskStatus
from orchestrator.core.task import Task
from orchestrator.policies.recovery import RecoveryPolicy


class Pipeline(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., min_length=1, max_length=256)
    tasks: List[Task]
    parallel_tasks: int = Field(5, ge=1, le=100)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=86400)
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    recovery_policy: Optional[RecoveryPolicy] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator("tasks")
    def validate_tasks(cls, v):
        if not v:
            raise ValueError("Pipeline must have at least one task")
        if len(v) > 1000:
            raise ValueError("Too many tasks in pipeline")
        return v

    class Config:
        arbitrary_types_allowed = True
