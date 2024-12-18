import pytest

from orchestrator.policies.retry import RetryPolicy
from orchestrator.policies.recovery import RecoveryPolicy
from orchestrator.policies.circuit_breaker import CircuitBreaker


class TestRetryPolicy:
    def test_retry_policy_creation(self):
        policy = RetryPolicy(max_attempts=3, delay_seconds=5, exponential_backoff=True)
        assert policy.max_attempts == 3
        assert policy.delay_seconds == 5
        assert policy.exponential_backoff is True

    def test_retry_delay_calculation(self):
        policy = RetryPolicy(
            max_attempts=3,
            delay_seconds=5,
            exponential_backoff=True,
            max_delay_seconds=300,
        )

        # First retry
        assert policy.get_next_delay(1) == 5
        # Second retry (with exponential backoff)
        assert policy.get_next_delay(2) == 10
        # Third retry
        assert policy.get_next_delay(3) == 20

    def test_retry_max_delay(self):
        policy = RetryPolicy(
            max_attempts=3,
            delay_seconds=5,
            exponential_backoff=True,
            max_delay_seconds=15,
        )

        # Should be capped at max_delay_seconds
        assert policy.get_next_delay(4) == 15


class TestRecoveryPolicy:
    def test_recovery_policy_creation(self):
        policy = RecoveryPolicy(
            max_recovery_attempts=2,
            recovery_delay_seconds=30,
            retry_failed_tasks_only=True,
        )
        assert policy.max_recovery_attempts == 2
        assert policy.recovery_delay_seconds == 30
        assert policy.retry_failed_tasks_only is True

    def test_recovery_policy_validation(self):
        with pytest.raises(ValueError):
            RecoveryPolicy(max_recovery_attempts=0)  # Should be >= 1

        with pytest.raises(ValueError):
            RecoveryPolicy(recovery_delay_seconds=0)  # Should be >= 1


@pytest.mark.asyncio
class TestCircuitBreaker:
    async def test_circuit_breaker_creation(self):
        cb = CircuitBreaker(threshold=5, timeout_seconds=60)
        assert cb.threshold == 5
        assert cb.timeout_seconds == 60
        assert not cb.is_open

    async def test_circuit_breaker_failure_recording(self):
        cb = CircuitBreaker(threshold=2, timeout_seconds=60)

        assert await cb.can_execute() is True
        await cb.record_failure()
        assert await cb.can_execute() is True
        await cb.record_failure()
        assert await cb.can_execute() is False  # Circuit should be open
