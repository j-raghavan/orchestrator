from pydantic import BaseModel, Field
from typing import Optional


class OrchestratorConfig(BaseModel):
    max_parallel_pipelines: int = Field(10, ge=1, le=100)
    max_queue_size: int = Field(1000, ge=1, le=10000)
    cache_ttl_seconds: int = Field(86400, ge=1)  # 24 hours
    cache_max_size: int = Field(10000, ge=1)
    secret_key: str
    auth_endpoint: Optional[str]
    enable_circuit_breaker: bool = True
    circuit_breaker_threshold: int = Field(5, ge=1)
    circuit_breaker_timeout_seconds: int = Field(300, ge=1)
    dead_letter_queue_size: int = Field(1000, ge=1)

    class Config:
        env_file = ".env"
        env_prefix = "ORCHESTRATOR_"
