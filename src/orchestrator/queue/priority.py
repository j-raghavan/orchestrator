from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(order=True)
class PrioritizedItem(Generic[T]):
    priority: int
    timestamp: datetime
    item: T


class PriorityQueue(Generic[T]):
    def __init__(self, maxsize: int = 0):
        self._queue: list[PrioritizedItem[T]] = []
        self._maxsize = maxsize
        self._lock = asyncio.Lock()

    async def put(self, item: T, priority: int) -> None:
        async with self._lock:
            if self._maxsize > 0 and len(self._queue) >= self._maxsize:
                raise asyncio.QueueFull()

            prioritized_item = PrioritizedItem(
                priority=-priority, timestamp=datetime.now(), item=item
            )
            heapq.heappush(self._queue, prioritized_item)

    async def get(self) -> T:
        async with self._lock:
            if not self._queue:
                raise asyncio.QueueEmpty()
            return heapq.heappop(self._queue).item

    def empty(self) -> bool:
        return len(self._queue) == 0

    def qsize(self) -> int:
        return len(self._queue)
