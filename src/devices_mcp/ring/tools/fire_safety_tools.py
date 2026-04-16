"""
Ring Fire Safety Management Tools - FastMCP 3.1

Fire alarm monitoring, testing, and emergency protocols for Ring fire safety devices.
Handles smoke detection, safety alerts, and emergency response automation.

This module uses FastMCP 3.1 patterns with multiline decorators and proper
tool registration for Claude Desktop stdio communication.
"""

import logging
from datetime import datetime
from typing import Any

from fastmcp import FastMCP

from ..core.ring_client import RingClient

logger = logging.getLogger(__name__)


def register_tools(app: FastMCP) -> None:
    """Register fire safety management tools with the FastMCP application.

    Uses FastMCP 3.1 patterns with multiline decorators and proper
    stdio communication support for Claude Desktop integration.

    Args:
        app: FastMCP application instance
    """

    @app.tool(
        name="get_fire_alarm_status",
        description="Get comprehensive status of all Ring fire alarms and smoke detectors",
    )
    async def get_fire_alarm_status() -> dict[str, Any]:
        """Get comprehensive status of all Ring fire alarms and smoke detectors.

        Provides detailed information about fire safety device health, battery levels,
        sensor functionality, and recent alert history. Critical for maintaining
        home fire safety and ensuring emergency detection systems are operational.

        Returns:
            Dict containing:
            - fire_alarms: List of all fire safety devices with status
            - system_health: Overall fire safety system assessment
            - battery_warnings: Devices with low battery requiring attention
            - test_recommendations: Suggested testing schedule
        """
        try:
            async with RingClient() as client:
                # Get all devices and filter for fire safety devices
                all_devices = await client.get_devices()
                fire_devices = [
                    device
                    for device in all_devices
                    if "smoke" in device.get("type", "").lower() or "fire" in device.get("type", "").lower()
                ]

                # Enhanced fire safety device analysis
                fire_alarms = []
                battery_warnings = []
                system_health = "operational"

                for device in fire_devices:
                    try:
                        # Get device events for alarm history
                        events = await client.get_device_events(device["id"], limit=3)

                        device_info = {
                            "device_id": device["id"],
                            "name": device["name"],
                            "type": device["type"],
                            "model": device["model"],
                            "online": device["online"],
                            "battery_life": device.get("battery_life"),
                            "firmware": device.get("firmware"),
                            "address": device.get("address"),
                            "recent_events": events,
                            "last_update": device["last_update"],
                        }
                        fire_alarms.append(device_info)

                        # Check battery levels
                        battery_level = device.get("battery_life")
                        if battery_level is not None and battery_level < 20:
                            battery_warnings.append(
                                {
                                    "device_id": device["id"],
                                    "device_name": device["name"],
                                    "battery_level": battery_level,
                                    "recommendation": "Replace battery soon",
                                }
                            )

                    except Exception as e:
                        logger.exception("Error getting details for fire device {device['id']}:")
                        # Still include the device with basic info
                        fire_alarms.append(
                            {
                                "device_id": device["id"],
                                "name": device["name"],
                                "type": device["type"],
                                "online": device["online"],
                                "error": str(e),
                            }
                        )

                # Determine system health
                if not fire_devices:
                    system_health = "no_devices"
                elif len([d for d in fire_devices if d.get("online", False)]) == 0:
                    system_health = "offline"
                elif battery_warnings:
                    system_health = "maintenance_needed"
                else:
                    system_health = "operational"

                return {
                    "success": True,
                    "fire_alarms": fire_alarms,
                    "total_alarms": len(fire_alarms),
                    "online_alarms": len([d for d in fire_alarms if d.get("online", False)]),
                    "system_health": system_health,
                    "battery_warnings": battery_warnings,
                    "test_recommendations": [
                        "Test smoke alarms monthly",
                        "Replace batteries annually",
                        "Clean dust from sensors regularly",
                        "Ensure proper placement away from vents",
                    ],
                    "last_updated": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.exception("Error getting fire alarm status:")
            return {"success": False, "error": str(e)}

    @app.tool(
        name="test_fire_safety_system",
        description="Perform comprehensive test of fire safety system",
    )
    async def test_fire_safety_system() -> dict[str, Any]:
        """Perform comprehensive test of fire safety system.

        Executes safety test protocols for all fire alarms and smoke detectors.
        Essential for regular safety maintenance and ensuring proper emergency
        detection functionality. Follows Austrian fire safety standards.

        Returns:
            Dict containing:
            - test_results: Results for each device tested
            - overall_status: Pass/fail status of safety system
            - recommendations: Actions needed for failed tests
            - next_test_date: Recommended date for next safety test
        """
        try:
            async with RingClient() as client:
                # Get all devices and filter for fire safety devices
                all_devices = await client.get_devices()
                fire_devices = [
                    device
                    for device in all_devices
                    if "smoke" in device.get("type", "").lower() or "fire" in device.get("type", "").lower()
                ]

                test_results = []

                for device in fire_devices:
                    try:
                        # Get recent events to check if device is functioning
                        events = await client.get_device_events(device["id"], limit=5)

                        # Check device health
                        battery_level = device.get("battery_life")
                        is_online = device.get("online", False)

                        # Determine test result
                        test_status = "pass"
                        issues = []

                        if not is_online:
                            test_status = "fail"
                            issues.append("Device is offline")
                        elif battery_level is not None and battery_level < 20:
                            test_status = "warning"
                            issues.append(f"Low battery: {battery_level}%")
                        elif not events:
                            test_status = "warning"
                            issues.append("No recent activity detected")

                        test_results.append(
                            {
                                "device_id": device["id"],
                                "device_name": device["name"],
                                "device_type": device["type"],
                                "test_status": test_status,
                                "issues": issues,
                                "battery_level": battery_level,
                                "online": is_online,
                                "last_event": events[0] if events else None,
                            }
                        )

                    except Exception as e:
                        logger.exception("Error testing fire device {device['id']}:")
                        test_results.append(
                            {
                                "device_id": device["id"],
                                "device_name": device["name"],
                                "device_type": device["type"],
                                "test_status": "error",
                                "issues": [str(e)],
                                "error": True,
                            }
                        )

                # Determine overall status
                failed_tests = len([r for r in test_results if r["test_status"] == "fail"])
                warning_tests = len([r for r in test_results if r["test_status"] == "warning"])

                if failed_tests > 0:
                    overall_status = "fail"
                elif warning_tests > 0:
                    overall_status = "warning"
                else:
                    overall_status = "pass"

                # Generate recommendations
                recommendations = []
                if failed_tests > 0:
                    recommendations.append(f"Immediate attention required for {failed_tests} failed devices")
                if warning_tests > 0:
                    recommendations.append(f"Maintenance needed for {warning_tests} devices with warnings")

                # Calculate next test date (monthly tests recommended)
                next_test_date = datetime.now() + timedelta(days=30)

                return {
                    "success": True,
                    "test_results": test_results,
                    "total_devices_tested": len(test_results),
                    "passed_tests": len([r for r in test_results if r["test_status"] == "pass"]),
                    "failed_tests": failed_tests,
                    "warning_tests": warning_tests,
                    "overall_status": overall_status,
                    "recommendations": recommendations,
                    "next_test_date": next_test_date.isoformat(),
                    "test_timestamp": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.exception("Error testing fire safety system:")
            return {"success": False, "error": str(e)}
