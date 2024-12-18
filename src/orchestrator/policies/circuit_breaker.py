import asyncio
from datetime import datetime
from typing import Optional


class CircuitBreaker:
    def __init__(self, threshold: int, timeout_seconds: int):
        self.threshold = threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.is_open = False
        self._lock = asyncio.Lock()

    async def record_failure(self):
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            if self.failure_count >= self.threshold:
                self.is_open = True

    async def record_success(self):
        async with self._lock:
            self.failure_count = 0
            self.is_open = False

    async def can_execute(self) -> bool:
        if not self.is_open:
            return True

        if (
            self.last_failure_time
            and (datetime.now() - self.last_failure_time).total_seconds()
            > self.timeout_seconds
        ):
            async with self._lock:
                self.is_open = False
                self.failure_count = 0
                return True

        return False
