"""Retry utilities for resilient async operations.

Provides configurable retry decorators built on ``tenacity`` with
exponential back-off, jitter, and structured logging for every
retry attempt.  Designed for wrapping Redis and other I/O calls
that may encounter transient failures.

Usage::

    from src.shared.retry import async_retry, with_retry, RetryConfig

    # Quick default retry (3 attempts, exponential + jitter)
    @async_retry()
    async def fetch_data():
        ...

    # Custom retry configuration
    config = RetryConfig(max_attempts=5, base_delay=1.0)
    @with_retry(config)
    async def important_operation():
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

import redis.asyncio as redis
import structlog
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

# ── Retryable exception types ──────────────────────────────────
_DEFAULT_RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    redis.ConnectionError,
    redis.TimeoutError,
)


# ── Retry configuration ────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class RetryConfig:
    """Immutable configuration for retry behaviour.

    Attributes:
        max_attempts: Maximum number of total attempts (including the first).
        base_delay: Initial delay in seconds before the first retry.
        max_delay: Upper-bound cap on the computed wait time.
        jitter: Whether to add random jitter to the wait time.
        retryable_exceptions: Tuple of exception types that trigger a retry.
    """

    max_attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 10.0
    jitter: bool = True
    retryable_exceptions: tuple[type[BaseException], ...] = field(
        default=_DEFAULT_RETRYABLE_EXCEPTIONS,
    )


# ── Default config singleton ───────────────────────────────────
DEFAULT_RETRY_CONFIG = RetryConfig()


# ── Logging callback ───────────────────────────────────────────
def _log_retry(retry_state: RetryCallState) -> None:
    """Log each retry attempt with structured context."""
    exception = retry_state.outcome and retry_state.outcome.exception()
    logger.warning(
        "retry_attempt",
        function=getattr(retry_state.fn, "__qualname__", str(retry_state.fn)),
        attempt=retry_state.attempt_number,
        wait_seconds=round(retry_state.next_action.sleep if retry_state.next_action else 0, 3),  # type: ignore[union-attr]
        error_type=type(exception).__name__ if exception else None,
        error=str(exception) if exception else None,
    )


# ── Decorator factories ────────────────────────────────────────
def async_retry(
    *,
    max_attempts: int = DEFAULT_RETRY_CONFIG.max_attempts,
    base_delay: float = DEFAULT_RETRY_CONFIG.base_delay,
    max_delay: float = DEFAULT_RETRY_CONFIG.max_delay,
    jitter: bool = DEFAULT_RETRY_CONFIG.jitter,
) -> Callable[[F], F]:
    """Decorator factory for async functions with exponential-jitter retry.

    Args:
        max_attempts: Maximum number of total attempts.
        base_delay: Initial back-off delay in seconds.
        max_delay: Maximum wait cap in seconds.
        jitter: Add random jitter to the wait time.

    Returns:
        A tenacity retry decorator configured for async usage.

    Example::

        @async_retry(max_attempts=5, base_delay=1.0)
        async def fragile_call():
            ...
    """
    wait_strategy = wait_exponential_jitter(
        initial=base_delay,
        max=max_delay,
        jitter=base_delay if jitter else 0,
    )

    return retry(  # type: ignore[return-value]
        stop=stop_after_attempt(max_attempts),
        wait=wait_strategy,
        retry=retry_if_exception_type(_DEFAULT_RETRYABLE_EXCEPTIONS),
        before_sleep=_log_retry,
        reraise=True,
    )


def with_retry(config: RetryConfig) -> Callable[[F], F]:
    """Decorator factory using a :class:`RetryConfig` instance.

    Args:
        config: The retry configuration to apply.

    Returns:
        A tenacity retry decorator.

    Example::

        cfg = RetryConfig(max_attempts=5, base_delay=1.0, jitter=False)
        @with_retry(cfg)
        async def custom_call():
            ...
    """
    wait_strategy = wait_exponential_jitter(
        initial=config.base_delay,
        max=config.max_delay,
        jitter=config.base_delay if config.jitter else 0,
    )

    return retry(  # type: ignore[return-value]
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_strategy,
        retry=retry_if_exception_type(config.retryable_exceptions),
        before_sleep=_log_retry,
        reraise=True,
    )
