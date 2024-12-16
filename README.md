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

You can install Orchestrator directly from GitHub releases:

### Latest Version
```bash
pip install https://github.com/j-raghavan/orchestrator/releases/download/latest/orchestrator-latest-py3-none-any.whl
```

### Specific Version
```bash
pip install https://github.com/j-raghavan/orchestrator/releases/download/v0.1.0/orchestrator-0.1.0-py3-none-any.whl
```

### Using Poetry
```bash
poetry add https://github.com/j-raghavan/orchestrator/releases/download/latest/orchestrator-latest-py3-none-any.whl
```

### From Source
```bash
git clone https://github.com/j-raghavan/orchestrator.git
cd orchestrator
poetry install
```

## Quick Start

Here's a simple example to get you started:

```python
from orchestrator import DiagnosticOrchestrator, Task, Pipeline, TaskPriority
from orchestrator.models.config import OrchestratorConfig

# Configure the orchestrator
config = OrchestratorConfig(
    max_parallel_pipelines=5,
    max_queue_size=100,
    enable_circuit_breaker=True
)

# Create tasks
task1 = Task(
    name="data_preprocessing",
    priority=TaskPriority.HIGH,
)

task2 = Task(
    name="data_analysis",
    priority=TaskPriority.MEDIUM,
    dependencies={task1.id}
)

# Create a pipeline
pipeline = Pipeline(
    name="data_processing",
    tasks=[task1, task2],
    parallel_tasks=2
)

# Run the pipeline
async def main():
    orchestrator = DiagnosticOrchestrator(executor, config)
    await orchestrator.start()
    pipeline_id = await orchestrator.submit_pipeline(pipeline)

    # Monitor pipeline status
    status = await orchestrator.get_pipeline_status(pipeline_id)
    print(f"Pipeline status: {status}")
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