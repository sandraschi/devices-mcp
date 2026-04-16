"""
Rate Limiter and Retry Utilities for Ring MCP.

This module provides rate limiting and retry functionality to prevent hitting API rate limits
and handle transient failures gracefully.
"""

import asyncio
import logging
import time
from collections import deque
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, TypeVar, cast

from ..core.exceptions import RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RateLimit:
    """Represents a rate limit with a maximum number of requests per time window."""

    max_requests: int
    window_seconds: float

    def __post_init__(self) -> None:
        """Validate the rate limit values."""
        if self.max_requests <= 0:
            raise ValueError("max_requests must be greater than 0")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be greater than 0")


@dataclass
class RateLimitState:
    """Tracks the state of a rate limit."""

    limit: RateLimit
    timestamps: deque[float] = field(default_factory=deque)

    def is_exceeded(self) -> bool:
        """Check if the rate limit has been exceeded."""
        now = time.monotonic()

        # Remove timestamps outside the current window
        while self.timestamps and (now - self.timestamps[0] > self.limit.window_seconds):
            self.timestamps.popleft()

        # Check if we've exceeded the limit
        return len(self.timestamps) >= self.limit.max_requests

    def record_request(self) -> None:
        """Record a new request."""
        self.timestamps.append(time.monotonic())

    def time_until_reset(self) -> float:
        """Get the time in seconds until the rate limit resets."""
        if not self.timestamps:
            return 0.0

        now = time.monotonic()
        oldest = self.timestamps[0]
        return max(0.0, (oldest + self.limit.window_seconds) - now)


class RateLimiter:
    """Manages multiple rate limits and enforces them."""

    def __init__(self) -> None:
        """Initialize the rate limiter."""
        self.limits: dict[str, RateLimitState] = {}
        self.lock = asyncio.Lock()

    def add_limit(self, name: str, limit: RateLimit) -> None:
        """Add a rate limit.

        Args:
            name: Name of the rate limit
            limit: RateLimit instance
        """
        self.limits[name] = RateLimitState(limit)

    async def acquire(self, name: str, timeout: float | None = None) -> None:
        """Acquire a permit for a rate-limited operation.

        Args:
            name: Name of the rate limit
            timeout: Maximum time to wait for the rate limit (in seconds)

        Raises:
            RateLimitError: If the rate limit is exceeded and timeout is None or exceeded
        """
        if name not in self.limits:
            return

        start_time = time.monotonic()
        time_left = timeout

        while True:
            async with self.lock:
                state = self.limits[name]
                if not state.is_exceeded():
                    state.record_request()
                    return

                # Calculate how long to wait
                wait_time = state.time_until_reset()

                # If we have a timeout and we'd exceed it, raise an error
                if timeout is not None and (time.monotonic() + wait_time - start_time) > timeout:
                    raise RateLimitError(f"Rate limit '{name}' exceeded. Try again in {wait_time:.1f} seconds")

                # If we don't need to wait, record the request and return
                if wait_time <= 0:
                    state.record_request()
                    return

            # Sleep outside the lock to allow other tasks to proceed
            await asyncio.sleep(wait_time)

            # Update time left if we have a timeout
            if timeout is not None:
                time_left = timeout - (time.monotonic() - start_time)
                if time_left <= 0:
                    raise RateLimitError("Rate limit timeout exceeded")

    @asynccontextmanager
    async def limit(self, name: str, timeout: float | None = None) -> AsyncIterator[None]:
        """Context manager for rate-limited operations.

        Args:
            name: Name of the rate limit
            timeout: Maximum time to wait for the rate limit (in seconds)

        Yields:
            None

        Raises:
            RateLimitError: If the rate limit is exceeded and timeout is None or exceeded
        """
        await self.acquire(name, timeout)
        try:
            yield
        except Exception as e:
            raise e


def retry_with_backoff(
    *exception_types: type[Exception],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that retries a function with exponential backoff.

    Args:
        *exception_types: Exception types to retry on
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add jitter to the delay

    Returns:
        Decorated function with retry logic
    """
    if not exception_types:
        exception_types = (Exception,)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def async_wrapper(*args: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args)
                    return func(*args)
                except exception_types as e:
                    last_exception = e

                    # Don't retry if we've reached max attempts
                    if attempt == max_attempts:
                        break

                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (exponential_base ** (attempt - 1)), max_delay)

                    # Add jitter (up to 25% of the delay)
                    if jitter:
                        delay = delay * (0.75 + 0.5 * (hash(str(args)) % 100) / 100)

                    logger.warning(
                        "Attempt %d/%d failed: %s. Retrying in %.1f seconds...",
                        attempt,
                        max_attempts,
                        str(e),
                        delay,
                    )

                    await asyncio.sleep(delay)

            # If we get here, all attempts failed
            if last_exception is not None:
                raise last_exception

            raise RuntimeError("Retry failed but no exception was caught")

        def sync_wrapper(*args: Any) -> T:
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args)
                except exception_types as e:
                    last_exception = e

                    # Don't retry if we've reached max attempts
                    if attempt == max_attempts:
                        break

                    # Calculate delay with exponential backoff
                    delay = min(initial_delay * (exponential_base ** (attempt - 1)), max_delay)

                    # Add jitter (up to 25% of the delay)
                    if jitter:
                        delay = delay * (0.75 + 0.5 * (hash(str(args)) % 100) / 100)

                    logger.warning(
                        "Attempt %d/%d failed: %s. Retrying in %.1f seconds...",
                        attempt,
                        max_attempts,
                        str(e),
                        delay,
                    )

                    time.sleep(delay)

            # If we get here, all attempts failed
            if last_exception is not None:
                raise last_exception

            raise RuntimeError("Retry failed but no exception was caught")

        # Return the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return cast("Callable[..., T]", async_wrapper)
        return cast("Callable[..., T]", sync_wrapper)

    return decorator


def with_retry(
    *exception_types: type[Exception],
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Alias for retry_with_backoff for backward compatibility."""
    return retry_with_backoff(
        *exception_types,
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
    )


# Global rate limiter instance
global_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    return global_rate_limiter


def set_rate_limits(limits: dict[str, RateLimit]) -> None:
    """Set rate limits for the global rate limiter.

    Args:
        limits: Dictionary mapping rate limit names to RateLimit objects
    """
    for name, limit in limits.items():
        global_rate_limiter.add_limit(name, limit)
