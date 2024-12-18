import asyncio
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent / "src"))

from result import Err, Ok

from orchestrator import (
    OrchestratorConfig,
    Task,
    TaskExecutor,
    TaskPriority,
    TaskResult,
)


@pytest.fixture
def config():
    return OrchestratorConfig(
        max_parallel_pipelines=5,
        max_queue_size=100,
        cache_ttl_seconds=3600,
        cache_max_size=1000,
        secret_key="test_secret",
        auth_endpoint=None,
        enable_circuit_breaker=True,
        circuit_breaker_threshold=5,
        circuit_breaker_timeout_seconds=300,
        dead_letter_queue_size=1000,
    )


class MockTaskExecutor(TaskExecutor):
    def __init__(self, should_fail: bool = False, delay: float = 0):
        self.should_fail = should_fail
        self.delay = delay
        self.executed_tasks: list[Task] = []

    async def execute(self, task: Task) -> Ok[TaskResult] | Err[str]:
        self.executed_tasks.append(task)
        if self.delay:
            await asyncio.sleep(self.delay)

        if self.should_fail:
            return Err("Task failed deliberately")

        return Ok(
            TaskResult(
                success=True,
                data={
                    "execution_time": datetime.now().isoformat(),
                    "task_name": task.name,
                    "attempt": task.attempts,
                },
                metrics={"processing_time": 1.0, "memory_usage": 100.0},
            )
        )


@pytest.fixture
def mock_executor():
    return MockTaskExecutor()


@pytest.fixture
def failing_executor():
    return MockTaskExecutor(should_fail=True)


@pytest.fixture
def slow_executor():
    return MockTaskExecutor(delay=2.0)


@pytest.fixture
def sample_task():
    return Task(name="test_task", priority=TaskPriority.MEDIUM, timeout_seconds=30)


@pytest.fixture
def sample_tasks():
    task1 = Task(name="task1", priority=TaskPriority.HIGH)
    task2 = Task(name="task2", priority=TaskPriority.MEDIUM, dependencies={task1.id})
    task3 = Task(name="task3", priority=TaskPriority.LOW, dependencies={task2.id})
    return [task1, task2, task3]
