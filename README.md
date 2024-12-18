<h1 align="center">
  <a>
    <img src="https://github.com/j-raghavan/orchestrator/blob/main/assets/orchestrator.png?raw=True" width="60" height="50" alt="Orchestrator" style="vertical-align: middle;"> Orchestrator </img>
  </a>
</h1>

<p align="center">
  <a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
  </a>
  <a href="https://python.org">
    <img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python: 3.9+">
  </a>
  <a href="https://github.com/j-raghavan/orchestrator/releases/latest">
    <img src="https://img.shields.io/github/v/release/j-raghavan/orchestrator" alt="GitHub release">
  </a>
  <a href="https://github.com/j-raghavan/orchestrator/actions">
    <img src="https://github.com/j-raghavan/orchestrator/workflows/CI/badge.svg" alt="CI Status">
  </a>
  <a href="https://codecov.io/gh/j-raghavan/orchestrator">
    <img src="https://codecov.io/gh/j-raghavan/orchestrator/branch/main/graph/badge.svg" alt="Code Coverage">
  </a>
</p>

Orchestrator is a robust Python package for task orchestration, providing a powerful framework for managing complex task pipelines with built-in support for parallel execution, retry policies, and comprehensive monitoring. It offers a modern, async-first approach to task execution with strong emphasis on reliability and observability.

## Key Features

- **Robust Task Management**
  - Asynchronous task execution with controlled parallelism
  - Configurable retry policies with exponential backoff
  - Task prioritization and dependency management
  - Circuit breaker pattern for failure protection

- **Flexible Storage Options**
  - SQLAlchemy-based persistent storage
  - In-memory storage for testing and development
  - Extensible storage interface for custom implementations

- **Comprehensive Monitoring**
  - Prometheus metrics integration
  - Detailed execution metrics and timing
  - System resource monitoring
  - Dead letter queue for failed tasks

- **Production-Ready Features**
  - Health check endpoints
  - Graceful shutdown handling
  - Rate limiting and resource management
  - Structured logging with `structlog`

## Installation

You can install Orchestrator using Poetry:

```bash
# From GitHub releases
# Latest version
poetry add git+https://github.com/j-raghavan/orchestrator.git

# Specific version
poetry add git+https://github.com/j-raghavan/orchestrator.git@v0.1.8

# From source
git clone https://github.com/j-raghavan/orchestrator.git
cd orchestrator
poetry install
```

## Quick Start

Here's a complete example showing task orchestration with different priorities and retry policies:

```python
from orchestrator import Orchestrator, Task, Pipeline, TaskPriority
from orchestrator.models.config import OrchestratorConfig
from orchestrator.models.base import RetryPolicy

# Configure the orchestrator
config = OrchestratorConfig(
    max_parallel_pipelines=5,
    max_queue_size=100,
    enable_circuit_breaker=True
)

# Create tasks with different priorities and retry policies
task1 = Task(
    name="data_preprocessing",
    priority=TaskPriority.HIGH
)

task2 = Task(
    name="flaky_calculation",
    priority=TaskPriority.MEDIUM,
    dependencies={task1.id},
    retry_policy=RetryPolicy(
        max_attempts=3,
        delay_seconds=5,
        exponential_backoff=True
    )
)

task3 = Task(
    name="slow_analysis",
    priority=TaskPriority.LOW,
    dependencies={task2.id}
)

# Create a pipeline
pipeline = Pipeline(
    name="data_processing",
    tasks=[task1, task2, task3],
    parallel_tasks=2
)

# Run the pipeline
async def main():
    orchestrator = Orchestrator(config)
    await orchestrator.start()

    pipeline_id = await orchestrator.submit_pipeline(pipeline)
    print(f"Starting Pipeline: {pipeline_id}")

    # Monitor pipeline status until completion
    while True:
        status = await orchestrator.get_pipeline_status(pipeline_id)
        if status.is_terminal():
            break
        await asyncio.sleep(1)

    # Get execution summary
    metrics = await orchestrator.get_metrics_report()
    print(f"Task Metrics:\n{metrics['task_metrics']}")

    await orchestrator.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## Example Output

When you run a pipeline, you'll see detailed progress information and metrics:

```
Starting Pipeline: 0e3b33fa-b23d-4476-b789-4e93e1d7d402
Pipeline Status: ◐ RUNNING
◐ Running: 1  ✓ Completed: 0  ✗ Failed: 0  ↻ Retrying: 0  ○ Pending: 2

Task execution summary:
- data_preprocessing: Status=completed, Duration=1.00s, Attempts=1
- flaky_calculation: Status=completed, Duration=4.01s, Attempts=2
- slow_analysis: Status=completed, Duration=6.00s, Attempts=1

Metrics Report
Task Metrics:
→ data_preprocessing:
  Success: 1, Avg Duration: 1.00s
→ flaky_calculation:
  Success: 1, Avg Duration: 4.00s
→ slow_analysis:
  Success: 1, Avg Duration: 6.00s

System Load:
CPU: 2.5%
Memory: 60.3%
Disk: 0.8%
```

## Configuration

Orchestrator can be configured via environment variables or a configuration object:

```yaml
orchestrator:
  max_parallel_pipelines: 10
  max_queue_size: 1000
  cache_ttl_seconds: 86400
  enable_circuit_breaker: true
  circuit_breaker_threshold: 5
  circuit_breaker_timeout_seconds: 300
```

## Advanced Features

### Retry Policies

```python
from orchestrator.models.base import RetryPolicy

task = Task(
    name="flaky_operation",
    retry_policy=RetryPolicy(
        max_attempts=3,
        delay_seconds=5,
        exponential_backoff=True
    )
)
```

### Monitoring Integration

```python
# Get metrics
metrics = await orchestrator.get_metrics_report()
print(f"Active pipelines: {metrics['pipeline_stats']['active_pipelines']}")
print(f"Task success rate: {metrics['task_metrics']}")
```

## Contributing

We welcome contributions to Orchestrator! Here's how you can help:

1. Check out our [contribution guidelines](docs/contributing.md)
2. Fork the repository
3. Create a feature branch
4. Add your changes
5. Run the tests: `poetry run pytest`
6. Submit a pull request

## Development Setup

```shell
# Clone the repository
git clone https://github.com/j-raghavan/orchestrator.git
cd orchestrator

# Install dependencies with Poetry
poetry install

# Set up pre-commit hooks
poetry run pre-commit install

# Run tests
poetry run pytest

# Build documentation
poetry run mkdocs serve
```

## Versioning

We use [Semantic Versioning](https://semver.org/). For the versions available, see the [tags on this repository](https://github.com/j-raghavan/orchestrator/tags).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

We are grateful to the open-source community and the following excellent libraries that make this project possible:

- SQLAlchemy for database operations
- Pydantic for data validation
- Prometheus Client for metrics
- structlog for structured logging
