"""Grafana metrics collection tool."""

import asyncio
from datetime import datetime
from typing import Any

from ..base_tool import BaseTool, ToolCategory


class GrafanaMetricsTool(BaseTool):
    """Tool for collecting camera metrics in Grafana-compatible format."""

    class Meta:
        name: str = "get_grafana_metrics"
        description: str = "Export comprehensive camera metrics for Grafana HTTP data source"
        category: ToolCategory = ToolCategory.UTILITY

    async def execute(self, **_kwargs) -> dict[str, Any]:
        """Collect all camera metrics for Grafana consumption."""
        try:
            # Get camera manager instance
            camera_manager = self.get_camera_manager()

            metrics = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "cameras": {},
                "system": {
                    "active_cameras": 0,
                    "total_cameras": len(camera_manager.cameras),
                    "alerts_pending": 0,
                    "recordings_active": 0,
                    "vienna_context": {
                        "timezone": "Europe/Vienna",
                        "season": self._get_vienna_season(),
                        "heating_period": self._is_heating_period(),
                        "local_time": datetime.now().strftime("%H:%M CET"),
                    },
                },
            }

            # Collect metrics for each camera
            for camera_id, camera in camera_manager.cameras.items():
                try:
                    # Get camera status and info
                    status = await camera.get_device_info()

                    camera_metrics = {
                        "status": "online" if status.get("online", False) else "offline",
                        "uptime_minutes": status.get("uptime", 0) // 60,
                        "motion_events_1h": await self._get_motion_events(camera_id, hours=1),
                        "motion_events_24h": await self._get_motion_events(camera_id, hours=24),
                        "last_motion_time": await self._get_last_motion_time(camera_id),
                        "recording_active": status.get("recording", False),
                        "temperature_celsius": status.get("temperature", 25.0),
                        "signal_strength_dbm": status.get("wifi_signal", -50),
                        "battery_level": status.get("battery_level", 100),
                        "storage_used_mb": status.get("storage_used", 0),
                        "storage_total_mb": status.get("storage_total", 32000),
                    }

                    metrics["cameras"][camera_id] = camera_metrics

                    # Update system counters
                    if camera_metrics["status"] == "online":
                        metrics["system"]["active_cameras"] += 1
                    if camera_metrics["recording_active"]:
                        metrics["system"]["recordings_active"] += 1

                except Exception as e:
                    # Camera offline or error - provide default metrics
                    metrics["cameras"][camera_id] = {
                        "status": "offline",
                        "error": str(e),
                        "uptime_minutes": 0,
                        "motion_events_1h": 0,
                        "motion_events_24h": 0,
                        "recording_active": False,
                    }

            return {
                "success": True,
                "data": metrics,
                "content_type": "application/json",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to collect metrics: {e!s}",
                "data": {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "cameras": {},
                },
            }

    def _get_vienna_season(self) -> str:
        """Get current season in Vienna."""
        month = datetime.now().month
        if month in [12, 1, 2]:
            return "winter"
        if month in [3, 4, 5]:
            return "spring"
        if month in [6, 7, 8]:
            return "summer"
        return "autumn"

    def _is_heating_period(self) -> bool:
        """Check if it's heating period in Vienna (Oct-May)."""
        month = datetime.now().month
        return month >= 10 or month <= 5

    async def _get_motion_events(self, camera_id: str, hours: int) -> int:
        """Get motion event count for specified time period."""
        try:
            from devices_mcp.core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()

            if hasattr(server, "camera_manager") and server.camera_manager:
                camera = server.camera_manager.cameras.get(camera_id)
                if camera and hasattr(camera, "_camera") and camera._camera:
                    # Get real motion events from camera
                    motion_data = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: camera._camera.getMotionDetection()
                    )

                    # Extract motion event count from camera response
                    # This is a simplified implementation - real cameras may have different APIs
                    events = motion_data.get("motion_detection", {}).get("events", [])

                    # Filter events by time period
                    from datetime import datetime, timedelta

                    cutoff_time = datetime.now() - timedelta(hours=hours)
                    recent_events = [
                        event
                        for event in events
                        if datetime.fromisoformat(event.get("timestamp", "1970-01-01")) > cutoff_time
                    ]

                    return len(recent_events)

            # Fallback: return 0 if no real data available
            return 0

        except Exception:
            import logging

            logger = logging.getLogger(__name__)
            logger.exception("Failed to get motion events for %s", camera_id)
            return 0

    async def _get_last_motion_time(self, _camera_id: str) -> str:
        """Get timestamp of last motion detection."""
        # TODO: Implement from actual camera logs
        # For now, return recent time - replace with actual implementation
        recent_time = datetime.utcnow().replace(minute=45, second=23)
        return recent_time.isoformat() + "Z"
