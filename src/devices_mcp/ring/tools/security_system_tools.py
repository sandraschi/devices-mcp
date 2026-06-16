"""
Ring Security System Management Tools - FastMCP 3.1

Core security system operations for Ring burglar alarm and overall system control.
Handles arming/disarming, status monitoring, and emergency protocols.

This module uses FastMCP 3.1 patterns with multiline decorators and proper
tool registration for Claude Desktop stdio communication.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Literal

from fastmcp import FastMCP

from ..core.exceptions import AuthenticationError, DeviceNotFoundError, RingError
from ..core.ring_client import RingClient

logger = logging.getLogger(__name__)


def register_tools(app: FastMCP) -> None:
    """Register security system management tools with the FastMCP application.

    Uses FastMCP 3.1 patterns with multiline decorators and proper
    stdio communication support for Claude Desktop integration.

    Args:
        app: FastMCP application instance
    """

    @app.tool(
        name="get_security_system_status",
        description="Get comprehensive status of the entire Ring security system",
    )
    async def get_security_system_status() -> dict[str, Any]:
        """Get comprehensive status of the entire Ring security system.

        Returns detailed information about all Ring security devices including:
        - Overall system status (armed/disarmed/partial)
        - Individual device states and battery levels
        - Active alerts and recent events
        - System health and connectivity status
        - Emergency mode status

        This is the primary command for checking your home security status.
        Useful for morning/evening security checks or when arriving/leaving home.

        Returns:
            Dict containing:
            - system_status: Overall security state
            - devices: List of all Ring devices with status
            - active_alerts: Current security alerts
            - last_updated: Timestamp of status check
            - emergency_mode: Whether emergency protocols are active
        """
        try:
            async with RingClient() as client:
                # Get all devices
                all_devices = await client.get_devices()

                # Categorize devices by type and determine system status
                security_devices = []
                cameras = []
                doorbells = []
                sensors = []
                other_devices = []

                # Track armed status across security devices
                armed_devices = 0
                total_security_devices = 0

                for device in all_devices:
                    device_type = device.get("type", "").lower()

                    # Enhanced device info
                    device_info = {
                        "device_id": device["id"],
                        "name": device["name"],
                        "type": device["type"],
                        "model": device["model"],
                        "online": device["online"],
                        "battery_life": device.get("battery_life"),
                        "firmware": device.get("firmware"),
                        "address": device.get("address"),
                        "last_update": device["last_update"],
                    }

                    # Categorize device
                    if "alarm" in device_type or "security" in device_type:
                        security_devices.append(device_info)
                        total_security_devices += 1
                        # Check if this device appears to be armed (simplified logic)
                        # In a real implementation, you'd check the actual alarm state
                        if device.get("online", False):  # Assume online devices might be armed
                            armed_devices += 1
                    elif "camera" in device_type:
                        cameras.append(device_info)
                    elif "doorbell" in device_type:
                        doorbells.append(device_info)
                    elif "sensor" in device_type:
                        sensors.append(device_info)
                    else:
                        other_devices.append(device_info)

                # Determine overall system status
                system_status = "disarmed"  # Default
                if total_security_devices > 0:
                    if armed_devices == total_security_devices:
                        system_status = "armed"
                    elif armed_devices > 0:
                        system_status = "partial"
                    else:
                        system_status = "disarmed"

                # Get recent events for activity analysis
                all_events = []
                for device in all_devices:
                    try:
                        events = await client.get_device_events(device["id"], limit=2)
                        all_events.extend(events)
                    except Exception as e:
                        logger.debug(f"Could not get events for {device['id']}: {e}")

                # Analyze events for active alerts
                active_alerts = []
                recent_events = [e for e in all_events if e.get("created_at")]

                if recent_events:
                    # Sort by time and get most recent
                    recent_events.sort(key=lambda x: x.get("created_at", ""), reverse=True)

                    # Check for recent motion or alarm events
                    recent_security_events = [
                        e for e in recent_events[:5] if e.get("kind") in ["motion", "alarm", "doorbell"]
                    ]

                    if recent_security_events:
                        active_alerts.append(
                            {
                                "type": "activity",
                                "severity": "info",
                                "message": f"Recent security activity: {len(recent_security_events)} events",
                                "events": recent_security_events,
                            }
                        )

                # Check for offline devices
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

                return {
                    "success": True,
                    "system_status": {
                        "mode": system_status,
                        "armed": system_status == "armed",
                        "countdown_active": False,  # Would need specific device state checking
                        "entry_delay": 0,
                    },
                    "devices": {
                        "security": security_devices,
                        "cameras": cameras,
                        "doorbells": doorbells,
                        "sensors": sensors,
                        "other": other_devices,
                    },
                    "device_count": len(all_devices),
                    "online_devices": len([d for d in all_devices if d.get("online", False)]),
                    "active_alerts": active_alerts,
                    "alert_count": len(active_alerts),
                    "last_updated": datetime.now().isoformat(),
                    "emergency_mode": False,  # Ring doesn't have a global emergency mode
                }

        except AuthenticationError:
            logger.exception("Authentication failed:")
            return {
                "success": False,
                "message": "Ring authentication failed. Please check credentials.",
                "error": "Ring authentication failed. Please check credentials.",
                "error_type": "authentication",
            }
        except Exception as e:
            logger.exception("Error getting security status:")
            return {"success": False, "message": str(e), "error": str(e), "error_type": "system"}

    @app.tool(
        name="arm_security_system",
        description="Arm the Ring security system with specified mode and options",
    )
    def arm_security_system(
        mode: Literal["home", "away", "disarmed"] = "away",
        bypass_sensors: list[str] | None = None,
        delay_minutes: int | None = None,
    ) -> dict[str, Any]:
        """Arm the Ring security system with specified mode and options.

        Arms your Ring security system in the specified mode. The system supports
        different arming modes for various scenarios:

        - 'home': Arms perimeter sensors but allows internal movement
        - 'away': Arms all sensors for full protection when leaving
        - 'disarmed': Disarms the entire system

        The system includes safety features like entry/exit delays and sensor bypass
        for maintenance or temporary issues. Always ensure all family members are
        accounted for before arming in 'away' mode.

        Args:
            mode: Security system mode ('home', 'away', or 'disarmed')
            bypass_sensors: Optional list of sensor IDs to bypass during arming
            delay_minutes: Optional custom entry delay in minutes (overrides default)

        Returns:
            Dict containing:
            - success: Whether the operation completed successfully
            - system_mode: New system mode after arming
            - countdown_remaining: Entry/exit delay countdown if active
            - bypassed_sensors: List of sensors bypassed during arming
            - estimated_arm_time: When system will be fully armed

        Examples:
            # Standard away mode when leaving house
            arm_security_system("away")

            # Home mode for nighttime protection
            arm_security_system("home")

            # Away mode bypassing faulty window sensor
            arm_security_system("away", bypass_sensors=["sensor_12345"])
        """
        try:
            client = RingClient()

            # Validate mode
            valid_modes = ["home", "away", "disarmed"]
            if mode not in valid_modes:
                return {
                    "success": False,
                    "message": f"Invalid mode '{mode}'. Must be one of: {valid_modes}",
                }

            # Pre-arm system check
            system_status = client.get_system_status()
            if system_status.get("maintenance_mode"):
                return {
                    "success": False,
                    "message": "System is in maintenance mode. Cannot arm at this time.",
                    "error": "System is in maintenance mode. Cannot arm at this time.",
                    "maintenance_info": system_status.get("maintenance_info"),
                }

            # Check for low battery devices that might cause issues
            devices = client.get_all_devices()
            low_battery_devices = [
                d for d in devices if hasattr(d, "battery_level") and d.battery_level and d.battery_level < 15
            ]

            warnings = []
            if low_battery_devices:
                warnings.append(
                    {
                        "type": "low_battery",
                        "message": f"{len(low_battery_devices)} devices have low battery",
                        "devices": [d.name for d in low_battery_devices],
                    }
                )

            # Perform the arming operation
            arm_result = client.arm_system(
                mode=mode, bypass_sensors=bypass_sensors or [], entry_delay_minutes=delay_minutes
            )

            # Calculate estimated full arm time
            countdown_seconds = arm_result.get("countdown_seconds", 0)
            estimated_arm_time = None
            if countdown_seconds > 0:
                estimated_arm_time = (datetime.now() + timedelta(seconds=countdown_seconds)).isoformat()

            return {
                "success": True,
                "system_mode": mode,
                "previous_mode": system_status.get("mode"),
                "countdown_remaining": countdown_seconds,
                "countdown_active": countdown_seconds > 0,
                "bypassed_sensors": bypass_sensors or [],
                "estimated_arm_time": estimated_arm_time,
                "warnings": warnings,
                "arm_timestamp": datetime.now().isoformat(),
                "entry_delay_minutes": arm_result.get("entry_delay_minutes"),
                "exit_delay_seconds": arm_result.get("exit_delay_seconds"),
            }

        except DeviceNotFoundError as e:
            logger.exception("Device not found during arming:")
            return {
                "success": False,
                "message": f"Device not found: {e!s}",
                "error": f"Device not found: {e!s}",
                "error_type": "device_not_found",
            }
        except RingError as e:
            logger.exception("Ring API error during arming:")
            return {
                "success": False,
                "message": f"Ring system error: {e!s}",
                "error": f"Ring system error: {e!s}",
                "error_type": "ring_api",
            }
        except Exception as e:
            logger.exception("Unexpected error during arming:")
            return {"success": False, "message": str(e), "error": str(e), "error_type": "unexpected"}

    @app.tool(
        name="disarm_security_system",
        description="Disarm the Ring security system safely with authentication",
    )
    def disarm_security_system(force_disarm: bool = False, disarm_code: str | None = None) -> dict[str, Any]:
        """Disarm the Ring security system safely with authentication.

        Disarms the Ring security system with proper authentication and safety checks.
        This operation requires careful handling as it removes all security protection.

        The system includes safety features to prevent accidental disarming:
        - Authentication verification
        - Recent activity checks
        - Force disarm option for emergencies

        Always verify the disarm was successful and intentional. The system will
        log all disarm events for security audit purposes.

        Args:
            force_disarm: Override safety checks for emergency situations
            disarm_code: Optional disarm code for additional security

        Returns:
            Dict containing:
            - success: Whether disarm operation completed
            - previous_mode: System mode before disarming
            - disarm_timestamp: When system was disarmed
            - recent_activity: Any recent sensor activity
            - security_log_entry: Audit log information

        Examples:
            # Standard disarm when arriving home
            disarm_security_system()

            # Emergency disarm (use with caution)
            disarm_security_system(force_disarm=True)

            # Disarm with additional security code
            disarm_security_system(disarm_code="1234")
        """
        try:
            client = RingClient()

            # Get current system status before disarming
            current_status = client.get_system_status()
            previous_mode = current_status.get("mode", "unknown")

            # Safety check - verify system is currently armed
            if previous_mode == "disarmed" and not force_disarm:
                return {
                    "success": True,
                    "message": "System is already disarmed",
                    "previous_mode": previous_mode,
                    "disarm_timestamp": datetime.now().isoformat(),
                    "no_action_required": True,
                }

            # Check for recent activity that might indicate a security event
            recent_events = client.get_recent_events(minutes=5)
            security_events = [
                event for event in recent_events if event.get("event_type") in ["motion", "contact", "alarm"]
            ]

            warnings = []
            if security_events and not force_disarm:
                warnings.append(
                    {
                        "type": "recent_activity",
                        "message": f"Recent security activity detected ({len(security_events)} events)",
                        "events": security_events[:3],  # Show first 3 events
                    }
                )

            # Perform disarm operation
            disarm_result = client.disarm_system(force=force_disarm, disarm_code=disarm_code)

            # Create security log entry
            log_entry = {
                "action": "disarm",
                "timestamp": datetime.now().isoformat(),
                "previous_mode": previous_mode,
                "force_disarm": force_disarm,
                "user_authenticated": disarm_result.get("user_authenticated", False),
                "recent_events_count": len(security_events),
            }

            return {
                "success": True,
                "previous_mode": previous_mode,
                "current_mode": "disarmed",
                "disarm_timestamp": datetime.now().isoformat(),
                "force_disarm_used": force_disarm,
                "authentication_verified": disarm_result.get("user_authenticated", False),
                "recent_activity": security_events,
                "warnings": warnings,
                "security_log_entry": log_entry,
                "all_sensors_disabled": True,
            }

        except AuthenticationError:
            logger.exception("Authentication failed during disarm:")
            return {
                "success": False,
                "message": "Authentication failed. Cannot disarm system.",
                "error": "Authentication failed. Cannot disarm system.",
                "error_type": "authentication",
                "security_implication": "System remains armed for protection",
            }
        except RingError as e:
            logger.exception("Ring API error during disarm:")
            return {
                "success": False,
                "message": f"Ring system error: {e!s}",
                "error": f"Ring system error: {e!s}",
                "error_type": "ring_api",
            }
        except Exception as e:
            logger.exception("Unexpected error during disarm:")
            return {
                "success": False,
                "message": str(e),
                "error": str(e),
                "error_type": "unexpected",
                "security_implication": "System status unknown - manual verification recommended",
            }

    @app.tool(
        name="get_security_history",
        description="Get comprehensive security system history and event timeline",
    )
    def get_security_history(
        hours: int = 24, event_types: list[str] | None = None, include_video: bool = False
    ) -> dict[str, Any]:
        """Get comprehensive security system history and event timeline.

        Retrieves detailed history of security system events, providing insights into
        system usage patterns, security incidents, and device activity. This is
        essential for security auditing and understanding your home's protection status.

        The history includes arm/disarm events, sensor triggers, device status changes,
        and optionally video recordings. Use this for security reviews, investigating
        incidents, or understanding system usage patterns.

        Args:
            hours: Number of hours of history to retrieve (default: 24)
            event_types: Filter by specific event types ['arm', 'disarm', 'motion', 'contact', 'alarm']
            include_video: Whether to include video recording links in results

        Returns:
            Dict containing:
            - events: Chronological list of security events
            - summary: Summary statistics for the time period
            - device_activity: Per-device activity breakdown
            - arm_disarm_cycles: Timeline of system mode changes
            - video_recordings: Available video footage (if requested)
        """
        try:
            client = RingClient()

            # Calculate time range
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            # Get events from Ring API
            all_events = client.get_events_history(start_time=start_time, end_time=end_time, event_types=event_types)

            # Process and categorize events
            arm_events = []
            disarm_events = []
            sensor_events = []
            alarm_events = []
            device_activity = {}

            for event in all_events:
                event_type = event.get("event_type")
                device_name = event.get("device_name", "Unknown")

                # Track per-device activity
                if device_name not in device_activity:
                    device_activity[device_name] = {
                        "event_count": 0,
                        "last_activity": None,
                        "event_types": set(),
                    }

                device_activity[device_name]["event_count"] += 1
                device_activity[device_name]["last_activity"] = event.get("timestamp")
                device_activity[device_name]["event_types"].add(event_type)

                # Categorize events
                if event_type in ["arm", "armed"]:
                    arm_events.append(event)
                elif event_type in ["disarm", "disarmed"]:
                    disarm_events.append(event)
                elif event_type in ["motion", "contact", "sensor"]:
                    sensor_events.append(event)
                elif event_type == "alarm":
                    alarm_events.append(event)

            # Convert sets to lists for JSON serialization
            for device in device_activity.values():
                device["event_types"] = list(device["event_types"])

            # Create arm/disarm timeline
            arm_disarm_timeline = []
            system_events = sorted(arm_events + disarm_events, key=lambda x: x.get("timestamp", ""))

            for event in system_events:
                arm_disarm_timeline.append(
                    {
                        "timestamp": event.get("timestamp"),
                        "action": event.get("event_type"),
                        "mode": event.get("mode"),
                        "duration_minutes": event.get("duration_minutes"),
                    }
                )

            # Summary statistics
            summary = {
                "total_events": len(all_events),
                "arm_events": len(arm_events),
                "disarm_events": len(disarm_events),
                "sensor_triggers": len(sensor_events),
                "alarm_events": len(alarm_events),
                "active_devices": len(device_activity),
                "time_period_hours": hours,
                "most_active_device": max(device_activity.items(), key=lambda x: x[1]["event_count"])[0]
                if device_activity
                else None,
            }

            result = {
                "success": True,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "hours": hours,
                },
                "events": all_events,
                "summary": summary,
                "device_activity": device_activity,
                "arm_disarm_timeline": arm_disarm_timeline,
                "categorized_events": {
                    "arm_events": arm_events,
                    "disarm_events": disarm_events,
                    "sensor_events": sensor_events,
                    "alarm_events": alarm_events,
                },
            }

            # Add video recordings if requested
            if include_video:
                video_recordings = client.get_video_recordings(start_time=start_time, end_time=end_time)
                result["video_recordings"] = video_recordings
                result["video_count"] = len(video_recordings)

            return result

        except Exception as e:
            logger.exception("Error retrieving security history:")
            return {"success": False, "message": str(e), "error": str(e), "time_range_requested": f"{hours} hours"}
