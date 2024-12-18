from pydantic import BaseModel, Field


class RecoveryPolicy(BaseModel):
    max_recovery_attempts: int = Field(
        default=3, ge=1, description="Must be greater than or equal to 1"
    )
    recovery_delay_seconds: int = Field(
        default=60, ge=1, description="Must be greater than or equal to 1"
    )
    retry_failed_tasks_only: bool = True
    notify_on_recovery: bool = True
