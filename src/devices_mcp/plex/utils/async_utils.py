"""
Asynchronous utilities for PlexMCP.

This module provides utility functions for working with asyncio and asynchronous operations.
"""

import asyncio
import functools
import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import wraps
from typing import Any, Callable, Coroutine, List, Optional, Set, Type, TypeVar, Union

# Type variables
T = TypeVar("T")
R = TypeVar("R")

# Global thread pool for CPU-bound operations
_THREAD_POOL = ThreadPoolExecutor(max_workers=10, thread_name_prefix="PlexMCP_Thread")
_PROCESS_POOL = ProcessPoolExecutor(max_workers=4)

logger = logging.getLogger(__name__)

# Track running tasks for graceful shutdown
_RUNNING_TASKS: Set[asyncio.Task] = set()


def run_in_executor(
    func: Callable[..., T],
    *args: Any,
    executor: Optional[Union[ThreadPoolExecutor, ProcessPoolExecutor]] = None,
    **kwargs: Any,
) -> Coroutine[Any, Any, T]:
    """Run a synchronous function in a thread or process pool executor.

    Args:
        func: The synchronous function to run.
        *args: Positional arguments to pass to the function.
        executor: Optional executor to use. If None, uses the default thread pool.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        A coroutine that will yield the function's result.
    """
    if executor is None:
        executor = _THREAD_POOL

    loop = asyncio.get_running_loop()

    # Create a partial function with the arguments
    partial_func = functools.partial(func, *args, **kwargs)

    # Run in the executor
    return loop.run_in_executor(executor, partial_func)


def run_in_process(func: Callable[..., T], *args: Any, **kwargs: Any) -> Coroutine[Any, Any, T]:
    """Run a CPU-bound function in a process pool executor.

    Args:
        func: The CPU-bound function to run.
        *args: Positional arguments to pass to the function.
        **kwargs: Keyword arguments to pass to the function.

    Returns:
        A coroutine that will yield the function's result.
    """
    return run_in_executor(func, *args, executor=_PROCESS_POOL, **kwargs)


class AsyncLock:
    """A reentrant lock for async code."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None
        self._depth = 0

    async def __aenter__(self):
        # If we already hold the lock, just increment the depth
        if self._task == asyncio.current_task():
            self._depth += 1
            return self

        # Otherwise, acquire the lock
        await self._lock.acquire()
        self._task = asyncio.current_task()
        self._depth = 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._task != asyncio.current_task():
            raise RuntimeError("Lock is not held by the current task")

        self._depth -= 1
        if self._depth == 0:
            self._task = None
            self._lock.release()

    def locked(self) -> bool:
        """Return True if the lock is currently held."""
        return self._lock.locked() and self._task == asyncio.current_task()


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Union[Type[Exception], tuple[Type[Exception], ...]] = Exception,
    logger: Optional[logging.Logger] = None,
):
    """Decorator for retrying async functions with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts before giving up.
        delay: Initial delay between attempts in seconds.
        backoff: Multiplier for the delay between attempts.
        exceptions: Exception(s) to catch and retry on.
        logger: Optional logger for logging retry attempts.

    Returns:
        Decorated async function with retry logic.
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        if logger is not None:
                            logger.error(
                                f"Function {func.__name__} failed after {max_attempts} attempts: {e}",
                                exc_info=True,
                            )
                        raise

                    if logger is not None:
                        logger.warning(
                            f"Retrying {func.__name__} (attempt {attempt + 1}/{max_attempts}) "
                            f"in {current_delay:.2f} seconds: {e}"
                        )

                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # This should never be reached due to the raise in the except block
            raise RuntimeError("Unexpected error in retry logic")  # pragma: no cover

        return wrapper

    return decorator


class TaskPool:
    """A pool for managing and limiting concurrent tasks."""

    def __init__(self, max_concurrent: int = 10):
        """Initialize the task pool.

        Args:
            max_concurrent: Maximum number of concurrent tasks.
        """
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._pending: List[asyncio.Task] = []
        self._running: Set[asyncio.Task] = set()
        self._completed: List[asyncio.Task] = []

    async def add_task(
        self,
        coro: Coroutine[Any, Any, T],
        callback: Optional[Callable[[T], None]] = None,
        error_callback: Optional[Callable[[Exception], None]] = None,
    ) -> asyncio.Task:
        """Add a task to the pool.

        Args:
            coro: The coroutine to run.
            callback: Optional callback to call when the task completes successfully.
            error_callback: Optional callback to call when the task raises an exception.

        Returns:
            The created task.
        """

        async def _wrapped_coro() -> T:
            try:
                async with self._semaphore:
                    result = await coro
                    if callback is not None:
                        callback(result)
                    return result
            except Exception as e:
                if error_callback is not None:
                    error_callback(e)
                raise
            finally:
                self._running.discard(task)
                self._completed.append(task)

        task = asyncio.create_task(_wrapped_coro())
        self._pending.append(task)
        self._running.add(task)

        # Clean up completed tasks
        self._completed = [t for t in self._completed if not t.done()]

        return task

    async def gather(self) -> List[Any]:
        """Wait for all tasks in the pool to complete and return their results."""
        if not self._pending and not self._running:
            return []

        # Combine pending and running tasks
        all_tasks = self._pending + list(self._running)

        # Clear the pending and running lists
        self._pending.clear()
        self._running.clear()

        # Wait for all tasks to complete
        results = await asyncio.gather(*all_tasks, return_exceptions=True)

        # Add to completed tasks
        self._completed.extend(all_tasks)

        return results

    def cancel_all(self) -> None:
        """Cancel all pending and running tasks."""
        for task in self._pending + list(self._running):
            if not task.done():
                task.cancel()

        self._completed.extend(self._pending)
        self._completed.extend(self._running)
        self._pending.clear()
        self._running.clear()

    @property
    def pending_count(self) -> int:
        """Number of pending tasks."""
        return len(self._pending)

    @property
    def running_count(self) -> int:
        """Number of currently running tasks."""
        return len(self._running)

    @property
    def completed_count(self) -> int:
        """Number of completed tasks."""
        return len(self._completed)


def create_task(coro: Coroutine[Any, Any, T], name: Optional[str] = None) -> asyncio.Task[T]:
    """Create a task and track it for graceful shutdown.

    Args:
        coro: The coroutine to run as a task.
        name: Optional name for the task.

    Returns:
        The created task.
    """
    task = asyncio.create_task(coro, name=name)
    _RUNNING_TASKS.add(task)

    def _on_done(task: asyncio.Task) -> None:
        _RUNNING_TASKS.discard(task)

        # Log any exceptions
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("Task {task.get_name() or 'unnamed'} failed:")

    task.add_done_callback(_on_done)
    return task


async def gather_with_concurrency(
    n: int, *coros: Coroutine[Any, Any, T], return_exceptions: bool = False
) -> List[Union[T, Exception]]:
    """Run coroutines with limited concurrency.

    Args:
        n: Maximum number of concurrent tasks.
        *coros: Coroutines to run.
        return_exceptions: Whether to return exceptions instead of raising them.

    Returns:
        List of results, in the same order as the input coroutines.
    """
    if n <= 0:
        raise ValueError("Concurrency limit must be positive")

    semaphore = asyncio.Semaphore(n)

    async def _wrap_coro(coro: Coroutine[Any, Any, T]) -> T:
        async with semaphore:
            return await coro

    tasks = [create_task(_wrap_coro(coro)) for coro in coros]
    return await asyncio.gather(*tasks, return_exceptions=return_exceptions)


async def cancel_all_tasks() -> None:
    """Cancel all running tasks."""
    if not _RUNNING_TASKS:
        return

    logger.info(f"Cancelling {len(_RUNNING_TASKS)} running tasks")

    # Create a copy to avoid modification during iteration
    tasks = list(_RUNNING_TASKS)

    # Cancel all tasks
    for task in tasks:
        if not task.done():
            task.cancel()

    # Wait for all tasks to complete
    await asyncio.gather(*tasks, return_exceptions=True)

    # Clear the set of running tasks
    _RUNNING_TASKS.clear()


def async_timeout(
    seconds: float,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """Decorator to add a timeout to an async function.

    Args:
        seconds: Maximum time in seconds before timing out.

    Returns:
        Decorated function with timeout.
    """

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]],
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError as e:
                raise asyncio.TimeoutError(
                    f"Function {func.__name__} timed out after {seconds} seconds"
                ) from e

        return wrapper

    return decorator


async def run_until_complete_with_timeout(
    coro: Coroutine[Any, Any, T], timeout: float, default: T = None
) -> Optional[T]:
    """Run a coroutine with a timeout and return a default value on timeout.

    Args:
        coro: The coroutine to run.
        timeout: Maximum time in seconds to wait.
        default: Value to return on timeout.

    Returns:
        The result of the coroutine, or the default value on timeout.
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        return default
