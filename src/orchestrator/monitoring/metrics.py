import asyncio
from typing import Any, Dict


class MetricsCollector:
    def __init__(self):
        self.metrics = {}
        self._lock = asyncio.Lock()

    async def _initialize_metrics(self, task_name: str):
        if task_name not in self.metrics:
            self.metrics[task_name] = {
                "success_count": 0,
                "failure_count": 0,
                "total_duration": 0,
                "average_duration": 0,
                "errors": {},
            }

    async def record_task_success(self, task_name: str, duration: float):
        async with self._lock:
            await self._initialize_metrics(task_name)

            self.metrics[task_name]["success_count"] += 1
            self.metrics[task_name]["total_duration"] += duration
            self.metrics[task_name]["average_duration"] = (
                self.metrics[task_name]["total_duration"]
                / self.metrics[task_name]["success_count"]
            )

    async def record_task_failure(self, task_name: str, error_type: str):
        async with self._lock:
            await self._initialize_metrics(task_name)

            self.metrics[task_name]["failure_count"] += 1
            self.metrics[task_name]["errors"][error_type] = (
                self.metrics[task_name]["errors"].get(error_type, 0) + 1
            )

    async def get_metrics(self) -> Dict[str, Any]:
        async with self._lock:
            return self.metrics.copy()
