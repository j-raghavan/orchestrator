from __future__ import annotations

import asyncio
from typing import Any, Callable, List

import structlog


class DeadLetterQueue:
    def __init__(self, maxsize: int = 1000):
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self._handlers: List[Callable] = []

    async def put(self, item: Any):
        await self.queue.put(item)
        for handler in self._handlers:
            try:
                await handler(item)
            except Exception as e:
                structlog.get_logger().error(
                    "dead_letter_queue_handler_error", error=str(e)
                )

    async def get(self):
        return await self.queue.get()

    def add_handler(self, handler: Callable):
        self._handlers.append(handler)
