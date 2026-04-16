"""
Asynchronous utilities for Devices MCP.
"""

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def safe_create_task(
    coro: Coroutine[Any, Any, T],
    *,
    name: str | None = None,
    context: dict | None = None,
) -> asyncio.Task[T]:
    """
    Create an asyncio task with a standard exception handler that logs errors.

    Args:
        coro: The coroutine to run.
        name: Optional name for the task.
        context: Optional context dictionary to include in log messages.

    Returns:
        The created asyncio.Task.
    """
    task = asyncio.create_task(coro, name=name)

    def handle_task_result(t: asyncio.Task):
        try:
            t.result()
        except asyncio.CancelledError:
            pass  # Task cancellation is expected during shutdown
        except Exception as e:
            task_name = name or t.get_name()
            extra = {"task_name": task_name}
            if context:
                extra.update(context)

            logger.exception(
                f"Unhandled exception in background task '{task_name}': {e}",
                extra=extra,
            )

    task.add_done_callback(handle_task_result)
    return task
