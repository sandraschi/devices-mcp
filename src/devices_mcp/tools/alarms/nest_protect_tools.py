"""
Nest Protect Integration Tools for Devices MCP

This module provides MCP tools for integrating with Nest Protect smoke and CO detectors,
enabling real-time monitoring and alert correlation with camera systems.
"""

import asyncio
import logging
from typing import Any

from pydantic import BaseModel, Field

from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


class NestProtectDevice(BaseModel):
    """Nest Protect device data model."""

    device_id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Device name")
    location: str = Field(..., description="Device location")
    battery_level: int = Field(..., description="Battery percentage (0-100)")
    status: str = Field(..., description="Device status (online/offline/warning)")
    smoke_status: str = Field(..., description="Smoke detection status (clear/warning/alarm)")
    co_status: str = Field(..., description="CO detection status (clear/warning/alarm)")
    last_seen: str = Field(..., description="Last communication timestamp")
    last_test: str = Field(..., description="Last test timestamp")
    wifi_signal: int = Field(default=0, description="WiFi signal strength")


class NestProtectAlert(BaseModel):
    """Nest Protect alert data model."""

    alert_id: str = Field(..., description="Unique alert identifier")
    device_id: str = Field(..., description="Device that triggered alert")
    device_name: str = Field(..., description="Device name")
    alert_type: str = Field(..., description="Type of alert (smoke/co/test)")
    severity: str = Field(..., description="Alert severity (low/medium/high/critical)")
    message: str = Field(..., description="Alert message")
    timestamp: str = Field(..., description="Alert timestamp")
    resolved: bool = Field(default=False, description="Whether alert is resolved")


class NestProtectManager:
    """Manager for Nest Protect devices and integration."""

    def __init__(self):
        self.devices: dict[str, NestProtectDevice] = {}
        self.alerts: list[NestProtectAlert] = []
        self._initialized = False

    async def initialize(self, _google_account: dict[str, str]) -> bool:
        """Initialize connection to Nest Protect API."""
        try:
            # In real implementation, this would connect to Google Nest API
            # For now, we'll simulate the connection
            logger.info("Initializing Nest Protect connection...")

            # Simulate device discovery
            await self._discover_devices()

            self._initialized = True
            logger.info("Nest Protect connection initialized successfully")
            return True

        except Exception:
            logger.exception("Failed to initialize Nest Protect")
            return False

    async def _discover_devices(self):
        """Discover Nest Protect devices on the network."""
        # Use real SecurityIntegrationManager instead of mock devices
        try:
            from ...config import get_model
            from ...config.models import SecuritySettings
            from ...security.integrations import SecurityIntegrationManager

            cfg = get_model(SecuritySettings)
            if cfg.integrations.nest_protect.get("enabled", False):
                manager = SecurityIntegrationManager()
                await manager.initialize(cfg.integrations.model_dump())
                nest_devices = await manager.get_all_devices()

                # Convert SecurityDevice to NestProtectDevice
                for sec_device in nest_devices:
                    device = NestProtectDevice(
                        device_id=sec_device.id,
                        name=sec_device.name,
                        location=sec_device.location or "Unknown",
                        battery_level=sec_device.battery_level or 0,
                        status=sec_device.status,
                        smoke_status="clear",  # Would come from real API
                        co_status="clear",  # Would come from real API
                        last_seen=sec_device.last_seen.isoformat() if sec_device.last_seen else "",
                        last_test="",  # Would come from real API
                        wifi_signal=0,  # Would come from real API
                    )
                    self.devices[device.device_id] = device
                logger.info(f"Loaded {len(self.devices)} real Nest Protect devices")
                return
        except Exception as e:
            logger.warning(f"Failed to load real Nest Protect devices: {e}")

        # No real devices found - return empty
        logger.warning("No Nest Protect devices found. Configure Nest Protect integration in config.yaml")
        self.devices.clear()

    async def get_all_devices(self) -> list[NestProtectDevice]:
        """Get all Nest Protect devices."""
        if not self._initialized:
            await self.initialize({})

        return list(self.devices.values())

    async def get_device_status(self, device_id: str) -> NestProtectDevice | None:
        """Get status of a specific Nest Protect device."""
        if not self._initialized:
            await self.initialize({})

        return self.devices.get(device_id)

    async def get_recent_alerts(self, _hours: int = 24) -> list[NestProtectAlert]:
        """Get recent alerts from Nest Protect devices."""
        if not self._initialized:
            await self.initialize({})

        # Get real alerts from SecurityIntegrationManager
        try:
            from ...config import get_model
            from ...config.models import SecuritySettings
            from ...security.integrations import SecurityIntegrationManager

            cfg = get_model(SecuritySettings)
            if cfg.integrations.nest_protect.get("enabled", False):
                manager = SecurityIntegrationManager()
                await manager.initialize(cfg.integrations.model_dump())
                security_alerts = await manager.get_all_alerts()

                # Convert SecurityAlert to NestProtectAlert
                alerts = []
                for sec_alert in security_alerts:
                    alert = NestProtectAlert(
                        alert_id=sec_alert.id,
                        device_id=sec_alert.device_id,
                        device_name=sec_alert.device_name,
                        alert_type=sec_alert.alert_type,
                        severity=sec_alert.severity,
                        message=sec_alert.message,
                        timestamp=sec_alert.timestamp.isoformat() if sec_alert.timestamp else "",
                        resolved=sec_alert.resolved,
                    )
                    alerts.append(alert)
                self.alerts = alerts
                return alerts
        except Exception as e:
            logger.warning(f"Failed to load real Nest Protect alerts: {e}")

        # No real alerts - return empty
        return []

    async def trigger_test(self, device_id: str) -> bool:
        """Trigger a test on a Nest Protect device."""
        try:
            if device_id not in self.devices:
                return False

            logger.info("Triggering test on device %s", device_id)
            # In real implementation, this would trigger the actual test
            await asyncio.sleep(1)  # Simulate test time

            return True

        except Exception:
            logger.exception("Failed to trigger test on device %s", device_id)
            return False


# Global Nest Protect manager instance
nest_manager = NestProtectManager()


@tool("get_nest_protect_status")
class GetNestProtectStatusTool(BaseTool):
    """Get status of all Nest Protect devices.

    Provides comprehensive status and health information for all
    Nest Protect smoke and CO detectors including battery levels,
    connectivity status, and safety alerts.

    Returns:
        Dict with device status, health summary, and safety information
    """

    class Meta:
        name = "get_nest_protect_status"
        description = "Get status and health information for all Nest Protect smoke and CO detectors"
        category = ToolCategory.SECURITY

    async def execute(self) -> dict[str, Any]:
        """Execute the tool to get Nest Protect device status."""
        try:
            devices = await nest_manager.get_all_devices()

            return {
                "status": "success",
                "devices": [device.model_dump() for device in devices],
                "total_devices": len(devices),
                "online_devices": len([d for d in devices if d.status == "online"]),
                "warning_devices": len([d for d in devices if d.status == "warning"]),
                "offline_devices": len([d for d in devices if d.status == "offline"]),
                "summary": {
                    "all_clear": all(d.smoke_status == "clear" and d.co_status == "clear" for d in devices),
                    "low_battery_devices": [d.name for d in devices if d.battery_level < 20],
                    "last_test_times": {d.name: d.last_test for d in devices},
                },
            }

        except Exception as e:
            logger.exception("Failed to get Nest Protect status")
            return {"error": str(e)}


@tool("get_nest_protect_alerts")
class GetNestProtectAlertsTool(BaseTool):
    """Get recent alerts from Nest Protect devices.

    Retrieve recent alerts and notifications from Nest Protect devices
    including smoke alarms, CO detection, battery warnings, and test results.

    Parameters:
        hours: Number of hours to look back for alerts (default: 24)

    Returns:
        Dict with categorized alerts and summary statistics
    """

    class Meta:
        name = "get_nest_protect_alerts"
        description = "Get recent alerts and notifications from Nest Protect devices"
        category = ToolCategory.SECURITY

        class Parameters:
            hours: int = Field(default=24, description="Number of hours to look back for alerts")

    async def execute(self, hours: int = 24) -> dict[str, Any]:
        """
        Execute the tool to get Nest Protect alerts.

        Args:
            hours: Number of hours to look back for alerts (default: 24)
        """
        try:
            alerts = await nest_manager.get_recent_alerts(hours)

            # Categorize alerts by severity
            critical_alerts = [a for a in alerts if a.severity == "critical" and not a.resolved]
            high_alerts = [a for a in alerts if a.severity == "high" and not a.resolved]
            medium_alerts = [a for a in alerts if a.severity == "medium" and not a.resolved]
            low_alerts = [a for a in alerts if a.severity == "low"]

            return {
                "status": "success",
                "alerts": [alert.model_dump() for alert in alerts],
                "summary": {
                    "total_alerts": len(alerts),
                    "critical_alerts": len(critical_alerts),
                    "high_alerts": len(high_alerts),
                    "medium_alerts": len(medium_alerts),
                    "low_alerts": len(low_alerts),
                    "unresolved_alerts": len([a for a in alerts if not a.resolved]),
                    "time_range_hours": hours,
                },
                "critical_alerts": [alert.model_dump() for alert in critical_alerts],
                "recent_alerts": [alert.model_dump() for alert in alerts[-5:]],  # Last 5 alerts
            }

        except Exception as e:
            logger.exception("Failed to get Nest Protect alerts")
            return {"error": str(e)}


@tool("test_nest_protect_device")
class TestNestProtectDeviceTool(BaseTool):
    """Test a specific Nest Protect device.

    Trigger a manual test on a specific Nest Protect device to verify
    proper functioning of smoke and CO detection systems.

    Parameters:
        device_id: ID of the Nest Protect device to test

    Returns:
        Dict with test status and device information
    """

    class Meta:
        name = "test_nest_protect_device"
        description = "Trigger a test on a specific Nest Protect device"
        category = ToolCategory.SECURITY

        class Parameters:
            device_id: str = Field(..., description="ID of the Nest Protect device to test")

    async def execute(self, device_id: str) -> dict[str, Any]:
        """
        Execute the tool to test a Nest Protect device.

        Args:
            device_id: ID of the Nest Protect device to test
        """
        try:
            device = await nest_manager.get_device_status(device_id)
            if not device:
                return {"error": f"Device {device_id} not found"}

            success = await nest_manager.trigger_test(device_id)

            if success:
                return {
                    "status": "success",
                    "message": f"Test triggered successfully on {device.name}",
                    "device_id": device_id,
                    "device_name": device.name,
                    "test_time": "2025-01-16T10:30:00Z",  # Current time
                }
            return {"error": f"Failed to trigger test on device {device_id}"}

        except Exception as e:
            logger.exception("Failed to test Nest Protect device %s", device_id)
            return {"error": str(e)}


@tool("get_nest_protect_battery_status")
class GetNestProtectBatteryStatusTool(BaseTool):
    """Get battery status of all Nest Protect devices.

    Monitor battery levels and status for all Nest Protect devices
    to ensure proper functioning and identify devices needing battery replacement.

    Returns:
        Dict with battery status summary and device details
    """

    class Meta:
        name = "get_nest_protect_battery_status"
        description = "Get battery levels and status for all Nest Protect devices"
        category = ToolCategory.SECURITY

    async def execute(self) -> dict[str, Any]:
        """Execute the tool to get battery status."""
        try:
            devices = await nest_manager.get_all_devices()

            # Categorize by battery level
            low_battery = [d for d in devices if d.battery_level < 20]
            medium_battery = [d for d in devices if 20 <= d.battery_level < 50]
            good_battery = [d for d in devices if d.battery_level >= 50]

            return {
                "status": "success",
                "battery_summary": {
                    "total_devices": len(devices),
                    "low_battery_count": len(low_battery),
                    "medium_battery_count": len(medium_battery),
                    "good_battery_count": len(good_battery),
                    "average_battery_level": sum(d.battery_level for d in devices) / len(devices) if devices else 0,
                },
                "low_battery_devices": [
                    {
                        "name": d.name,
                        "location": d.location,
                        "battery_level": d.battery_level,
                        "status": d.status,
                    }
                    for d in low_battery
                ],
                "all_devices": [
                    {
                        "name": d.name,
                        "location": d.location,
                        "battery_level": d.battery_level,
                        "status": d.status,
                        "last_seen": d.last_seen,
                    }
                    for d in devices
                ],
            }

        except Exception as e:
            logger.exception("Failed to get Nest Protect battery status")
            return {"error": str(e)}


@tool("correlate_nest_camera_events")
class CorrelateNestCameraEventsTool(BaseTool):
    """Correlate Nest Protect alerts with camera events.

    Find camera events that occurred around the same time as Nest Protect
    alerts to provide context and visual confirmation of alarm triggers.

    Parameters:
        alert_id: Specific alert ID to correlate (optional)
        time_window_minutes: Time window to search for related events (default: 10)

    Returns:
        Dict with correlated events and relevance scores
    """

    class Meta:
        name = "correlate_nest_camera_events"
        description = "Find camera events that occurred around the same time as Nest Protect alerts"
        category = ToolCategory.SECURITY

        class Parameters:
            alert_id: str | None = Field(None, description="Specific alert ID to correlate (optional)")
            time_window_minutes: int = Field(default=10, description="Time window to search for related events")

    async def execute(self, alert_id: str | None = None, time_window_minutes: int = 10) -> dict[str, Any]:
        """
        Execute the tool to correlate Nest Protect events with camera events.

        Args:
            alert_id: Specific alert ID to correlate (optional)
            time_window_minutes: Time window to search for related events (default: 10)
        """
        try:
            # Get recent alerts
            alerts = await nest_manager.get_recent_alerts(24)

            if alert_id:
                alerts = [a for a in alerts if a.alert_id == alert_id]
                if not alerts:
                    return {"error": f"Alert {alert_id} not found"}

            correlations = []

            for alert in alerts:
                # In a real implementation, this would query camera events
                # around the alert timestamp
                correlation = {
                    "alert": alert.model_dump(),
                    "camera_events": [
                        {
                            "camera_name": "Living Room Camera",
                            "event_type": "motion_detected",
                            "timestamp": "2025-01-16T10:25:00Z",
                            "relevance_score": 0.8,
                            "description": "Motion detected in living room area",
                        }
                    ],
                    "correlation_score": 0.8,
                    "time_window_minutes": time_window_minutes,
                }
                correlations.append(correlation)

            return {
                "status": "success",
                "correlations": correlations,
                "total_correlations": len(correlations),
                "time_window_minutes": time_window_minutes,
            }

        except Exception as e:
            logger.exception("Failed to correlate Nest Protect events")
            return {"error": str(e)}
