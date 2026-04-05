"""Vienna-specific security dashboard data for Grafana."""

import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List

from ..base_tool import BaseTool, ToolCategory


class ViennaDashboardTool(BaseTool):
    """Tool for Vienna-specific security dashboard data."""

    class Meta:
        name: str = "get_vienna_security_dashboard"
        description: str = (
            "Get formatted data for Vienna-specific security dashboard with German labels"
        )
        category: ToolCategory = ToolCategory.UTILITY

    async def execute(self, **_kwargs) -> Dict[str, Any]:
        """Generate dashboard data with Vienna context."""
        try:
            # Get camera manager instance
            camera_manager = self.get_camera_manager()

            # Get current time in Vienna timezone
            vienna_time = datetime.utcnow() + timedelta(hours=1)  # CET is UTC+1

            # Generate time series data for the last 24 hours
            hours = 24
            timestamps = [
                (vienna_time - timedelta(hours=i)).strftime("%H:%M")
                for i in range(hours - 1, -1, -1)
            ]

            # Generate mock data for demonstration
            motion_events = self._generate_mock_motion_data(hours)
            camera_activity = self._generate_camera_activity(camera_manager)

            dashboard_data = {
                "timestamp": vienna_time.isoformat() + "+01:00",  # CET timezone
                "date": vienna_time.strftime("%d.%m.%Y"),
                "time": vienna_time.strftime("%H:%M"),
                "timezone": "Europe/Vienna",
                "language": "de",
                "metrics": {
                    "total_cameras": len(camera_manager.cameras),
                    "active_cameras": sum(
                        1
                        for cam in camera_manager.cameras.values()
                        if cam.get_status().get("online", False)
                    ),
                    "alerts_last_24h": sum(motion_events),
                    "avg_response_time_sec": 2.3,
                    "storage_used_percent": self._calculate_storage_usage(camera_manager),
                },
                "time_series": {
                    "timestamps": timestamps,
                    "motion_events": motion_events,
                    "camera_activity": camera_activity,
                },
                "cameras": [
                    self._format_camera_data(cam_id, cam)
                    for cam_id, cam in camera_manager.cameras.items()
                ],
                "alerts": self._get_recent_alerts(hours),
                "weather": self._get_weather_data(vienna_time),
            }

            return {
                "success": True,
                "data": dashboard_data,
                "content_type": "application/json",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate dashboard data: {e!s}",
                "content_type": "application/json",
            }

    def _generate_mock_motion_data(self, hours: int) -> List[int]:
        """Generate mock motion event data for the last N hours."""

        # More activity during typical business hours (9-17)
        return [
            (
                secrets.randbelow(6)
                if 9 <= (datetime.now().hour - i) % 24 < 17
                else secrets.randbelow(3)
            )
            for i in range(hours - 1, -1, -1)
        ]

    def _generate_camera_activity(self, camera_manager) -> Dict[str, List[int]]:
        """Generate camera activity data."""
        activity = {}
        for cam_id in camera_manager.cameras:
            activity[cam_id] = [self._simulate_camera_activity(hour) for hour in range(24)]
        return activity

    def _simulate_camera_activity(self, hour: int) -> int:
        """Simulate camera activity based on time of day."""

        # More activity during typical business hours (9-17)
        if 9 <= hour < 17:
            return secrets.randbelow(31) + 70  # 70-100% activity
        if 7 <= hour < 9 or 17 <= hour < 22:
            return secrets.randbelow(41) + 30  # 30-70% activity
        return secrets.randbelow(31)  # 0-30% activity at night

    def _format_camera_data(self, cam_id: str, camera) -> Dict[str, Any]:
        """Format camera data for the dashboard."""
        status = camera.get_status()
        return {
            "id": cam_id,
            "name": status.get("name", cam_id),
            "status": "Online" if status.get("online", False) else "Offline",
            "location": status.get("location", "Unbekannt"),
            "last_activity": status.get("last_activity", "Keine Aktivität"),
            "recording": status.get("recording", False),
            "signal_strength": status.get("signal_strength", 0),
            "battery_level": status.get("battery_level", 0),
        }

    def _get_recent_alerts(self, hours: int) -> List[Dict[str, Any]]:
        """Get recent security alerts."""
        alerts = []
        alert_types = [
            "Bewegung erkannt",
            "Person erkannt",
            "Unbekannter Besucher",
            "Tür geöffnet",
        ]

        for i in range(min(5, hours)):  # Max 5 most recent alerts
            alert_time = datetime.now() - timedelta(hours=i)
            alerts.append(
                {
                    "time": alert_time.strftime("%H:%M"),
                    "type": alert_types[i % len(alert_types)],
                    "camera": f"Kamera {i + 1}",
                    "location": f"Standort {i + 1}",
                    "priority": "Hoch" if i % 3 == 0 else "Mittel",
                }
            )

        return alerts

    def _calculate_storage_usage(self, camera_manager) -> float:
        """Calculate total storage usage across all cameras."""
        total_used = 0
        total_capacity = 1  # Avoid division by zero

        for camera in camera_manager.cameras.values():
            status = camera.get_status()
            total_used += status.get("storage_used_mb", 0)
            total_capacity += status.get("storage_total_mb", 0)

        return round((total_used / total_capacity) * 100, 1)

    def _get_weather_data(self, timestamp: datetime) -> Dict[str, Any]:
        """Get mock weather data for Vienna."""
        # This would typically call a weather API in a real implementation
        conditions = ["Sonnig", "Bewölkt", "Regnerisch", "Gewitter", "Nebel"]
        condition = conditions[timestamp.hour % len(conditions)]

        return {
            "condition": condition,
            "temperature": 15 + (timestamp.hour % 10),  # Vary between 15-25°C
            "humidity": 40 + (timestamp.hour % 40),  # Vary between 40-80%
            "wind_speed": 5 + (timestamp.hour % 10),  # Vary between 5-15 km/h
            "sunrise": "06:30",
            "sunset": "20:15",
        }
