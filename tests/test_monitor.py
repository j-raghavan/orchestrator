import pytest

from orchestrator.monitoring.metrics import MetricsCollector
from orchestrator.monitoring.system import SystemLoadMonitor


@pytest.mark.asyncio
class TestSystemLoadMonitor:
    async def test_load_monitoring(self):
        monitor = SystemLoadMonitor()
        load = await monitor.get_load()
        assert 0 <= load <= 1.0

    async def test_detailed_metrics(self):
        monitor = SystemLoadMonitor()
        metrics = await monitor.get_detailed_metrics()

        assert "cpu_percent" in metrics
        assert "memory_percent" in metrics
        assert "disk_percent" in metrics
        assert all(0 <= value <= 100 for value in metrics.values())


@pytest.mark.asyncio
class TestMetricsCollector:
    async def test_task_success_recording(self):
        collector = MetricsCollector()
        task_name = "test_task"
        duration = 1.5

        await collector.record_task_success(task_name, duration)
        metrics = await collector.get_metrics()

        assert task_name in metrics
        assert metrics[task_name]["success_count"] == 1
        assert metrics[task_name]["average_duration"] == duration

    async def test_task_failure_recording(self):
        collector = MetricsCollector()
        task_name = "test_task"
        error_type = "TestError"

        await collector.record_task_failure(task_name, error_type)
        metrics = await collector.get_metrics()

        assert task_name in metrics
        assert metrics[task_name]["failure_count"] == 1
        assert error_type in metrics[task_name]["errors"]
        assert metrics[task_name]["errors"][error_type] == 1

    async def test_multiple_task_recordings(self):
        collector = MetricsCollector()
        task_name = "test_task"

        # Record multiple successes and failures
        await collector.record_task_success(task_name, 1.0)
        await collector.record_task_success(task_name, 2.0)
        await collector.record_task_failure(task_name, "Error1")
        await collector.record_task_failure(task_name, "Error1")
        await collector.record_task_failure(task_name, "Error2")

        metrics = await collector.get_metrics()
        assert metrics[task_name]["success_count"] == 2
        assert metrics[task_name]["failure_count"] == 3
        assert metrics[task_name]["average_duration"] == 1.5
        assert metrics[task_name]["errors"]["Error1"] == 2
        assert metrics[task_name]["errors"]["Error2"] == 1
