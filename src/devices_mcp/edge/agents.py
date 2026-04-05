"""
Edge agent abstractions for metrics and log collection.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Iterable

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class EdgeCollectorConfig:
    """
    Configuration for a single edge collector.

    Attributes:
        host: Network host or identifier for the node.
        tags: Extra labels appended to metrics/log records.
        metrics_endpoints: HTTP endpoints that expose Prometheus metrics.
        log_paths: Files or sockets that should be tailed for logs.
        scrape_interval: Interval (seconds) between scrapes.
    """

    host: str
    tags: dict[str, str] = field(default_factory=dict)
    metrics_endpoints: list[str] = field(default_factory=list)
    log_paths: list[str] = field(default_factory=list)
    scrape_interval: float = 15.0


class EdgeCollector:
    """
    Base collector that can be extended for protocol-specific behavior.
    """

    def __init__(self, config: EdgeCollectorConfig):
        self.config = config

    async def collect_metrics(self) -> dict[str, Any]:
        """
        Return a dictionary of metrics keyed by metric family.
        """
        raise NotImplementedError

    async def collect_logs(self) -> AsyncIterator[dict[str, Any]]:
        """
        Yield structured log entries for forwarding to Loki/Promtail.
        """
        raise NotImplementedError

    async def run(self) -> None:
        """
        Default loop: collect metrics and ignore logs.
        Subclasses can override for more sophisticated behavior.

        NOTE: This method now uses the centralized polling manager to prevent
        aggressive polling and coordinate with other monitoring tasks.
        """
        # Use centralized polling manager instead of manual loop
        from ..polling_manager import PollingPriority, get_polling_manager

        manager = get_polling_manager()

        # Determine priority based on scrape interval
        if self.config.scrape_interval < 10:
            priority = PollingPriority.HIGH
        elif self.config.scrape_interval < 60:
            priority = PollingPriority.NORMAL
        else:
            priority = PollingPriority.LOW

        async def collect_wrapper():
            """Wrapper to collect metrics and handle errors."""
            try:
                metrics = await self.collect_metrics()
                if metrics:
                    logger.debug(
                        "Collector %s harvested metrics: %s",
                        self.config.host,
                        metrics.keys(),
                    )
            except Exception:  # pragma: no cover - defensive
                logger.exception("Collector %s failed to collect metrics", self.config.host)
                raise  # Re-raise so polling manager can track errors

        task_name = f"edge_collector_{self.config.host}"
        manager.register_task(
            name=task_name,
            callback=collect_wrapper,
            interval_seconds=self.config.scrape_interval,
            priority=priority,
            enabled=True,
        )

        # Start manager if not already running
        if not manager._running:
            await manager.start()

        logger.info(
            f"Edge collector {self.config.host} registered with polling manager "
            f"(interval: {self.config.scrape_interval}s, priority: {priority.value})"
        )

        # Keep the task running (polling manager handles the actual polling)
        # This allows the method to be awaited and cancelled properly
        try:
            while True:
                await asyncio.sleep(3600)  # Sleep for 1 hour, check periodically
        except asyncio.CancelledError:
            # Unregister when cancelled
            manager.unregister_task(task_name)
            raise


class EdgeAgentManager:
    """
    Coordinates collectors running on a single node.
    """

    def __init__(self) -> None:
        self._collectors: dict[str, EdgeCollector] = {}
        self._tasks: list[asyncio.Task] = []

    def register_collector(self, name: str, collector: EdgeCollector) -> None:
        """Register a collector and schedule it to run."""
        if name in self._collectors:
            raise ValueError(f"Collector {name} already registered")
        self._collectors[name] = collector
        logger.info("Registered edge collector %s (%s)", name, collector.config.host)

    async def start(self) -> None:
        """Start all collectors concurrently."""
        if self._tasks:
            return
        for name, collector in self._collectors.items():
            task = asyncio.create_task(collector.run(), name=f"edge-collector-{name}")
            self._tasks.append(task)

    async def stop(self) -> None:
        """Cancel running collector tasks."""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def scrape_once(self) -> dict[str, dict[str, Any]]:
        """
        Collect metrics from all registered collectors once.
        Useful for Prometheus exporters running in pull mode.
        """
        results: dict[str, dict[str, Any]] = {}
        for name, collector in self._collectors.items():
            try:
                metrics = await collector.collect_metrics()
                results[name] = metrics
            except Exception:  # pragma: no cover - defensive
                logger.exception("Collector %s scrape failed", name)
                results[name] = {}
        return results

    def list_collectors(self) -> Iterable[str]:
        """Return the names of registered collectors."""
        return self._collectors.keys()
