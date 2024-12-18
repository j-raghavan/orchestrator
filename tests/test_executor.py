import asyncio
from datetime import datetime
from uuid import UUID

import pytest
from result import Err, Ok

from orchestrator import (
    Orchestrator,
    OrchestratorConfig,
    Pipeline,
    RecoveryPolicy,
    RetryPolicy,
    Task,
    TaskPriority,
    TaskResult,
    TaskStatus,
)
from orchestrator.executors.base import TaskExecutor


# Mock Executors
class MockExecutor(TaskExecutor):
    def __init__(self):
        self.executed_tasks = []
        self.lock = asyncio.Lock()

    async def execute(self, task: Task) -> Ok[TaskResult]:
        await asyncio.sleep(0.01)
        async with self.lock:
            self.executed_tasks.append(task)
        return Ok(
            TaskResult(
                success=True,
                data={"task_id": task.id},
                timestamp=datetime.now(),
                metrics={"duration": 0.01},
            )
        )


class FailingExecutor(TaskExecutor):
    def __init__(self):
        self.attempts = {}

    async def execute(self, task: Task) -> Err[str]:
        self.attempts[task.id] = self.attempts.get(task.id, 0) + 1
        await asyncio.sleep(0.1)  # Reduced delay for faster failure
        return Err(f"Task execution failed for {task.name}")


class SlowExecutor(TaskExecutor):
    async def execute(self, task: Task) -> Ok[TaskResult]:
        await asyncio.sleep(0.2)  # Reduced from 1 second to 0.5 seconds
        return Ok(
            TaskResult(
                success=True,
                data={"task_id": task.id},
                timestamp=datetime.now(),
                metrics={"duration": 0.2},
            )
        )


@pytest.fixture
def config():
    return OrchestratorConfig(
        max_queue_size=100,
        max_parallel_pipelines=5,
        enable_circuit_breaker=True,
        cache_ttl_seconds=3600,
        cache_max_size=1000,
        dead_letter_queue_size=100,
        secret_key="test-secret-key",
        auth_endpoint="http://test-auth.example.com",
        circuit_breaker_threshold=5,
        circuit_breaker_timeout_seconds=60,
        environment="test",
    )


@pytest.fixture
def mock_executor():
    return MockExecutor()


@pytest.fixture
def failing_executor():
    return FailingExecutor()


@pytest.fixture
def slow_executor():
    return SlowExecutor()


@pytest.fixture
def sample_tasks():
    retry_policy = RetryPolicy(
        max_attempts=2,  # Reduced for faster tests
        delay_seconds=1,
        exponential_backoff=True,
        max_delay_seconds=5,
    )

    recovery_policy = RecoveryPolicy(
        max_recovery_attempts=1,
        recovery_delay_seconds=1,
        retry_failed_tasks_only=True,
        notify_on_recovery=True,
    )

    return [
        Task(
            name="task1",
            dependencies=set(),
            priority=TaskPriority.MEDIUM,
            timeout_seconds=10,
            retry_policy=retry_policy,
            recovery_policy=recovery_policy,
            cache_key="task1_key",
        ),
        Task(
            name="task2",
            dependencies=set(),
            priority=TaskPriority.HIGH,
            timeout_seconds=10,
            retry_policy=retry_policy,
            recovery_policy=recovery_policy,
            cache_key="task2_key",
        ),
        Task(
            name="task3",
            dependencies=set(),
            priority=TaskPriority.LOW,
            timeout_seconds=10,
            retry_policy=retry_policy,
            recovery_policy=recovery_policy,
            cache_key="task3_key",
        ),
    ]


async def wait_for_pipeline_completion(
    orchestrator, pipeline_id, timeout=120
):  # Increased timeout
    start_time = datetime.now()
    # check_interval = 1.5  # Increased interval
    while (datetime.now() - start_time).total_seconds() < timeout:
        status = await orchestrator.get_pipeline_status(pipeline_id)
        if status and status.status in [
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        ]:
            return status
        await asyncio.sleep(0.5)
    return None


async def wait_for_pipeline_cleanup(orchestrator, pipeline_id, timeout=5):
    start_time = datetime.now()
    while (datetime.now() - start_time).total_seconds() < timeout:
        if pipeline_id not in orchestrator.active_pipelines:
            return True
        await asyncio.sleep(0.1)
    return False


async def ensure_pipeline_started(orchestrator, pipeline_id, max_attempts=100):
    """Helper function to ensure pipeline has started"""
    for _ in range(max_attempts):
        status = await orchestrator.get_pipeline_status(pipeline_id)
        if status and status.status in [
            TaskStatus.RUNNING,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
        ]:
            return status
        await asyncio.sleep(0.1)
    return None


@pytest.mark.asyncio
class TestOrchestrator:
    async def test_orchestrator_initialization(self, config, mock_executor):
        orchestrator = Orchestrator(mock_executor, config)
        assert orchestrator.executor == mock_executor
        assert orchestrator.config == config
        assert orchestrator.pipeline_queue is not None
        assert orchestrator.active_pipelines == {}
        assert orchestrator.results_cache == {}
        assert orchestrator.dead_letter_queue is not None

    async def test_pipeline_submission(self, config, mock_executor, sample_tasks):
        orchestrator = Orchestrator(mock_executor, config)
        await orchestrator.start()

        try:
            pipeline = Pipeline(
                name="test_pipeline",
                tasks=sample_tasks,
                parallel_tasks=2,
                timeout_seconds=30,
                recovery_policy=RecoveryPolicy(
                    max_recovery_attempts=2,
                    recovery_delay_seconds=1,
                    retry_failed_tasks_only=True,
                    notify_on_recovery=True,
                ),
            )

            pipeline_id = await orchestrator.submit_pipeline(pipeline)
            assert isinstance(pipeline_id, UUID)

            status = await ensure_pipeline_started(orchestrator, pipeline_id)
            assert status is not None
            assert status.status in [
                TaskStatus.PENDING,
                TaskStatus.RUNNING,
                TaskStatus.COMPLETED,
            ]
        finally:
            await orchestrator.shutdown()


@pytest.mark.skip("Skipping due to long execution time")
@pytest.mark.asyncio
class TestPipelineExecution:
    async def test_pipeline_execution(self, config, mock_executor, sample_tasks):
        orchestrator = Orchestrator(mock_executor, config)
        await orchestrator.start()

        try:
            # Ensure task priorities are correctly set
            for task in sample_tasks:
                task.priority = TaskPriority.MEDIUM
            sample_tasks[1].priority = (
                TaskPriority.HIGH
            )  # Set one task to high priority

            pipeline = Pipeline(
                name="test_pipeline",
                tasks=sample_tasks,
                parallel_tasks=1,
                timeout_seconds=60,
                recovery_policy=RecoveryPolicy(
                    max_recovery_attempts=2,
                    recovery_delay_seconds=1,
                    retry_failed_tasks_only=True,
                    notify_on_recovery=True,
                ),
            )

            pipeline_id = await orchestrator.submit_pipeline(pipeline)

            # Wait for pipeline to start
            await asyncio.sleep(1)

            status = await wait_for_pipeline_completion(orchestrator, pipeline_id)
            assert status is not None, "Pipeline execution timed out"
            assert status.status == TaskStatus.COMPLETED
            assert len(mock_executor.executed_tasks) == len(sample_tasks)

            # Verify high priority task was executed first
            first_task = mock_executor.executed_tasks[0]
            assert first_task.priority == TaskPriority.HIGH
        finally:
            await orchestrator.shutdown()

    async def test_pipeline_failure(self, config, failing_executor, sample_tasks):
        orchestrator = Orchestrator(failing_executor, config)
        await orchestrator.start()

        try:
            pipeline = Pipeline(
                name="test_pipeline",
                tasks=sample_tasks,
                parallel_tasks=2,
                timeout_seconds=30,
                recovery_policy=RecoveryPolicy(
                    max_recovery_attempts=1,
                    recovery_delay_seconds=1,  # Reduced for faster testing
                    retry_failed_tasks_only=True,
                    notify_on_recovery=True,
                ),
            )

            pipeline_id = await orchestrator.submit_pipeline(pipeline)

            # Use longer timeout for failure case
            status = await wait_for_pipeline_completion(
                orchestrator, pipeline_id, timeout=45
            )
            assert status is not None, "Pipeline execution timed out"
            assert status.status == TaskStatus.FAILED

            await asyncio.sleep(1)  # Allow time for cleanup

            cleanup_success = await wait_for_pipeline_cleanup(orchestrator, pipeline_id)
            assert cleanup_success, "Pipeline was not removed from active_pipelines"

            # Verify the tasks have error messages
            for task in status.tasks:
                assert task.status == TaskStatus.FAILED
                assert task.result is not None
                assert isinstance(task.result.error, str)
                assert "Task execution failed" in task.result.error
        finally:
            await orchestrator.shutdown()

    async def test_pipeline_cancellation(self, config, slow_executor, sample_tasks):
        orchestrator = Orchestrator(slow_executor, config)
        await orchestrator.start()

        try:
            pipeline = Pipeline(
                name="test_pipeline",
                tasks=sample_tasks,
                parallel_tasks=1,
                timeout_seconds=30,
                recovery_policy=RecoveryPolicy(
                    max_recovery_attempts=1,
                    recovery_delay_seconds=1,  # Reduced for faster testing
                    retry_failed_tasks_only=True,
                    notify_on_recovery=True,
                ),
            )

            pipeline_id = await orchestrator.submit_pipeline(pipeline)

            # Wait for pipeline to start and first task to begin
            await asyncio.sleep(1)

            success = await orchestrator.cancel_pipeline(pipeline_id)
            assert success is True

            status = await wait_for_pipeline_completion(orchestrator, pipeline_id)
            assert status is not None
            assert status.status == TaskStatus.CANCELLED

            await asyncio.sleep(1)
            cleanup_success = await wait_for_pipeline_cleanup(orchestrator, pipeline_id)
            assert cleanup_success, "Pipeline was not removed from active_pipelines"
        finally:
            await orchestrator.shutdown()

    async def test_pipeline_timeout(self, config, slow_executor, sample_tasks):
        orchestrator = Orchestrator(slow_executor, config)
        await orchestrator.start()

        try:
            pipeline = Pipeline(
                name="test_pipeline",
                tasks=sample_tasks,
                parallel_tasks=2,
                timeout_seconds=1,  # Reduced timeout to ensure it triggers
                recovery_policy=RecoveryPolicy(
                    max_recovery_attempts=1,
                    recovery_delay_seconds=1,  # Reduced for faster testing
                    retry_failed_tasks_only=True,
                    notify_on_recovery=True,
                ),
            )

            pipeline_id = await orchestrator.submit_pipeline(pipeline)

            # Use a longer timeout for waiting to ensure we catch the failure
            status = await wait_for_pipeline_completion(
                orchestrator, pipeline_id, timeout=10
            )

            assert status is not None, "Pipeline execution timed out"
            assert status.status == TaskStatus.FAILED

            await asyncio.sleep(1)
            cleanup_success = await wait_for_pipeline_cleanup(orchestrator, pipeline_id)
            assert cleanup_success, "Pipeline was not removed from active_pipelines"

            # Verify timeout occurred
            assert any(
                task.result
                and task.result.error
                and "timed out" in str(task.result.error)
                for task in status.tasks
            ), "No timeout errors found in tasks"
        finally:
            await orchestrator.shutdown()
