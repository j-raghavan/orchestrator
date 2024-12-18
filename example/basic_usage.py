import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

sys.path.append(str(Path(__file__).parent.parent / "src"))
from result import Err, Ok

from orchestrator import (
    Orchestrator,
    OrchestratorConfig,
    Pipeline,
    RecoveryPolicy,
    RetryPolicy,
    Task,
    TaskExecutor,
    TaskPriority,
    TaskResult,
    TaskStatus,
)


# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'

# Status symbols
class Symbols:
    PENDING = "○"
    RUNNING = "◐"
    COMPLETED = "✓"
    FAILED = "✗"
    RETRYING = "↻"
    ARROW = "→"

def format_duration(seconds: float) -> str:
    """Format duration in a human-readable way"""
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    seconds = seconds % 60
    return f"{minutes}m {seconds:.2f}s"

def format_task_status(status: TaskStatus) -> str:
    """Format task status with color and symbol"""
    status_formats = {
        TaskStatus.PENDING: (Colors.DIM, Symbols.PENDING, "PENDING"),
        TaskStatus.RUNNING: (Colors.BLUE, Symbols.RUNNING, "RUNNING"),
        TaskStatus.COMPLETED: (Colors.GREEN, Symbols.COMPLETED, "COMPLETED"),
        TaskStatus.FAILED: (Colors.RED, Symbols.FAILED, "FAILED"),
        TaskStatus.RETRYING: (Colors.YELLOW, Symbols.RETRYING, "RETRYING"),
    }
    color, symbol, text = status_formats[status]
    return f"{color}{symbol} {text}{Colors.ENDC}"

class ExampleTaskExecutor(TaskExecutor):
    """Example task executor that simulates different task behaviors"""

    async def execute(self, task: Task) -> Ok[TaskResult] | Err[str]:
        print(f"\n{Colors.BOLD}Executing:{Colors.ENDC} {task.name} (Attempt {task.attempts})")

        await asyncio.sleep(1)

        if task.name.startswith("fail"):
            return Err("Task failed deliberately")

        if task.name.startswith("slow"):
            print(f"{Colors.BLUE}Starting long operation...{Colors.ENDC}")
            await asyncio.sleep(5)
            print(f"{Colors.GREEN}Operation completed{Colors.ENDC}")

        if task.name.startswith("flaky"):
            if task.attempts == 1:
                print(f"{Colors.YELLOW}Failed on first attempt (will retry){Colors.ENDC}")
                return Err("Flaky task failed but can be retried")
            print(f"{Colors.GREEN}Succeeded on retry{Colors.ENDC}")

        return Ok(TaskResult(
            success=True,
            data={
                "execution_time": datetime.now().isoformat(),
                "task_name": task.name,
                "attempt": task.attempts
            },
            metrics={
                "processing_time": 1.0,
                "memory_usage": 100.0
            }
        ))

async def print_pipeline_status(status, clear_line=True):
    """Print formatted pipeline status"""
    if clear_line:
        print("\033[2K\r", end="")  # Clear line

    task_counts = {
        'pending': 0,
        'running': 0,
        'completed': 0,
        'failed': 0,
        'retrying': 0
    }

    for task in status.tasks:
        task_counts[task.status.value.lower()] += 1

    status_str = (
        f"{Colors.BOLD}Pipeline Status:{Colors.ENDC} {format_task_status(status.status)}\n"
        f"{Colors.BLUE}{Symbols.RUNNING} Running: {task_counts['running']}  "
        f"{Colors.GREEN}{Symbols.COMPLETED} Completed: {task_counts['completed']}  "
        f"{Colors.RED}{Symbols.FAILED} Failed: {task_counts['failed']}  "
        f"{Colors.YELLOW}{Symbols.RETRYING} Retrying: {task_counts['retrying']}  "
        f"{Colors.DIM}{Symbols.PENDING} Pending: {task_counts['pending']}{Colors.ENDC}"
    )

    print(status_str)

def print_task_summary(pipeline: Pipeline):
    """Print formatted task execution summary"""
    print(f"\n{Colors.BOLD}Task Execution Summary:{Colors.ENDC}")

    for task in pipeline.tasks:
        duration = (task.completed_at - task.started_at).total_seconds() if task.completed_at and task.started_at else 0
        status_str = format_task_status(task.status)
        print(f"{status_str:<30} {task.name:<20} Duration: {format_duration(duration):<8} Attempts: {task.attempts}")

def print_metrics_report(metrics: Dict[str, Any]):
    """Print formatted metrics report"""
    print(f"\n{Colors.BOLD}Metrics Report{Colors.ENDC}")
    print(f"Active Pipelines: {metrics['pipeline_stats']['active_pipelines']}")

    print(f"\n{Colors.BOLD}Task Metrics:{Colors.ENDC}")
    for task_name, task_metrics in metrics['task_metrics'].items():
        print(f"{Colors.DIM}{Symbols.ARROW}{Colors.ENDC} {task_name}:")
        print(f"  Success: {task_metrics['success_count']}, "
              f"Avg Duration: {format_duration(task_metrics['average_duration'])}")

    print(f"\n{Colors.BOLD}System Load:{Colors.ENDC}")
    print(f"CPU: {metrics['system_metrics']['cpu_percent']}%")
    print(f"Memory: {metrics['system_metrics']['memory_percent']}%")
    print(f"Disk: {metrics['system_metrics']['disk_percent']}%")

async def example_usage():
    config = OrchestratorConfig(
        max_parallel_pipelines=5,
        max_queue_size=100,
        cache_ttl_seconds=3600,
        cache_max_size=1000,
        secret_key="example_secret",
        auth_endpoint=None,
        enable_circuit_breaker=True,
        circuit_breaker_threshold=5,
        circuit_breaker_timeout_seconds=300,
        dead_letter_queue_size=1000
    )

    executor = ExampleTaskExecutor()
    orchestrator = Orchestrator(executor, config)

    # Create the first task
    task1 = Task(
        name="data_preprocessing",
        priority=TaskPriority.HIGH,
        retry_policy=RetryPolicy(
            max_attempts=3,
            delay_seconds=5,
            exponential_backoff=True,
            max_delay_seconds=300
        ),
        cache_key="preprocess_v1",
        timeout_seconds=30
    )

    # Create the second task that depends on the first
    task2 = Task(
        name="flaky_calculation",
        priority=TaskPriority.MEDIUM,
        retry_policy=RetryPolicy(
            max_attempts=3,
            delay_seconds=2,
            exponential_backoff=False,
            max_delay_seconds=30
        ),
        dependencies={task1.id}
    )

    # Create the third task that depends on the second
    task3 = Task(
        name="slow_analysis",
        priority=TaskPriority.LOW,
        timeout_seconds=60,
        dependencies={task2.id}
    )

    pipeline = Pipeline(
        name="example_pipeline",
        tasks=[task1, task2, task3],
        parallel_tasks=2,  # Allow 2 tasks to run in parallel
        timeout_seconds=120,
        recovery_policy=RecoveryPolicy(
            max_recovery_attempts=2,
            recovery_delay_seconds=30,
            retry_failed_tasks_only=True,
            notify_on_recovery=True
        )
    )

    async def on_pipeline_success(pipeline: Pipeline):
        print(f"\nPipeline {pipeline.id} completed successfully!")
        print("Task execution summary:")
        for task in pipeline.tasks:
            duration = (task.completed_at - task.started_at).total_seconds() if task.completed_at and task.started_at else 0
            print(f"- {task.name}: Status={task.status.value}, Duration={duration:.2f}s, Attempts={task.attempts}")

    async def on_pipeline_failure(pipeline: Pipeline, error: Exception):
        print(f"\nPipeline {pipeline.id} failed: {error}")
        print("Task status at failure:")
        for task in pipeline.tasks:
            print(f"- {task.name}: Status={task.status.value}, Attempts={task.attempts}")

    async def handle_dead_letter(item: Dict[str, Any]):
        print("\nDead letter queue item received:")
        print(f"- Error: {item.get('error')}")
        print(f"- Task: {item.get('task_name')}")
        print(f"- Timestamp: {item.get('timestamp')}")

    orchestrator.register_success_callback(on_pipeline_success)
    orchestrator.register_failure_callback(on_pipeline_failure)
    orchestrator.register_dead_letter_handler(handle_dead_letter)


    try:
        await orchestrator.start()
        pipeline_id = await orchestrator.submit_pipeline(pipeline)
        print(f"\n{Colors.BOLD}Starting Pipeline:{Colors.ENDC} {pipeline_id}")

        while True:
            status = await orchestrator.get_pipeline_status(pipeline_id)
            if not status:
                break

            await print_pipeline_status(status)

            if status.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                print()  # Add newline after final status
                break

            await asyncio.sleep(1)

        metrics = await orchestrator.get_metrics_report()
        print_metrics_report(metrics)

    except Exception as e:
        print(f"{Colors.RED}Error: {e}{Colors.ENDC}")
        raise
    finally:
        await orchestrator.shutdown()

async def main():
    print("Starting example orchestrator usage...")
    await example_usage()
    print("Example completed!")

if __name__ == "__main__":
    asyncio.run(main())
