from abc import ABC, abstractmethod

from result import Result

from orchestrator.core.task import Task, TaskResult


class TaskExecutor(ABC):
    @abstractmethod
    async def execute(self, task: Task) -> Result[TaskResult, str]:
        pass
