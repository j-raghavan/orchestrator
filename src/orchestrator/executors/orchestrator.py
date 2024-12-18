import asyncio
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from result import Ok

from orchestrator.core import (
    OrchestratorConfig,
    Permission,
    Pipeline,
    Task,
    TaskResult,
    TaskStatus,
)
from orchestrator.executors.base import TaskExecutor
from orchestrator.monitoring.metrics import MetricsCollector
from orchestrator.monitoring.system import SystemLoadMonitor
from orchestrator.policies.circuit_breaker import CircuitBreaker
from orchestrator.queue import PriorityQueue
from orchestrator.queue.dead_letter import DeadLetterQueue
from orchestrator.utils.logging import OrchestrationLogger


class Orchestrator:
    def __init__(self, executor: TaskExecutor, config: OrchestratorConfig):
        self.executor = executor
        self.config = config

        # Core components
        self.pipeline_queue = PriorityQueue[Pipeline](maxsize=config.max_queue_size)
        self.active_pipelines: Dict[UUID, Pipeline] = {}
        self.results_cache: Dict[str, TaskResult] = {}
        self.dead_letter_queue = DeadLetterQueue(config.dead_letter_queue_size)

        # Circuit breakers
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        if config.enable_circuit_breaker:
            self.circuit_breakers = {}

        # Monitoring and metrics
        self.system_monitor = SystemLoadMonitor()
        self.metrics = MetricsCollector()

        # Callbacks
        self.failure_callbacks: List[Callable] = []
        self.success_callbacks: List[Callable] = []

        # Background tasks
        self._shutdown_event = asyncio.Event()
        self._pipeline_workers: List[asyncio.Task] = []
        self._cache_cleanup_task: Optional[asyncio.Task] = None
        self._load_monitor_task: Optional[asyncio.Task] = None

        # Logging
        logger_config = OrchestrationLogger(
            service_name="orchestrator", env="config.environment"
        )
        self.logger = logger_config.get_logger()

    def register_failure_callback(self, callback: Callable):
        """Register a callback to be called when a pipeline fails"""
        self.failure_callbacks.append(callback)

    def register_success_callback(self, callback: Callable):
        """Register a callback to be called when a pipeline succeeds"""
        self.success_callbacks.append(callback)

    def register_dead_letter_handler(self, handler: Callable):
        """Register a handler for dead letter queue items"""
        self.dead_letter_queue.add_handler(handler)

    async def start(self):
        """Start the orchestrator and its background tasks"""
        self.logger.info("starting_orchestrator")

        # Start pipeline workers
        for _ in range(self.config.max_parallel_pipelines):
            worker = asyncio.create_task(self._pipeline_worker())
            self._pipeline_workers.append(worker)

        # Start background tasks
        self._cache_cleanup_task = asyncio.create_task(
            self._cleanup_cache_periodically()
        )
        self._load_monitor_task = asyncio.create_task(self._monitor_system_load())

    async def shutdown(self):
        """Gracefully shutdown the orchestrator"""
        self.logger.info("shutting_down_orchestrator")
        self._shutdown_event.set()

        # Wait for queued pipelines to complete
        while not self.pipeline_queue.empty():
            await asyncio.sleep(1)

        # Cancel all background tasks
        tasks = []
        if self._cache_cleanup_task:
            tasks.append(self._cache_cleanup_task)
        if self._load_monitor_task:
            tasks.append(self._load_monitor_task)
        tasks.extend(self._pipeline_workers)

        for task in tasks:
            task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)
        self.logger.info("orchestrator_shutdown_complete")

    async def submit_pipeline(
        self, pipeline: Pipeline, user_context: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Submit a new pipeline for execution"""
        if user_context and not await self._check_permissions(
            user_context, Permission.EXECUTE
        ):
            raise PermissionError("Insufficient permissions")

        if self.pipeline_queue.qsize() >= self.config.max_queue_size:
            raise RuntimeError("Pipeline queue is full")

        # Check circuit breaker if enabled
        if self.config.enable_circuit_breaker:
            circuit_breaker = self.circuit_breakers.get(pipeline.name)
            if not circuit_breaker:
                circuit_breaker = CircuitBreaker(
                    self.config.circuit_breaker_threshold,
                    self.config.circuit_breaker_timeout_seconds,
                )
                self.circuit_breakers[pipeline.name] = circuit_breaker

            if not await circuit_breaker.can_execute():
                raise RuntimeError(
                    f"Circuit breaker is open for pipeline {pipeline.name}"
                )

        self.logger.info("submitting_pipeline", pipeline_id=pipeline.id)
        await self.pipeline_queue.put(
            pipeline, priority=max(t.priority.value for t in pipeline.tasks)
        )
        self.active_pipelines[pipeline.id] = pipeline
        return pipeline.id

    async def get_pipeline_status(self, pipeline_id: UUID) -> Optional[Pipeline]:
        """Get the current status of a pipeline"""
        return self.active_pipelines.get(pipeline_id)

    async def cancel_pipeline(self, pipeline_id: UUID) -> bool:
        """Cancel a running pipeline"""
        pipeline = self.active_pipelines.get(pipeline_id)
        if not pipeline:
            return False

        if pipeline.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            return False

        pipeline.status = TaskStatus.CANCELLED
        for task in pipeline.tasks:
            if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                task.status = TaskStatus.CANCELLED

        del self.active_pipelines[pipeline_id]
        return True

    async def retry_pipeline(self, pipeline_id: UUID) -> Optional[UUID]:
        """Retry a failed pipeline"""
        original_pipeline = self.active_pipelines.get(pipeline_id)
        if not original_pipeline:
            return None

        if original_pipeline.status != TaskStatus.FAILED:
            return None

        # Create a new pipeline with the same configuration
        new_pipeline = Pipeline(
            name=f"retry_{original_pipeline.name}",
            tasks=[
                Task(
                    name=task.name,
                    dependencies=task.dependencies,
                    retry_policy=task.retry_policy,
                    timeout_seconds=task.timeout_seconds,
                    cache_key=task.cache_key,
                    cache_ttl=task.cache_ttl,
                    recovery_policy=task.recovery_policy,
                    metadata=task.metadata.copy(),
                )
                for task in original_pipeline.tasks
            ],
            parallel_tasks=original_pipeline.parallel_tasks,
            timeout_seconds=original_pipeline.timeout_seconds,
            recovery_policy=original_pipeline.recovery_policy,
            metadata=original_pipeline.metadata.copy(),
        )

        return await self.submit_pipeline(new_pipeline)

    async def health_check(self) -> Dict[str, Any]:
        """Get health check information"""
        metrics = await self.system_monitor.get_detailed_metrics()
        task_metrics = await self.metrics.get_metrics()

        circuit_breaker_status = {
            name: {
                "is_open": breaker.is_open,
                "failure_count": breaker.failure_count,
                "last_failure": (
                    breaker.last_failure_time.isoformat()
                    if breaker.last_failure_time
                    else None
                ),
            }
            for name, breaker in self.circuit_breakers.items()
        }

        return {
            "status": "healthy",
            "queue_size": self.pipeline_queue.qsize(),
            "active_pipelines": len(self.active_pipelines),
            "worker_status": [w.done() for w in self._pipeline_workers],
            "cache_size": len(self.results_cache),
            "system_metrics": metrics,
            "task_metrics": task_metrics,
            "circuit_breakers": circuit_breaker_status,
            "dead_letter_queue_size": self.dead_letter_queue.queue.qsize(),
        }

    # ================ Private Methods ================

    async def _check_permissions(
        self, user_context: Dict[str, Any], required_permission: Permission
    ) -> bool:
        """Check if user has required permissions"""
        if not self.config.auth_endpoint:
            return True

        try:
            # Make request to auth endpoint
            # This is a placeholder - implement actual auth logic
            return True
        except Exception as e:
            self.logger.error("permission_check_failed", error=str(e))
            return False

    async def _cleanup_cache_periodically(self):
        """Periodically clean up expired cache entries"""
        while not self._shutdown_event.is_set():
            try:
                now = datetime.now()
                expired_keys = [
                    k
                    for k, v in self.results_cache.items()
                    if (now - v.timestamp)
                    > timedelta(seconds=self.config.cache_ttl_seconds)
                ]

                for k in expired_keys:
                    del self.results_cache[k]

                # Enforce cache size limit
                if len(self.results_cache) > self.config.cache_max_size:
                    sorted_items = sorted(
                        self.results_cache.items(), key=lambda x: x[1].timestamp
                    )
                    for k, _ in sorted_items[: -self.config.cache_max_size]:
                        del self.results_cache[k]

            except Exception as e:
                self.logger.error("cache_cleanup_error", error=str(e))

            await asyncio.sleep(3600)  # Clean up every hour

    async def _monitor_system_load(self):
        """Monitor system load and adjust resources accordingly"""
        while not self._shutdown_event.is_set():
            try:
                load = await self.system_monitor.get_load()
                if load > 0.8:  # High load threshold
                    self.logger.warning("high_system_load", load=load)
                    # Implement load shedding or scaling logic here
                await asyncio.sleep(60)
            except Exception as e:
                self.logger.error("load_monitor_error", error=str(e))
                await asyncio.sleep(60)

    async def _pipeline_worker(self):
        """Worker process that executes pipelines"""
        while not self._shutdown_event.is_set():
            try:
                # Try to get a pipeline from the queue
                try:
                    pipeline = await self.pipeline_queue.get()
                except asyncio.QueueEmpty:
                    # No pipeline available, wait a bit before trying again
                    await asyncio.sleep(1)
                    continue

                if not pipeline:
                    continue

                self.logger.info("pipeline_started", pipeline_id=pipeline.id)

                try:
                    await self._execute_pipeline(pipeline)
                    if pipeline.status == TaskStatus.COMPLETED:
                        self.logger.info(
                            "pipeline_completed",
                            pipeline_id=pipeline.id,
                            task_count=len(pipeline.tasks),
                        )
                        # Call success callbacks
                        for callback in self.success_callbacks:
                            try:
                                await callback(pipeline)
                            except Exception as callback_error:
                                self.logger.error(
                                    "success_callback_error", error=str(callback_error)
                                )
                except Exception as pipeline_error:
                    self.logger.error(
                        "pipeline_execution_failed",
                        pipeline_id=pipeline.id,
                        error=str(pipeline_error),
                    )
                    pipeline.status = TaskStatus.FAILED
                    await self._handle_pipeline_failure(pipeline, pipeline_error)
                finally:
                    if pipeline.status in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                        if pipeline.id in self.active_pipelines:
                            del self.active_pipelines[pipeline.id]

            except asyncio.CancelledError:
                break
            except Exception as worker_error:
                # Properly log the actual error instead of an empty error message
                self.logger.error(
                    "pipeline_worker_error",
                    error=str(worker_error),
                    error_type=type(worker_error).__name__,
                    traceback=str(worker_error.__traceback__),
                )
                # Add a small delay to prevent tight error loops
                await asyncio.sleep(1)

    async def _execute_pipeline(self, pipeline: Pipeline):
        """Execute a single pipeline with timeout handling"""
        if pipeline.status == TaskStatus.RUNNING:
            raise RuntimeError(f"Pipeline {pipeline.id} is already running")

        pipeline.status = TaskStatus.RUNNING
        pipeline.started_at = datetime.now()

        try:

            async def execute_with_timeout():
                execution_sets = self._create_execution_sets(pipeline.tasks)

                # Track task completion
                completed_task_ids = set()

                for task_set in execution_sets:
                    self.logger.info(
                        "executing_task_set",
                        pipeline_id=pipeline.id,
                        task_count=len(task_set),
                    )
                    await self._execute_task_set(task_set, pipeline.parallel_tasks)
                    completed_task_ids.update(task.id for task in task_set)

            if pipeline.timeout_seconds:
                try:
                    await asyncio.wait_for(
                        execute_with_timeout(), timeout=pipeline.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    pipeline.status = TaskStatus.FAILED
                    raise RuntimeError(
                        f"Pipeline timed out after {pipeline.timeout_seconds}s"
                    )
            else:
                await execute_with_timeout()

            # Check for failed tasks
            failed_tasks = [
                task for task in pipeline.tasks if task.status == TaskStatus.FAILED
            ]

            if failed_tasks:
                pipeline.status = TaskStatus.FAILED
                raise RuntimeError(
                    f"{len(failed_tasks)} tasks failed in pipeline: "
                    f"{[task.name for task in failed_tasks]}"
                )
            else:
                pipeline.status = TaskStatus.COMPLETED
                if self.config.enable_circuit_breaker:
                    circuit_breaker = self.circuit_breakers.get(pipeline.name)
                    if circuit_breaker:
                        await circuit_breaker.record_success()

        except Exception:
            pipeline.status = TaskStatus.FAILED
            if self.config.enable_circuit_breaker:
                circuit_breaker = self.circuit_breakers.get(pipeline.name)
                if circuit_breaker:
                    await circuit_breaker.record_failure()
            raise
        finally:
            pipeline.completed_at = datetime.now()

    def _create_execution_sets(self, tasks: List[Task]) -> List[List[Task]]:
        """Group tasks into sets that can be executed in parallel"""
        execution_sets = []
        remaining_tasks = tasks.copy()
        completed_tasks = set()

        while remaining_tasks:
            # Find tasks whose dependencies are satisfied
            executable_tasks = [
                task
                for task in remaining_tasks
                if task.dependencies.issubset(completed_tasks)
            ]

            if not executable_tasks:
                raise RuntimeError("Circular dependency detected in task graph")

            # Sort tasks by priority within the execution set
            executable_tasks.sort(key=lambda t: t.priority.value, reverse=True)

            execution_sets.append(executable_tasks)
            completed_tasks.update(task.id for task in executable_tasks)
            remaining_tasks = [
                task for task in remaining_tasks if task not in executable_tasks
            ]

        return execution_sets

    async def _execute_task_set(self, task_set: List[Task], parallel_tasks: int):
        """Execute a set of tasks in parallel with semaphore control"""
        semaphore = asyncio.Semaphore(parallel_tasks)

        # Group tasks by priority
        priority_groups = {}
        for task in task_set:
            priority = task.priority.value
            if priority not in priority_groups:
                priority_groups[priority] = []
            priority_groups[priority].append(task)

        # Execute tasks in priority order but allow parallel execution within same priority
        for priority in sorted(priority_groups.keys(), reverse=True):
            priority_tasks = priority_groups[priority]
            current_tasks = []

            for task in priority_tasks:
                self.logger.info(
                    "task_starting",
                    task_id=task.id,
                    task_name=task.name,
                    priority=task.priority.name,
                )
                current_tasks.append(self._execute_task_with_semaphore(task, semaphore))

            # Wait for all tasks in current priority group to complete
            if current_tasks:
                await asyncio.gather(*current_tasks, return_exceptions=True)

    async def _execute_task_with_semaphore(
        self, task: Task, semaphore: asyncio.Semaphore
    ):
        """Execute a single task with semaphore control"""
        async with semaphore:
            start_time = datetime.now()
            task.status = TaskStatus.RUNNING
            task.started_at = start_time

            try:
                self.logger.info(
                    "executing_task",
                    task_id=task.id,
                    task_name=task.name,
                    attempt=task.attempts + 1,
                )

                if task.timeout_seconds:
                    result = await asyncio.wait_for(
                        self._execute_task_with_retry(task),
                        timeout=task.timeout_seconds,
                    )
                else:
                    result = await self._execute_task_with_retry(task)

                task.result = result
                task.status = TaskStatus.COMPLETED

                # Record metrics
                duration = (datetime.now() - start_time).total_seconds()
                await self.metrics.record_task_success(
                    task_name=task.name, duration=duration
                )

                self.logger.info(
                    "task_completed",
                    task_id=task.id,
                    task_name=task.name,
                    duration=duration,
                )

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.result = TaskResult(success=False, error=str(e))
                await self.metrics.record_task_failure(
                    task_name=task.name, error_type=type(e).__name__
                )
                self.logger.error(
                    "task_failed", task_id=task.id, task_name=task.name, error=str(e)
                )
                await self._handle_task_failure(task, str(e))
                raise

            finally:
                task.completed_at = datetime.now()

    async def _execute_task_with_retry(self, task: Task) -> TaskResult:
        """Execute a task with retry logic"""
        last_error = None
        max_attempts = task.retry_policy.max_attempts if task.retry_policy else 1

        for attempt in range(max_attempts):
            task.attempts += 1

            try:
                result = await self.executor.execute(task)
                if isinstance(result, Ok):
                    return result.ok_value

                last_error = result.err_value

                if attempt < max_attempts - 1 and task.retry_policy:
                    task.status = TaskStatus.RETRYING
                    retry_delay = task.retry_policy.get_next_delay(task.attempts)
                    await asyncio.sleep(retry_delay)
                else:
                    break

            except Exception as e:
                last_error = str(e)
                if attempt < max_attempts - 1 and task.retry_policy:
                    task.status = TaskStatus.RETRYING
                    retry_delay = task.retry_policy.get_next_delay(task.attempts)
                    await asyncio.sleep(retry_delay)
                else:
                    break

        raise RuntimeError(f"Task failed after {task.attempts} attempts: {last_error}")

    async def _handle_task_failure(self, task: Task, error: str):
        """Handle task failure with dead letter queue and notification"""
        await self.dead_letter_queue.put(
            {
                "task_id": task.id,
                "task_name": task.name,
                "error": error,
                "attempts": task.attempts,
                "timestamp": datetime.now().isoformat(),
            }
        )

        self.logger.error(
            "task_failure",
            task_id=task.id,
            task_name=task.name,
            error=error,
            attempts=task.attempts,
        )

        # Attempt task-level recovery if policy exists
        if (
            task.recovery_policy
            and task.attempts < task.recovery_policy.max_recovery_attempts
        ):
            try:
                await self._attempt_task_recovery(task)
            except Exception as recovery_error:
                self.logger.error(
                    "task_recovery_failed", task_id=task.id, error=str(recovery_error)
                )

    async def _attempt_task_recovery(self, task: Task):
        """Attempt to recover a failed task based on its recovery policy"""
        if not task.recovery_policy:
            return

        self.logger.info(
            "attempting_task_recovery", task_id=task.id, task_name=task.name
        )

        # Reset task status for retry
        task.status = TaskStatus.PENDING
        task.result = None
        task.started_at = None
        task.completed_at = None

        # Wait for recovery delay
        await asyncio.sleep(task.recovery_policy.recovery_delay_seconds)

        try:
            # Execute task with original configuration
            result = await self._execute_task_with_retry(task)
            task.result = result
            task.status = TaskStatus.COMPLETED

            self.logger.info(
                "task_recovery_succeeded", task_id=task.id, task_name=task.name
            )
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.result = TaskResult(
                success=False, error=f"Recovery attempt failed: {str(e)}"
            )
            raise

    async def _handle_pipeline_failure(self, pipeline: Pipeline, error: Exception):
        """Handle pipeline failure and attempt recovery if configured"""
        self.logger.error(
            "pipeline_failure",
            pipeline_id=pipeline.id,
            error=str(error),
            task_count=len(pipeline.tasks),
            failed_tasks=[
                t.id for t in pipeline.tasks if t.status == TaskStatus.FAILED
            ],
        )

        # Add to dead letter queue
        await self.dead_letter_queue.put(
            {
                "pipeline_id": pipeline.id,
                "pipeline_name": pipeline.name,
                "error": str(error),
                "failed_tasks": [
                    {
                        "id": task.id,
                        "name": task.name,
                        "error": task.result.error if task.result else None,
                    }
                    for task in pipeline.tasks
                    if task.status == TaskStatus.FAILED
                ],
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Execute failure callbacks
        for callback in self.failure_callbacks:
            try:
                await callback(pipeline, error)
            except Exception as callback_error:
                self.logger.error(
                    "failure_callback_error",
                    pipeline_id=pipeline.id,
                    error=str(callback_error),
                )

        # Attempt recovery if policy exists
        if pipeline.recovery_policy:
            try:
                await self._attempt_pipeline_recovery(pipeline)
            except Exception as recovery_error:
                self.logger.error(
                    "pipeline_recovery_failed",
                    pipeline_id=pipeline.id,
                    error=str(recovery_error),
                )

    async def _attempt_pipeline_recovery(self, pipeline: Pipeline):
        """Attempt to recover a failed pipeline based on its recovery policy"""
        if not pipeline.recovery_policy:
            return

        self.logger.info(
            "attempting_pipeline_recovery",
            pipeline_id=pipeline.id,
            pipeline_name=pipeline.name,
        )

        # Create recovery pipeline
        tasks_to_retry = (
            [t for t in pipeline.tasks if t.status == TaskStatus.FAILED]
            if pipeline.recovery_policy.retry_failed_tasks_only
            else pipeline.tasks
        )

        recovery_pipeline = Pipeline(
            name=f"recovery_{pipeline.name}",
            tasks=[
                Task(
                    name=task.name,
                    dependencies=task.dependencies,
                    retry_policy=task.retry_policy,
                    timeout_seconds=task.timeout_seconds,
                    cache_key=task.cache_key,
                    cache_ttl=task.cache_ttl,
                    recovery_policy=task.recovery_policy,
                    metadata=task.metadata.copy(),
                )
                for task in tasks_to_retry
            ],
            parallel_tasks=pipeline.parallel_tasks,
            timeout_seconds=pipeline.timeout_seconds,
            recovery_policy=pipeline.recovery_policy,
            metadata=pipeline.metadata.copy(),
        )

        # Wait for recovery delay
        await asyncio.sleep(pipeline.recovery_policy.recovery_delay_seconds)

        try:
            # Submit recovery pipeline
            recovery_pipeline_id = await self.submit_pipeline(recovery_pipeline)
            self.logger.info(
                "recovery_pipeline_submitted",
                original_pipeline_id=pipeline.id,
                recovery_pipeline_id=recovery_pipeline_id,
            )
        except Exception as e:
            self.logger.error(
                "recovery_pipeline_submission_failed",
                pipeline_id=pipeline.id,
                error=str(e),
            )
            raise

    async def get_metrics_report(self) -> Dict[str, Any]:
        """Get a comprehensive metrics report"""
        metrics = await self.metrics.get_metrics()
        system_metrics = await self.system_monitor.get_detailed_metrics()

        return {
            "task_metrics": metrics,
            "system_metrics": system_metrics,
            "pipeline_stats": {
                "active_pipelines": len(self.active_pipelines),
                "queue_size": self.pipeline_queue.qsize(),
            },
            "cache_stats": {
                "size": len(self.results_cache),
                "max_size": self.config.cache_max_size,
            },
            "circuit_breakers": {
                name: {
                    "is_open": breaker.is_open,
                    "failure_count": breaker.failure_count,
                    "last_failure": (
                        breaker.last_failure_time.isoformat()
                        if breaker.last_failure_time
                        else None
                    ),
                }
                for name, breaker in self.circuit_breakers.items()
            },
            "dead_letter_queue_size": self.dead_letter_queue.queue.qsize(),
        }
