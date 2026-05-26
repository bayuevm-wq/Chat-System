"""Async circuit breaker for fault isolation.

Implements the circuit breaker pattern without external dependencies,
using only ``asyncio`` primitives.  Automatically trips after a
configurable number of consecutive failures and re-closes after a
recovery timeout.

State transitions::

    CLOSED ──(failures ≥ threshold)──► OPEN
    OPEN   ──(recovery timeout)──────► HALF_OPEN
    HALF_OPEN ──(success)────────────► CLOSED
    HALF_OPEN ──(failure)────────────► OPEN

Usage::

    breaker = CircuitBreaker("redis")

    result = await breaker(some_async_func, arg1, kwarg=value)

    # Or as a decorator
    @circuit_breaker("redis-publish", failure_threshold=3)
    async def publish(channel, msg):
        ...
"""

from __future__ import annotations

import asyncio
import functools
import time
from enum import StrEnum
from typing import Any, Callable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# ── Exceptions ──────────────────────────────────────────────────
class CircuitBreakerOpenError(Exception):
    """Raised when a call is attempted while the circuit is open."""

    def __init__(self, breaker_name: str, remaining_seconds: float) -> None:
        self.breaker_name = breaker_name
        self.remaining_seconds = remaining_seconds
        super().__init__(
            f"Circuit breaker '{breaker_name}' is OPEN — "
            f"retry in {remaining_seconds:.1f}s"
        )


# ── States ──────────────────────────────────────────────────────
class CircuitState(StrEnum):
    """Possible circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ── Circuit breaker implementation ─────────────────────────────
class CircuitBreaker:
    """Async-safe circuit breaker with automatic state transitions.

    Args:
        name: Human-readable name for logging / identification.
        failure_threshold: Consecutive failures before tripping to OPEN.
        recovery_timeout: Seconds to wait in OPEN before moving to HALF_OPEN.
        half_open_max_calls: Max concurrent probe calls in HALF_OPEN state.
    """

    __slots__ = (
        "_name",
        "_failure_threshold",
        "_recovery_timeout",
        "_half_open_max_calls",
        "_state",
        "_failure_count",
        "_last_failure_time",
        "_half_open_calls",
        "_lock",
    )

    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ) -> None:
        self._name = name
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._half_open_max_calls = half_open_max_calls

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._half_open_calls: int = 0
        self._lock = asyncio.Lock()

    # ── Public properties ───────────────────────────────────────

    @property
    def name(self) -> str:
        """Circuit breaker name."""
        return self._name

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Current consecutive failure count."""
        return self._failure_count

    # ── State transitions (must be called under lock) ───────────

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state and log the change."""
        old_state = self._state
        if old_state == new_state:
            return
        self._state = new_state
        logger.info(
            "circuit_breaker_state_change",
            breaker=self._name,
            from_state=old_state.value,
            to_state=new_state.value,
            failure_count=self._failure_count,
        )

    def _record_success(self) -> None:
        """Reset counters on a successful call."""
        self._failure_count = 0
        self._half_open_calls = 0
        self._transition_to(CircuitState.CLOSED)

    def _record_failure(self) -> None:
        """Increment failure count and trip if threshold reached."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self._failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def _should_attempt(self) -> bool:
        """Determine whether a call should proceed.

        Returns:
            ``True`` if the call is allowed, ``False`` otherwise.

        Raises:
            CircuitBreakerOpenError: When the circuit is OPEN and the
                recovery timeout has not yet elapsed.
        """
        if self._state is CircuitState.CLOSED:
            return True

        if self._state is CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self._recovery_timeout:
                # Move to half-open and allow a probe call
                self._transition_to(CircuitState.HALF_OPEN)
                self._half_open_calls = 0
                return True
            remaining = self._recovery_timeout - elapsed
            raise CircuitBreakerOpenError(self._name, remaining)

        # HALF_OPEN — allow up to max probe calls
        if self._half_open_calls < self._half_open_max_calls:
            self._half_open_calls += 1
            return True

        raise CircuitBreakerOpenError(self._name, self._recovery_timeout)

    # ── Call execution ──────────────────────────────────────────

    async def __call__(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute *func* within the circuit breaker.

        Args:
            func: An async callable to protect.
            *args: Positional arguments forwarded to *func*.
            **kwargs: Keyword arguments forwarded to *func*.

        Returns:
            The return value of *func*.

        Raises:
            CircuitBreakerOpenError: If the circuit is currently open.
        """
        async with self._lock:
            self._should_attempt()

        try:
            result = await func(*args, **kwargs)
        except Exception:
            async with self._lock:
                self._record_failure()
                logger.warning(
                    "circuit_breaker_failure",
                    breaker=self._name,
                    failure_count=self._failure_count,
                    state=self._state.value,
                )
            raise
        else:
            async with self._lock:
                self._record_success()
            return result

    # ── Convenience reset ───────────────────────────────────────

    async def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        async with self._lock:
            self._failure_count = 0
            self._half_open_calls = 0
            self._transition_to(CircuitState.CLOSED)
            logger.info("circuit_breaker_manual_reset", breaker=self._name)


# ── Decorator factory ──────────────────────────────────────────
def circuit_breaker(
    name: str,
    *,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    half_open_max_calls: int = 1,
) -> Callable[[F], F]:
    """Decorator factory that wraps an async function with a circuit breaker.

    Args:
        name: Identifier for this circuit breaker instance.
        failure_threshold: Failures before opening the circuit.
        recovery_timeout: Seconds before a probe is allowed.
        half_open_max_calls: Probe calls allowed in HALF_OPEN.

    Returns:
        Decorator that protects the wrapped function.

    Example::

        @circuit_breaker("redis-cache", failure_threshold=3)
        async def cached_lookup(key: str) -> str | None:
            ...
    """
    breaker = CircuitBreaker(
        name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_max_calls=half_open_max_calls,
    )

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await breaker(func, *args, **kwargs)

        # Expose the breaker instance for inspection / testing
        wrapper.circuit_breaker = breaker  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator
