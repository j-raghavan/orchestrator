import asyncio
from typing import Dict

import psutil


class SystemLoadMonitor:
    def __init__(
        self,
        cpu_weight: float = 0.7,
        memory_weight: float = 0.3,
        smoothing_factor: float = 0.3,
    ):
        self.cpu_weight = cpu_weight
        self.memory_weight = memory_weight
        self.smoothing_factor = smoothing_factor
        self._last_load = 0.0
        self._lock = asyncio.Lock()

    async def get_load(self) -> float:
        async with self._lock:
            cpu_percent = psutil.cpu_percent(interval=0.1) / 100.0
            memory = psutil.virtual_memory()
            memory_percent = memory.percent / 100.0

            current_load = (
                self.cpu_weight * cpu_percent + self.memory_weight * memory_percent
            )

            smoothed_load = (
                self.smoothing_factor * current_load
                + (1 - self.smoothing_factor) * self._last_load
            )

            self._last_load = smoothed_load
            return smoothed_load

    async def get_detailed_metrics(self) -> Dict[str, float]:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage("/").percent,
            "swap_percent": psutil.swap_memory().percent,
        }
