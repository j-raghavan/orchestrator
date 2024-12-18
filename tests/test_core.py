import pytest


from orchestrator.core.models import TaskStatus, TaskPriority
from orchestrator.core.task import Task, TaskResult
from orchestrator.core.pipeline import Pipeline
from orchestrator.policies.retry import RetryPolicy
from orchestrator.policies.recovery import RecoveryPolicy


@pytest.mark.asyncio
class TestTask:
    async def test_task_creation(self):
        task = Task(name="test_task", priority=TaskPriority.HIGH)
        assert task.name == "test_task"
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
        assert task.attempts == 0

    async def test_task_with_retry_policy(self):
        retry_policy = RetryPolicy(
            max_attempts=3, delay_seconds=1, exponential_backoff=True
        )
        task = Task(name="test_task", retry_policy=retry_policy)
        assert task.retry_policy.max_attempts == 3
        assert task.retry_policy.delay_seconds == 1
        assert task.retry_policy.exponential_backoff is True

    async def test_task_with_dependencies(self):
        task1 = Task(name="task1")
        task2 = Task(name="task2", dependencies={task1.id})
        assert task1.id in task2.dependencies

    async def test_task_result_creation(self):
        result = TaskResult(success=True, data={"key": "value"}, metrics={"time": 1.0})
        assert result.success is True
        assert result.data["key"] == "value"
        assert result.metrics["time"] == 1.0


@pytest.mark.asyncio
class TestPipeline:
    async def test_pipeline_creation(self, sample_tasks):
        pipeline = Pipeline(name="test_pipeline", tasks=sample_tasks, parallel_tasks=2)
        assert pipeline.name == "test_pipeline"
        assert len(pipeline.tasks) == 3
        assert pipeline.parallel_tasks == 2
        assert pipeline.status == TaskStatus.PENDING

    async def test_pipeline_with_recovery_policy(self, sample_tasks):
        recovery_policy = RecoveryPolicy(
            max_recovery_attempts=2, recovery_delay_seconds=30
        )
        pipeline = Pipeline(
            name="test_pipeline", tasks=sample_tasks, recovery_policy=recovery_policy
        )
        assert pipeline.recovery_policy.max_recovery_attempts == 2
        assert pipeline.recovery_policy.recovery_delay_seconds == 30

    async def test_pipeline_validation(self):
        with pytest.raises(ValueError):
            Pipeline(
                name="test_pipeline",
                tasks=[],  # Empty task list should raise error
                parallel_tasks=2,
            )

        with pytest.raises(ValueError):
            Pipeline(
                name="",  # Empty name should raise error
                tasks=[Task(name="task1")],
                parallel_tasks=2,
            )
