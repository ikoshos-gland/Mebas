"""
MEB RAG Sistemi - Resilience Pattern Tests
Tests for circuit breaker, retry logic, and timeout handling
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.utils.resilience import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerConfig,
    RetryConfig,
    CircuitOpenError,
    retry_with_backoff,
    with_resilience,
    get_circuit_breaker,
    reset_all_circuits
)


class TestCircuitBreakerConfig:
    """Tests for CircuitBreakerConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60.0
        assert config.half_open_requests == 3

    def test_custom_values(self):
        """Test custom configuration values."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30.0,
            half_open_requests=2
        )
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.half_open_requests == 2

    @pytest.mark.unit
    def test_from_settings(self, patched_settings):
        """Test creating config from settings."""
        config = CircuitBreakerConfig.from_settings()
        assert config.failure_threshold == patched_settings.circuit_breaker_failure_threshold


class TestCircuitBreaker:
    """Tests for CircuitBreaker state machine."""

    @pytest.fixture
    def breaker(self):
        """Create a test circuit breaker."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=0.1,  # 100ms for fast tests
            half_open_requests=1
        )
        return CircuitBreaker("test", config)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_initial_state_is_closed(self, breaker):
        """Circuit should start in CLOSED state."""
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_success_keeps_closed(self, breaker):
        """Successful calls should keep circuit CLOSED."""
        async def success_func():
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_failures_open_circuit(self, breaker):
        """Circuit should open after failure_threshold failures."""
        async def fail_func():
            raise Exception("test error")

        # First failure
        with pytest.raises(Exception):
            await breaker.call(fail_func)
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 1

        # Second failure - should open circuit
        with pytest.raises(Exception):
            await breaker.call(fail_func)
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_open_circuit_rejects_calls(self):
        """Open circuit should reject calls immediately."""
        import time

        # Create a breaker with a long timeout so it doesn't transition during test
        config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=60.0,  # Long timeout to prevent transition during test
            half_open_requests=1
        )
        breaker = CircuitBreaker("test_open", config)

        # Force circuit open
        breaker.state = CircuitState.OPEN
        breaker.last_failure_time = time.time()  # Set to now so timeout hasn't passed

        async def any_func():
            return "should not run"

        with pytest.raises(CircuitOpenError) as exc_info:
            await breaker.call(any_func)

        assert "test_open" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_half_open_after_timeout(self, breaker):
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        import time

        # Open the circuit
        breaker.state = CircuitState.OPEN
        breaker.last_failure_time = time.time() - 1  # 1 second ago (> 0.1s timeout)

        async def success_func():
            return "recovered"

        result = await breaker.call(success_func)
        assert result == "recovered"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_half_open_failure_reopens(self, breaker):
        """Failure during HALF_OPEN should reopen circuit."""
        breaker.state = CircuitState.HALF_OPEN

        async def fail_func():
            raise Exception("still failing")

        with pytest.raises(Exception):
            await breaker.call(fail_func)

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.unit
    def test_reset(self, breaker):
        """Reset should return circuit to initial state."""
        breaker.state = CircuitState.OPEN
        breaker.failure_count = 5

        breaker.reset()

        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0

    @pytest.mark.unit
    def test_get_state_info(self, breaker):
        """get_state_info should return circuit status."""
        info = breaker.get_state_info()

        assert info["name"] == "test"
        assert info["state"] == "closed"
        assert info["failure_count"] == 0


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_success_no_retry(self):
        """Successful function should not retry."""
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        config = RetryConfig(max_attempts=3, base_delay=0.01)
        result = await retry_with_backoff(success_func, config)

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_retry_on_failure(self):
        """Should retry on failure."""
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("temporary error")
            return "success"

        config = RetryConfig(max_attempts=3, base_delay=0.01)
        result = await retry_with_backoff(fail_then_succeed, config)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_max_retries_exhausted(self):
        """Should raise after max retries exhausted."""
        async def always_fail():
            raise Exception("persistent error")

        config = RetryConfig(max_attempts=3, base_delay=0.01)

        with pytest.raises(Exception, match="persistent error"):
            await retry_with_backoff(always_fail, config)


class TestWithResilienceDecorator:
    """Tests for with_resilience decorator."""

    @pytest.fixture(autouse=True)
    def reset_circuits(self):
        """Reset circuits before and after each test."""
        reset_all_circuits()
        yield
        reset_all_circuits()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_decorator_success(self, patched_settings):
        """Decorated function should work normally on success."""
        @with_resilience("test_circuit", timeout=1.0, use_retry=False)
        async def success_func():
            return "success"

        result = await success_func()
        assert result == "success"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_decorator_timeout(self, patched_settings):
        """Decorated function should timeout."""
        @with_resilience("test_circuit", timeout=0.1, use_retry=False)
        async def slow_func():
            await asyncio.sleep(1.0)
            return "too slow"

        with pytest.raises(asyncio.TimeoutError):
            await slow_func()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_decorator_retry_and_succeed(self, patched_settings):
        """Decorated function should retry and eventually succeed."""
        call_count = 0

        @with_resilience(
            "test_circuit",
            timeout=1.0,
            use_retry=True,
            retry_config=RetryConfig(max_attempts=3, base_delay=0.01)
        )
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("temporary")
            return "success"

        result = await flaky_func()
        assert result == "success"
        assert call_count == 2


class TestCircuitBreakerRegistry:
    """Tests for circuit breaker registry functions."""

    @pytest.fixture(autouse=True)
    def reset_circuits(self):
        """Reset circuits before and after each test."""
        reset_all_circuits()
        yield
        reset_all_circuits()

    @pytest.mark.unit
    def test_get_circuit_breaker_creates_new(self):
        """get_circuit_breaker should create new breaker if not exists."""
        breaker = get_circuit_breaker("new_circuit")
        assert breaker is not None
        assert breaker.name == "new_circuit"

    @pytest.mark.unit
    def test_get_circuit_breaker_returns_same(self):
        """get_circuit_breaker should return same breaker for same name."""
        breaker1 = get_circuit_breaker("same_circuit")
        breaker2 = get_circuit_breaker("same_circuit")
        assert breaker1 is breaker2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
