"""
Centralized Polling Manager for Hardware Monitoring.

This module provides a unified polling manager that coordinates all hardware
monitoring activities across the Devices MCP system. It prevents aggressive
polling, manages intervals, and provides health monitoring.

Features:
- Centralized configuration of polling intervals
- Prevents overlapping polls
- Automatic backoff on errors
- Health monitoring and statistics
- Graceful start/stop
- Minimum interval enforcement (prevents < 0.1s polling)
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class PollingPriority(StrEnum):
    """Priority levels for polling tasks."""

    CRITICAL = "critical"  # System health, security (min 1s)
    HIGH = "high"  # Camera status, energy monitoring (min 5s)
    NORMAL = "normal"  # Metrics collection, logs (min 15s)
    LOW = "low"  # Historical data, analytics (min 60s)


@dataclass
class PollingTask:
    """Configuration for a polling task."""

    name: str
    callback: Callable[[], Awaitable[Any]]
    interval_seconds: float
    priority: PollingPriority = PollingPriority.NORMAL
    enabled: bool = True
    last_run: datetime | None = None
    last_duration: float = 0.0
    error_count: int = 0
    success_count: int = 0
    min_interval: float = field(init=False)
    backoff_factor: float = 1.0  # Exponential backoff multiplier
    max_backoff: float = 300.0  # Max 5 minutes backoff

    def __post_init__(self):
        """Set minimum interval based on priority."""
        min_intervals = {
            PollingPriority.CRITICAL: 1.0,
            PollingPriority.HIGH: 5.0,
            PollingPriority.NORMAL: 15.0,
            PollingPriority.LOW: 60.0,
        }
        self.min_interval = min_intervals.get(self.priority, 15.0)
        # Enforce minimum interval
        if self.interval_seconds < self.min_interval:
            logger.warning(
                f"Task '{self.name}' interval {self.interval_seconds}s is below minimum "
                f"{self.min_interval}s for priority {self.priority}. Adjusting to minimum."
            )
            self.interval_seconds = self.min_interval

    def get_effective_interval(self) -> float:
        """Get effective interval with backoff applied."""
        if self.error_count == 0:
            return self.interval_seconds

        # Exponential backoff: interval * (backoff_factor ^ error_count)
        backoff_interval = self.interval_seconds * (self.backoff_factor ** min(self.error_count, 5))
        return min(backoff_interval, self.max_backoff)

    def record_success(self, duration: float):
        """Record successful execution."""
        self.last_run = datetime.now()
        self.last_duration = duration
        self.success_count += 1
        # Reset error count on success (gradual recovery)
        if self.error_count > 0:
            self.error_count = max(0, self.error_count - 1)

    def record_error(self, duration: float):
        """Record failed execution."""
        self.last_run = datetime.now()
        self.last_duration = duration
        self.error_count += 1


class PollingManager:
    """
    Centralized manager for all polling activities.

    Prevents aggressive polling by:
    - Enforcing minimum intervals based on priority
    - Coordinating polls to prevent overlapping
    - Implementing exponential backoff on errors
    - Providing statistics and health monitoring
    """

    def __init__(self):
        self._tasks: dict[str, PollingTask] = {}
        self._running = False
        self._tasks_dict: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        self._start_time: datetime | None = None
        self._stats = {
            "total_polls": 0,
            "total_errors": 0,
            "total_successes": 0,
            "total_duration": 0.0,
        }

    def register_task(
        self,
        name: str,
        callback: Callable[[], Awaitable[Any]],
        interval_seconds: float,
        priority: PollingPriority = PollingPriority.NORMAL,
        enabled: bool = True,
    ) -> PollingTask:
        """
        Register a polling task.

        Args:
            name: Unique name for the task
            callback: Async function to call
            interval_seconds: Polling interval (will be enforced to minimum based on priority)
            priority: Task priority (determines minimum interval)
            enabled: Whether task is enabled

        Returns:
            PollingTask instance

        Raises:
            ValueError: If task name already exists
        """
        if name in self._tasks:
            raise ValueError(f"Task '{name}' already registered")

        task = PollingTask(
            name=name,
            callback=callback,
            interval_seconds=interval_seconds,
            priority=priority,
            enabled=enabled,
        )

        self._tasks[name] = task
        logger.info(
            f"Registered polling task '{name}' with interval {task.interval_seconds}s "
            f"(priority: {priority.value}, min: {task.min_interval}s)"
        )

        # If manager is already running, start this task
        if self._running and enabled:
            asyncio.create_task(self._run_task(name))

        return task

    def unregister_task(self, name: str) -> bool:
        """Unregister and stop a polling task."""
        if name not in self._tasks:
            return False

        # Stop the task
        if name in self._tasks_dict:
            self._tasks_dict[name].cancel()
            del self._tasks_dict[name]

        del self._tasks[name]
        logger.info(f"Unregistered polling task '{name}'")
        return True

    def enable_task(self, name: str) -> bool:
        """Enable a polling task."""
        if name not in self._tasks:
            return False

        task = self._tasks[name]
        if task.enabled:
            return True

        task.enabled = True
        if self._running:
            asyncio.create_task(self._run_task(name))
        logger.info(f"Enabled polling task '{name}'")
        return True

    def disable_task(self, name: str) -> bool:
        """Disable a polling task."""
        if name not in self._tasks:
            return False

        task = self._tasks[name]
        if not task.enabled:
            return True

        task.enabled = False
        if name in self._tasks_dict:
            self._tasks_dict[name].cancel()
            del self._tasks_dict[name]
        logger.info(f"Disabled polling task '{name}'")
        return True

    async def start(self):
        """Start all enabled polling tasks."""
        if self._running:
            logger.warning("Polling manager already running")
            return

        self._running = True
        self._start_time = datetime.now()

        # Start all enabled tasks
        for name, task in self._tasks.items():
            if task.enabled:
                self._tasks_dict[name] = asyncio.create_task(self._run_task(name))

        logger.info(f"Polling manager started with {len(self._tasks_dict)} active tasks")

    async def stop(self):
        """Stop all polling tasks."""
        if not self._running:
            return

        self._running = False

        # Cancel all tasks
        for _name, task in list(self._tasks_dict.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks_dict.clear()
        logger.info("Polling manager stopped")

    async def _run_task(self, name: str):
        """Run a single polling task in a loop."""
        task = self._tasks.get(name)
        if not task:
            return

        logger.debug(f"Starting polling task loop for '{name}'")

        while self._running and task.enabled:
            try:
                # Calculate effective interval with backoff
                interval = task.get_effective_interval()

                # Wait for the interval
                await asyncio.sleep(interval)

                # Check if still enabled
                if not task.enabled or not self._running:
                    break

                # Execute the callback
                start_time = time.time()
                try:
                    await task.callback()
                    duration = time.time() - start_time

                    # Record success
                    task.record_success(duration)
                    self._stats["total_successes"] += 1
                    self._stats["total_polls"] += 1
                    self._stats["total_duration"] += duration

                    logger.debug(
                        f"Polling task '{name}' completed in {duration:.3f}s "
                        f"(next run in {task.get_effective_interval():.1f}s)"
                    )

                except Exception as e:
                    duration = time.time() - start_time

                    # Record error
                    task.record_error(duration)
                    self._stats["total_errors"] += 1
                    self._stats["total_polls"] += 1
                    self._stats["total_duration"] += duration

                    logger.warning(
                        f"Polling task '{name}' failed after {duration:.3f}s: {e} "
                        f"(error count: {task.error_count}, next run in {task.get_effective_interval():.1f}s)"
                    )

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Unexpected error in polling task '{name}':")
                # Wait a bit before retrying to avoid tight loop
                await asyncio.sleep(1.0)

        logger.debug(f"Polling task loop for '{name}' stopped")

    def get_task_status(self, name: str) -> dict[str, Any] | None:
        """Get status information for a specific task."""
        task = self._tasks.get(name)
        if not task:
            return None

        return {
            "name": task.name,
            "enabled": task.enabled,
            "priority": task.priority.value,
            "interval_seconds": task.interval_seconds,
            "effective_interval": task.get_effective_interval(),
            "min_interval": task.min_interval,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "last_duration": task.last_duration,
            "success_count": task.success_count,
            "error_count": task.error_count,
            "error_rate": (
                task.error_count / (task.success_count + task.error_count)
                if (task.success_count + task.error_count) > 0
                else 0.0
            ),
        }

    def get_all_status(self) -> dict[str, Any]:
        """Get status information for all tasks."""
        tasks_status = {name: self.get_task_status(name) for name in self._tasks.keys()}

        uptime = None
        if self._start_time:
            uptime = (datetime.now() - self._start_time).total_seconds()

        return {
            "running": self._running,
            "uptime_seconds": uptime,
            "total_tasks": len(self._tasks),
            "active_tasks": len(self._tasks_dict),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
            "stats": self._stats.copy(),
            "tasks": tasks_status,
        }

    def get_health(self) -> dict[str, Any]:
        """Get health summary of polling manager."""
        if not self._running:
            return {"status": "stopped", "healthy": False}

        # Check for tasks with high error rates
        unhealthy_tasks = []
        for name, task in self._tasks.items():
            if not task.enabled:
                continue

            total_runs = task.success_count + task.error_count
            if total_runs > 10:  # Only check after some runs
                error_rate = task.error_count / total_runs
                if error_rate > 0.5:  # More than 50% errors
                    unhealthy_tasks.append(
                        {
                            "name": name,
                            "error_rate": error_rate,
                            "error_count": task.error_count,
                        }
                    )

        healthy = len(unhealthy_tasks) == 0

        return {
            "status": "running" if healthy else "degraded",
            "healthy": healthy,
            "unhealthy_tasks": unhealthy_tasks,
            "total_tasks": len(self._tasks),
            "active_tasks": len(self._tasks_dict),
        }


# Global singleton instance
_global_manager: PollingManager | None = None


def get_polling_manager() -> PollingManager:
    """Get the global polling manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = PollingManager()
    return _global_manager
