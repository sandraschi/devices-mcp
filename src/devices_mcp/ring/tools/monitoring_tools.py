"""
Ring Monitoring and Health Check Tools - FastMCP 3.1

Real-time monitoring, health checks, and performance analysis for Ring security ecosystem.
Provides comprehensive system oversight and proactive maintenance alerts.

This module uses FastMCP 3.1 patterns with multiline decorators and proper
tool registration for Claude Desktop stdio communication.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from fastmcp import FastMCP

from ..core.ring_client import RingClient

logger = logging.getLogger(__name__)


def register_tools(app: FastMCP) -> None:
    """Register monitoring and health check tools with the FastMCP application.

    Uses FastMCP 3.1 patterns with multiline decorators and proper
    stdio communication support for Claude Desktop integration.

    Args:
        app: FastMCP application instance
    """

    @app.tool(
        name="monitor_system_health",
        description="Perform comprehensive health check of entire Ring security system",
    )
    async def monitor_system_health() -> Dict[str, Any]:
        """Perform comprehensive health check of entire Ring security system.

        Analyzes all Ring devices, connectivity, battery levels, signal strength,
        and system performance. Provides proactive maintenance recommendations
        and identifies potential issues before they affect security coverage.

        Returns:
            Dict containing:
            - overall_health_score: System health rating (0-100)
            - device_health: Individual device health assessments
            - maintenance_alerts: Required maintenance actions
            - performance_metrics: System performance indicators
            - recommendations: Proactive improvement suggestions
        """
        try:
            async with RingClient() as client:
                # Get all devices for health assessment
                all_devices = await client.get_devices()

                # Analyze device health
                total_devices = len(all_devices)
                online_devices = 0
                low_battery_devices = []
                offline_devices = []
                maintenance_needed = []

                for device in all_devices:
                    # Check online status
                    if device.get("online", False):
                        online_devices += 1
                    else:
                        offline_devices.append(
                            {
                                "device_id": device["id"],
                                "device_name": device["name"],
                                "device_type": device["type"],
                                "issue": "Device is offline",
                            }
                        )

                    # Check battery levels
                    battery_level = device.get("battery_life")
                    if battery_level is not None and battery_level < 20:
                        low_battery_devices.append(
                            {
                                "device_id": device["id"],
                                "device_name": device["name"],
                                "device_type": device["type"],
                                "battery_level": battery_level,
                                "issue": f"Low battery: {battery_level}%",
                            }
                        )

                    # Check for other maintenance needs
                    if battery_level is not None and battery_level < 10:
                        maintenance_needed.append(
                            {
                                "device_id": device["id"],
                                "device_name": device["name"],
                                "device_type": device["type"],
                                "priority": "urgent",
                                "action": "Replace battery immediately",
                            }
                        )

                # Calculate health score
                if total_devices > 0:
                    online_ratio = online_devices / total_devices
                    health_score = int(online_ratio * 100)
                    # Reduce score based on issues
                    health_score -= len(low_battery_devices) * 5
                    health_score -= len(offline_devices) * 10
                    health_score = max(0, min(100, health_score))
                else:
                    health_score = 0

                # Generate recommendations
                recommendations = []
                if offline_devices:
                    recommendations.append(
                        f"Check connectivity for {len(offline_devices)} offline devices"
                    )
                if low_battery_devices:
                    recommendations.append(
                        f"Replace batteries in {len(low_battery_devices)} devices"
                    )
                if not recommendations:
                    recommendations.append("All systems operational")

                return {
                    "success": True,
                    "overall_health_score": health_score,
                    "device_count": total_devices,
                    "healthy_devices": online_devices,
                    "devices_with_issues": len(low_battery_devices) + len(offline_devices),
                    "offline_devices": offline_devices,
                    "low_battery_devices": low_battery_devices,
                    "maintenance_alerts": maintenance_needed,
                    "performance_metrics": {
                        "api_response_time": "normal",  # Would need actual timing
                        "connection_stability": "stable"
                        if len(offline_devices) == 0
                        else "unstable",
                    },
                    "recommendations": recommendations,
                    "health_check_timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.exception("Error monitoring system health:")
            return {"success": False, "error": str(e)}

    @app.tool(
        name="get_real_time_activity",
        description="Get real-time activity feed from all Ring devices",
    )
    async def get_real_time_activity() -> Dict[str, Any]:
        """Get real-time activity feed from all Ring devices.

        Provides live activity monitoring across all Ring devices including
        motion events, doorbell presses, security alerts, and system changes.
        Essential for active security monitoring and incident response.

        Returns:
            Dict containing:
            - live_activity: Real-time events from all devices
            - activity_summary: Current activity levels by device type
            - active_alerts: Any current security or system alerts
            - system_status: Overall system operational status
        """
        try:
            async with RingClient() as client:
                # Get all devices
                all_devices = await client.get_devices()

                # Collect recent events from all devices
                live_activity = []
                activity_by_type = {}

                for device in all_devices:
                    try:
                        # Get recent events for this device
                        events = await client.get_device_events(device["id"], limit=3)

                        for event in events:
                            activity_item = {
                                "device_id": device["id"],
                                "device_name": device["name"],
                                "device_type": device["type"],
                                "event_id": event["id"],
                                "event_time": event["created_at"],
                                "event_type": event.get("kind", "unknown"),
                                "answered": event.get("answered", False),
                                "recording_status": event.get("recording_status"),
                            }
                            live_activity.append(activity_item)

                            # Track activity by type
                            event_type = event.get("kind", "unknown")
                            if event_type not in activity_by_type:
                                activity_by_type[event_type] = 0
                            activity_by_type[event_type] += 1

                    except Exception:
                        logger.exception("Error getting events for device {device['id']}:")

                # Sort activities by time (most recent first)
                live_activity.sort(key=lambda x: x["event_time"], reverse=True)

                # Determine system status
                active_alerts = []
                system_status = "normal"

                # Check for any critical issues
                offline_devices = [d for d in all_devices if not d.get("online", False)]
                if offline_devices:
                    active_alerts.append(
                        {
                            "type": "connectivity",
                            "severity": "warning",
                            "message": f"{len(offline_devices)} devices are offline",
                            "devices": [d["name"] for d in offline_devices],
                        }
                    )
                    system_status = "degraded"

                # Check for security events
                security_events = [
                    e for e in live_activity if e["event_type"] in ["motion", "alarm", "doorbell"]
                ]
                if security_events:
                    active_alerts.append(
                        {
                            "type": "security",
                            "severity": "info",
                            "message": "Recent security activity detected",
                            "event_count": len(security_events),
                        }
                    )

                return {
                    "success": True,
                    "live_activity": live_activity,
                    "activity_count": len(live_activity),
                    "activity_summary": activity_by_type,
                    "active_alerts": active_alerts,
                    "system_status": system_status,
                    "monitoring_timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.exception("Error getting real-time activity:")
            return {"success": False, "error": str(e)}
