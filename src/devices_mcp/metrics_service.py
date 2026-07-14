"""
Metrics collection and serving for Grafana integration.

This module provides real-time camera metrics in a format compatible with Grafana.
"""

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class CameraStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ERROR = "error"


@dataclass
class PTZPosition:
    """PTZ position data structure"""

    pan: float = 0.0  # -1.0 (left) to 1.0 (right)
    tilt: float = 0.0  # -1.0 (down) to 1.0 (up)
    zoom: float = 0.0  # 0.0 (wide) to 1.0 (tele)
    moving: bool = False
    preset_id: int | None = None
    preset_name: str | None = None


@dataclass
class CameraMetrics:
    """Camera metrics data structure"""

    camera_id: str
    name: str
    ip_address: str
    model: str = ""
    firmware: str = ""
    status: CameraStatus = CameraStatus.OFFLINE
    last_seen: datetime | None = None
    uptime_seconds: int = 0
    temperature: float | None = None
    motion_detected: bool = False
    motion_last_detected: datetime | None = None
    motion_zones: list[dict[str, Any]] = field(default_factory=list)
    cpu_usage: float | None = None
    memory_usage: float | None = None
    network_rx: int | None = None  # bytes received
    network_tx: int | None = None  # bytes transmitted
    signal_strength: int | None = None  # WiFi signal strength in dBm
    last_error: str | None = None
    custom_metadata: dict[str, Any] = field(default_factory=dict)

    # PTZ related fields
    ptz_supported: bool = False
    ptz_position: PTZPosition = field(default_factory=PTZPosition)
    ptz_presets: dict[int, str] = field(default_factory=dict)  # preset_id: preset_name

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime to ISO format
        for field_name in ["last_seen", "motion_last_detected"]:
            if data[field_name]:
                data[field_name] = data[field_name].isoformat()
        # Convert Enum to string
        if data.get("status"):
            data["status"] = data["status"].value
        # Convert PTZPosition to dict
        if data.get("ptz_position"):
            data["ptz_position"] = asdict(data["ptz_position"])
        return data


class MetricsCollector:
    """Collect and aggregate camera metrics"""

    def __init__(self, tapo_client):
        self.tapo_client = tapo_client
        self.metrics: dict[str, CameraMetrics] = {}
        self._running = False
        self._polling_task = None

    async def start(self):
        """Start the metrics collection service"""
        if self._running:
            return

        self._running = True

        # Use centralized polling manager instead of manual loop
        from .polling_manager import PollingPriority, get_polling_manager

        manager = get_polling_manager()
        self._polling_task = manager.register_task(
            name="metrics_collection",
            callback=self.collect_metrics,
            interval_seconds=30.0,  # Collect every 30 seconds
            priority=PollingPriority.NORMAL,
            enabled=True,
        )

        # Start manager if not already running
        if not manager._running:
            await manager.start()

        logger.info("Metrics collection service started (using polling manager)")

    async def stop(self):
        """Stop the metrics collection service"""
        if not self._running:
            return

        self._running = False

        # Unregister from polling manager
        if self._polling_task:
            from .polling_manager import get_polling_manager

            manager = get_polling_manager()
            manager.unregister_task("metrics_collection")
            self._polling_task = None

        logger.info("Metrics collection service stopped")

    async def collect_metrics(self):
        """Collect metrics from all cameras"""
        # This would be implemented to collect actual metrics from Tapo cameras
        # For now, we'll just update the last_seen timestamp
        for _camera_id, metrics in self.metrics.items():
            if metrics.status == CameraStatus.ONLINE:
                metrics.last_seen = datetime.now()

    def get_grafana_metrics(self) -> dict[str, Any]:
        """Format metrics for Grafana consumption"""
        timestamp = datetime.now().isoformat()

        # Convert all metrics to Grafana-compatible format
        metrics = {"status": "success", "data": {"resultType": "matrix", "result": []}}

        # Add each metric as a separate time series
        for camera_id, camera_metrics in self.metrics.items():
            # Add status metric
            self._add_metric(
                metrics,
                "camera_status",
                {
                    "camera_id": camera_id,
                    "name": camera_metrics.name,
                    "model": camera_metrics.model,
                    "status": camera_metrics.status.value,
                },
                timestamp,
                1 if camera_metrics.status == CameraStatus.ONLINE else 0,
            )

            # Add temperature metric if available
            if camera_metrics.temperature is not None:
                self._add_metric(
                    metrics,
                    "camera_temperature",
                    {"camera_id": camera_id, "name": camera_metrics.name},
                    timestamp,
                    camera_metrics.temperature,
                )

            # Add motion detection metric
            self._add_metric(
                metrics,
                "motion_detected",
                {"camera_id": camera_id, "name": camera_metrics.name},
                timestamp,
                1 if camera_metrics.motion_detected else 0,
            )

            # Add network metrics if available
            if camera_metrics.network_rx is not None:
                self._add_metric(
                    metrics,
                    "network_rx_bytes",
                    {"camera_id": camera_id, "name": camera_metrics.name},
                    timestamp,
                    camera_metrics.network_rx,
                )

            if camera_metrics.network_tx is not None:
                self._add_metric(
                    metrics,
                    "network_tx_bytes",
                    {"camera_id": camera_id, "name": camera_metrics.name},
                    timestamp,
                    camera_metrics.network_tx,
                )

            # Add signal strength if available
            if camera_metrics.signal_strength is not None:
                self._add_metric(
                    metrics,
                    "signal_strength_dbm",
                    {"camera_id": camera_id, "name": camera_metrics.name},
                    timestamp,
                    camera_metrics.signal_strength,
                )

            # Add PTZ metrics if supported
            if camera_metrics.ptz_supported:
                # PTZ Position
                for axis in ["pan", "tilt", "zoom"]:
                    if hasattr(camera_metrics.ptz_position, axis):
                        self._add_metric(
                            metrics,
                            f"ptz_{axis}",
                            {"camera_id": camera_id, "name": camera_metrics.name},
                            timestamp,
                            getattr(camera_metrics.ptz_position, axis),
                        )

                # PTZ Moving state
                self._add_metric(
                    metrics,
                    "ptz_moving",
                    {"camera_id": camera_id, "name": camera_metrics.name},
                    timestamp,
                    1 if camera_metrics.ptz_position.moving else 0,
                )

                # PTZ Preset
                if camera_metrics.ptz_position.preset_id is not None:
                    self._add_metric(
                        metrics,
                        "ptz_preset",
                        {
                            "camera_id": camera_id,
                            "name": camera_metrics.name,
                            "preset_id": str(camera_metrics.ptz_position.preset_id),
                            "preset_name": camera_metrics.ptz_position.preset_name or "",
                        },
                        timestamp,
                        camera_metrics.ptz_position.preset_id,
                    )

        return metrics

    def _add_metric(
        self,
        metrics: dict[str, Any],
        metric_name: str,
        labels: dict[str, str],
        timestamp: str,
        value: int | float,
    ) -> None:
        """Add a metric to the Grafana response"""
        metric = {
            "metric": {"__name__": metric_name, **labels},
            "values": [[timestamp, value]],
        }
        metrics["data"]["result"].append(metric)


class MetricsServer:
    """HTTP server providing metrics endpoint for Grafana"""

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        host: str = "0.0.0.0",  # nosec B104
        port: int = 8080,
    ):
        self.metrics_collector = metrics_collector
        self.host = host
        self.port = port
        self._server = None

    async def start(self):
        """Start the metrics server"""
        try:
            import uvicorn
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware

            app = FastAPI(title="Devices MCP Metrics")

            # Enable CORS
            app.add_middleware(
                CORSMiddleware,
                allow_origins=[
                    "http://localhost:10717",
                    "http://127.0.0.1:10717",
                    "http://tauri.localhost",
                    "https://tauri.localhost",
                    "tauri://localhost",
                ],
                allow_origin_regex=r"https?://(?:[a-zA-Z0-9-]+\.ts\.net|.*?\.tail-[a-f0-9]+\.ts\.net|tauri\.localhost|localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?$|^tauri://localhost$",
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

            @app.get("/api/health")
            async def health_check():
                return {"status": "ok"}

            @app.get("/api/metrics")
            async def get_metrics():
                return self.metrics_collector.get_grafana_metrics()

            @app.get("/api/cameras")
            async def list_cameras():
                return {camera_id: metrics.to_dict() for camera_id, metrics in self.metrics_collector.metrics.items()}

            config = uvicorn.Config(app, host=self.host, port=self.port, log_level="info")
            self._server = uvicorn.Server(config)
            await self._server.serve()

        except ImportError:
            logger.exception("Failed to start metrics server")
            logger.exception("Please install the required dependencies with: pip install fastapi uvicorn")
            raise

    async def stop(self):
        """Stop the metrics server"""
        if self._server:
            self._server.should_exit = True
            await self._server.shutdown()
            self._server = None
