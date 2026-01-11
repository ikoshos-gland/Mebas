"""
MEB RAG Sistemi - Resilience Patterns
Circuit Breaker, Exponential Backoff, and Timeout handling
"""
import asyncio
import time
import random
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, TypeVar, Optional, Dict, Any, Tuple
from functools import wraps

from config.settings import get_settings


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation - requests flow through
    OPEN = "open"          # Failing - requests are rejected immediately
    HALF_OPEN = "half_open"  # Testing recovery - limited requests allowed


class CircuitOpenError(Exception):
    """Raised when circuit is open and request is rejected."""
    def __init__(self, circuit_name: str, time_until_recovery: float = 0):
        self.circuit_name = circuit_name
        self.time_until_recovery = time_until_recovery
        super().__init__(
            f"Circuit '{circuit_name}' is OPEN. "
            f"Recovery in {time_until_recovery:.1f}s"
        )


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5      # Failures before opening circuit
    recovery_timeout: float = 60.0  # Seconds before attempting recovery
    half_open_requests: int = 3     # Successful requests needed to close

    @classmethod
    def from_settings(cls) -> "CircuitBreakerConfig":
        """Create config from application settings."""
        settings = get_settings()
        return cls(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            recovery_timeout=settings.circuit_breaker_recovery_timeout,
            half_open_requests=settings.circuit_breaker_half_open_requests
        )


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True  # Add randomness to prevent thundering herd
    retryable_exceptions: Tuple[type, ...] = (Exception,)

    @classmethod
    def from_settings(cls) -> "RetryConfig":
        """Create config from application settings."""
        settings = get_settings()
        return cls(
            max_attempts=settings.retry_max_attempts,
            base_delay=settings.retry_base_delay,
            max_delay=settings.retry_max_delay,
            exponential_base=settings.retry_exponential_base
        )


class CircuitBreaker:
    """
    Thread-safe circuit breaker for async functions.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests rejected immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed

    Transitions:
    - CLOSED -> OPEN: After failure_threshold consecutive failures
    - OPEN -> HALF_OPEN: After recovery_timeout seconds
    - HALF_OPEN -> CLOSED: After half_open_requests successful calls
    - HALF_OPEN -> OPEN: On any failure during half-open
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig.from_settings()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change: float = time.time()
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result if successful

        Raises:
            CircuitOpenError: If circuit is open
            Exception: If function fails and circuit trips
        """
        async with self._lock:
            # Check if we should attempt recovery
            if self.state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    self._transition_to(CircuitState.HALF_OPEN)
                else:
                    time_until_recovery = self._time_until_recovery()
                    raise CircuitOpenError(self.name, time_until_recovery)

        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result
        except Exception as e:
            await self._record_failure()
            raise

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.config.recovery_timeout

    def _time_until_recovery(self) -> float:
        """Calculate time remaining until recovery attempt."""
        if self.last_failure_time is None:
            return 0
        elapsed = time.time() - self.last_failure_time
        remaining = self.config.recovery_timeout - elapsed
        return max(0, remaining)

    async def _record_success(self) -> None:
        """Record successful call and potentially close circuit."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.half_open_requests:
                    self._transition_to(CircuitState.CLOSED)
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

    async def _record_failure(self) -> None:
        """Record failed call and potentially open circuit."""
        async with self._lock:
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                # Any failure during half-open immediately opens circuit
                self._transition_to(CircuitState.OPEN)
            elif self.state == CircuitState.CLOSED:
                self.failure_count += 1
                if self.failure_count >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state and reset counters."""
        old_state = self.state
        self.state = new_state
        self.last_state_change = time.time()

        if new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self.success_count = 0
        elif new_state == CircuitState.OPEN:
            self.success_count = 0

        print(f"[CircuitBreaker:{self.name}] {old_state.value} -> {new_state.value}")

    def get_state_info(self) -> Dict[str, Any]:
        """Get current state information for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "time_until_recovery": self._time_until_recovery() if self.state == CircuitState.OPEN else 0
        }

    def reset(self) -> None:
        """Reset circuit breaker to initial closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = time.time()


# Global registry of circuit breakers
_circuit_breakers: Dict[str, CircuitBreaker] = {}
_registry_lock = asyncio.Lock()


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """
    Get or create a circuit breaker by name.

    Circuit breakers are singletons per name - calling with the same name
    returns the same instance.
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]


def get_all_circuit_states() -> Dict[str, Dict[str, Any]]:
    """Get state info for all registered circuit breakers."""
    return {
        name: breaker.get_state_info()
        for name, breaker in _circuit_breakers.items()
    }


def reset_all_circuits() -> None:
    """Reset all circuit breakers to closed state."""
    for breaker in _circuit_breakers.values():
        breaker.reset()


async def retry_with_backoff(
    func: Callable,
    config: Optional[RetryConfig] = None,
    *args,
    **kwargs
) -> Any:
    """
    Execute function with exponential backoff retry.

    Args:
        func: Async function to execute
        config: Retry configuration (uses settings defaults if None)
        *args, **kwargs: Arguments to pass to function

    Returns:
        Function result if successful

    Raises:
        Exception: Last exception if all retries fail
    """
    if config is None:
        config = RetryConfig.from_settings()

    last_exception = None

    for attempt in range(config.max_attempts):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e

            if attempt < config.max_attempts - 1:
                # Calculate delay with exponential backoff
                delay = min(
                    config.base_delay * (config.exponential_base ** attempt),
                    config.max_delay
                )

                # Add jitter to prevent thundering herd
                if config.jitter:
                    delay = delay * (0.5 + random.random())

                print(
                    f"[Retry] Attempt {attempt + 1}/{config.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.2f}s"
                )
                await asyncio.sleep(delay)

    raise last_exception


T = TypeVar('T')


def with_resilience(
    circuit_name: str,
    timeout: Optional[float] = None,
    retry_config: Optional[RetryConfig] = None,
    use_circuit_breaker: bool = True,
    use_retry: bool = True
):
    """
    Composite decorator combining timeout, retry, and circuit breaker.

    Order of application (outer to inner):
    1. Circuit Breaker - Fast-fail if service is known to be down
    2. Retry - Retry transient failures with backoff
    3. Timeout - Prevent hanging on slow responses

    Args:
        circuit_name: Name for the circuit breaker (shared across calls)
        timeout: Timeout in seconds (uses settings default if None)
        retry_config: Retry configuration (uses settings defaults if None)
        use_circuit_breaker: Whether to use circuit breaker
        use_retry: Whether to use retry logic

    Usage:
        @with_resilience("azure_openai", timeout=30.0)
        async def call_llm(prompt: str) -> str:
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            settings = get_settings()

            # Get timeout from settings if not provided
            effective_timeout = timeout
            if effective_timeout is None:
                effective_timeout = settings.timeout_retrieve  # Default 30s

            # Get or create circuit breaker
            breaker = get_circuit_breaker(circuit_name) if use_circuit_breaker else None

            async def execute_with_timeout():
                """Execute function with timeout."""
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=effective_timeout
                )

            async def execute_with_retry():
                """Execute with retry logic."""
                if use_retry:
                    config = retry_config or RetryConfig.from_settings()
                    return await retry_with_backoff(execute_with_timeout, config)
                else:
                    return await execute_with_timeout()

            # Execute through circuit breaker if enabled
            if breaker:
                try:
                    return await breaker.call(execute_with_retry)
                except CircuitOpenError:
                    # Re-raise circuit open errors
                    raise
                except asyncio.TimeoutError:
                    # Timeouts count as failures for circuit breaker
                    raise
            else:
                return await execute_with_retry()

        return wrapper
    return decorator


def with_timeout_only(timeout: float):
    """
    Simple timeout decorator without retry or circuit breaker.

    For use on functions that already have their own error handling
    or where retry doesn't make sense.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=timeout
            )
        return wrapper
    return decorator
