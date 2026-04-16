"""Device status tools for Nest Protect MCP."""

from typing import Any

from pydantic import BaseModel, Field


class EmptyParams(BaseModel):
    """Empty parameters for tools that don't need input."""


class DeviceIdParams(BaseModel):
    """Parameters for device-specific operations."""

    device_id: str = Field(..., description="ID of the device")


class DeviceEventsParams(BaseModel):
    """Parameters for getting device events."""

    device_id: str = Field(..., description="ID of the device")
    limit: int = Field(10, ge=1, le=100, description="Maximum number of events to return")


async def list_devices() -> dict[str, Any]:
    """List all Nest Protect devices with conversational response format."""
    import aiohttp

    from ..state_manager import get_app_state

    state = get_app_state()

    if not state.access_token:
        return {
            "success": False,
            "error": "Authentication required",
            "error_code": "AUTHENTICATION_REQUIRED",
            "message": "You need to authenticate with the Nest API first",
            "recovery_options": [
                "Run 'initiate_oauth_flow' to start authentication",
                "Check your OAuth tokens are properly configured",
            ],
            "diagnostic_info": {
                "root_cause": "Missing or invalid access token",
                "affected_components": ["Nest API connection"],
            },
            "alternative_solutions": [
                "Re-run OAuth authentication flow",
                "Refresh your access tokens",
            ],
            "estimated_resolution_time": "< 5 minutes",
            "urgency": "high",
        }

    try:
        url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{state.config.project_id}/devices"
        headers = {"Authorization": f"Bearer {state.access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    devices = data.get("devices", [])
                    device_list = [
                        {
                            "id": d["name"].split("/")[-1],
                            "type": d.get("type", "").split(".")[-1],
                            "name": d.get("traits", {}).get("sdm.devices.traits.Info", {}).get("customName", ""),
                            "model": d.get("traits", {}).get("sdm.devices.traits.Info", {}).get("modelNumber", ""),
                            "online": d.get("traits", {}).get("sdm.devices.traits.Connectivity", {}).get("status")
                            == "ONLINE",
                        }
                        for d in devices
                    ]

                    device_types = [d["type"] for d in device_list if d["type"]]
                    online_count = sum(1 for d in device_list if d["online"])

                    return {
                        "success": True,
                        "operation": "list_devices",
                        "summary": f"Found {len(devices)} Nest Protect devices ({online_count} online)",
                        "result": {
                            "count": len(devices),
                            "devices": device_list,
                            "stats": {
                                "total": len(devices),
                                "online": online_count,
                                "offline": len(devices) - online_count,
                                "types": list(set(device_types)),
                            },
                        },
                        "next_steps": [
                            "Run 'get_device_status' to check individual device details",
                            "Use 'run_safety_check' to test device functionality",
                        ]
                        if devices
                        else ["Add Nest Protect devices to your account"],
                        "context": {
                            "operation_details": f"Retrieved device information from {len(devices)} Nest Protect devices",
                            "api_response": f"Successfully queried Nest API for enterprise {state.config.project_id}",
                        },
                        "suggestions": [
                            "Consider running safety checks on offline devices",
                            "Review battery levels for devices showing low power",
                        ]
                        if any(not d["online"] for d in device_list)
                        else [],
                        "follow_up_questions": [
                            "Would you like me to check the status of a specific device?",
                            "Should I run safety checks on any of these devices?",
                        ],
                    }
                error = await response.json()
                return {
                    "success": False,
                    "error": "API request failed",
                    "error_code": f"API_ERROR_{response.status}",
                    "message": "Failed to retrieve device list from Nest API",
                    "recovery_options": [
                        "Check your internet connection",
                        "Verify OAuth tokens are valid",
                        "Try refreshing access tokens",
                    ],
                    "diagnostic_info": {
                        "root_cause": error.get("error", {}).get("message", "Unknown API error"),
                        "affected_components": ["Nest API connection"],
                        "http_status": response.status,
                    },
                    "alternative_solutions": [
                        "Run 'refresh_access_token' to update authentication",
                        "Check API service status",
                    ],
                    "estimated_resolution_time": "< 10 minutes",
                    "urgency": "medium",
                }
    except Exception as e:
        return {
            "success": False,
            "error": "Unexpected error occurred",
            "error_code": "INTERNAL_ERROR",
            "message": "Failed to list devices due to internal error",
            "recovery_options": [
                "Check server logs for more details",
                "Restart the MCP server",
                "Verify network connectivity",
            ],
            "diagnostic_info": {
                "root_cause": str(e),
                "affected_components": ["Device listing functionality"],
            },
            "alternative_solutions": [
                "Try again in a few moments",
                "Contact support if issue persists",
            ],
            "estimated_resolution_time": "< 15 minutes",
            "urgency": "medium",
        }


async def get_device_status(device_id: str) -> dict[str, Any]:
    """Get status of a specific Nest Protect device with conversational response format."""
    import aiohttp

    from ..state_manager import get_app_state

    state = get_app_state()

    if not state.access_token:
        return {
            "success": False,
            "error": "Authentication required",
            "error_code": "AUTHENTICATION_REQUIRED",
            "message": "You need to authenticate with the Nest API first",
            "recovery_options": [
                "Run 'initiate_oauth_flow' to start authentication",
                "Check your OAuth tokens are properly configured",
            ],
            "diagnostic_info": {
                "root_cause": "Missing or invalid access token",
                "affected_components": ["Nest API connection"],
            },
            "alternative_solutions": [
                "Re-run OAuth authentication flow",
                "Refresh your access tokens",
            ],
            "estimated_resolution_time": "< 5 minutes",
            "urgency": "high",
        }

    try:
        url = (
            f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{state.config.project_id}/devices/{device_id}"
        )
        headers = {"Authorization": f"Bearer {state.access_token}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    device = await response.json()
                    traits = device.get("traits", {})
                    info = traits.get("sdm.devices.traits.Info", {})
                    connectivity = traits.get("sdm.devices.traits.Connectivity", {})

                    device_status = {
                        "id": device_id,
                        "name": info.get("customName", ""),
                        "model": info.get("modelNumber", ""),
                        "online": connectivity.get("status") == "ONLINE",
                        "battery": {
                            "level": traits.get("sdm.devices.traits.Battery", {}).get("batteryLevel"),
                            "status": traits.get("sdm.devices.traits.Battery", {}).get("batteryStatus"),
                        },
                        "alarm": {
                            "status": traits.get("sdm.devices.traits.SafetyAlarm", {}).get("alarmStatus"),
                            "last_event": traits.get("sdm.devices.traits.SafetyAlarm", {}).get("lastEvent"),
                        },
                        "smoke": {
                            "status": traits.get("sdm.devices.traits.Smoke", {}).get("smokeStatus"),
                            "last_event": traits.get("sdm.devices.traits.Smoke", {}).get("lastEvent"),
                        },
                        "co": {
                            "status": traits.get("sdm.devices.traits.CarbonMonoxide", {}).get("coStatus"),
                            "level_ppm": traits.get("sdm.devices.traits.CarbonMonoxide", {}).get("coLevel"),
                            "last_event": traits.get("sdm.devices.traits.CarbonMonoxide", {}).get("lastEvent"),
                        },
                        "heat": {
                            "status": traits.get("sdm.devices.traits.Heat", {}).get("heatStatus"),
                            "temperature_c": traits.get("sdm.devices.traits.Temperature", {}).get("temperature"),
                            "humidity": traits.get("sdm.devices.traits.Humidity", {}).get("humidity"),
                        },
                        "last_update": device.get("lastEventTime"),
                    }

                    # Analyze device health
                    health_issues = []
                    suggestions = []
                    follow_up_questions = []

                    if not device_status["online"]:
                        health_issues.append("Device is offline")
                        suggestions.append("Check device power and Wi-Fi connection")
                        follow_up_questions.append("Would you like me to try reconnecting the device?")

                    battery_level = device_status["battery"]["level"]
                    if battery_level and battery_level < 20:
                        health_issues.append(f"Low battery ({battery_level}%)")
                        suggestions.append("Replace the battery soon")
                        follow_up_questions.append("Should I schedule a battery replacement reminder?")

                    alarm_status = device_status["alarm"]["status"]
                    if alarm_status and alarm_status != "NONE":
                        health_issues.append(f"Active alarm: {alarm_status}")
                        suggestions.append("Investigate the alarm condition immediately")
                        follow_up_questions.append("Do you need help silencing this alarm?")

                    smoke_status = device_status["smoke"]["status"]
                    co_status = device_status["co"]["status"]
                    if smoke_status == "SMOKE_DETECTED" or co_status == "CO_DETECTED":
                        health_issues.append("Dangerous condition detected")
                        suggestions.append("Evacuate if necessary and call emergency services")
                        follow_up_questions.append("Are you safe? Should I help silence alarms?")

                    device_name = device_status["name"] or f"Device {device_id[:8]}"

                    return {
                        "success": True,
                        "operation": "get_device_status",
                        "summary": f"{device_name} is {'online' if device_status['online'] else 'offline'} with {len(health_issues)} health issue{'s' if len(health_issues) != 1 else ''}",
                        "result": {
                            "device": device_status,
                            "health_analysis": {
                                "issues": health_issues,
                                "overall_status": "critical"
                                if any("Dangerous condition" in issue for issue in health_issues)
                                else "warning"
                                if health_issues
                                else "good",
                            },
                        },
                        "next_steps": [
                            "Run 'run_safety_check' to test device functionality",
                            "Use 'get_device_events' to see recent activity",
                        ]
                        + (["Address health issues immediately"] if health_issues else []),
                        "context": {
                            "operation_details": f"Retrieved comprehensive status for Nest Protect device {device_id}",
                            "last_updated": device_status["last_update"],
                        },
                        "suggestions": suggestions,
                        "follow_up_questions": follow_up_questions,
                    }
                error = await response.json()
                return {
                    "success": False,
                    "error": "Device not found or API error",
                    "error_code": f"DEVICE_ERROR_{response.status}",
                    "message": f"Could not retrieve status for device {device_id}",
                    "recovery_options": [
                        "Verify the device ID is correct",
                        "Check if device is powered on and connected",
                        "Ensure device is registered in your Nest account",
                    ],
                    "diagnostic_info": {
                        "root_cause": error.get("error", {}).get("message", "Unknown device error"),
                        "affected_components": [f"Device {device_id}"],
                        "device_id": device_id,
                        "http_status": response.status,
                    },
                    "alternative_solutions": [
                        "Run 'list_devices' to see available devices",
                        "Check device connectivity and power status",
                    ],
                    "estimated_resolution_time": "< 10 minutes",
                    "urgency": "medium",
                }
    except Exception as e:
        return {
            "success": False,
            "error": "Unexpected error occurred",
            "error_code": "INTERNAL_ERROR",
            "message": f"Failed to get device status for {device_id}",
            "recovery_options": [
                "Check server logs for more details",
                "Try again in a few moments",
                "Verify device ID format is correct",
            ],
            "diagnostic_info": {
                "root_cause": str(e),
                "affected_components": [f"Device {device_id}"],
                "device_id": device_id,
            },
            "alternative_solutions": [
                "Run 'list_devices' to verify device exists",
                "Contact support if issue persists",
            ],
            "estimated_resolution_time": "< 15 minutes",
            "urgency": "medium",
        }


async def get_device_events(device_id: str, limit: int = 10) -> dict[str, Any]:
    """Get recent events for a Nest Protect device with conversational response format."""
    import aiohttp

    from ..state_manager import get_app_state

    state = get_app_state()

    if not state.access_token:
        return {
            "success": False,
            "error": "Authentication required",
            "error_code": "AUTHENTICATION_REQUIRED",
            "message": "You need to authenticate with the Nest API first",
            "recovery_options": [
                "Run 'initiate_oauth_flow' to start authentication",
                "Check your OAuth tokens are properly configured",
            ],
            "diagnostic_info": {
                "root_cause": "Missing or invalid access token",
                "affected_components": ["Nest API connection"],
            },
            "alternative_solutions": [
                "Re-run OAuth authentication flow",
                "Refresh your access tokens",
            ],
            "estimated_resolution_time": "< 5 minutes",
            "urgency": "high",
        }

    try:
        url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{state.config.project_id}/devices/{device_id}/events"
        headers = {"Authorization": f"Bearer {state.access_token}"}
        params = {"pageSize": min(max(1, limit), 100)}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    events = data.get("events", [])

                    formatted_events = []
                    event_types = set()
                    alarm_events = []
                    status_events = []

                    for event in events:
                        event_type = event.get("resourceType", "").split(".")[-1]
                        event_data = event.get("traits", {})

                        formatted_event = {
                            "event_id": event.get("eventId"),
                            "type": event_type,
                            "timestamp": event.get("timestamp"),
                            "data": event_data,
                        }
                        formatted_events.append(formatted_event)
                        event_types.add(event_type)

                        # Categorize events for analysis
                        if any(keyword in event_type.lower() for keyword in ["alarm", "smoke", "co", "safety"]):
                            alarm_events.append(formatted_event)
                        elif any(keyword in event_type.lower() for keyword in ["connectivity", "battery", "status"]):
                            status_events.append(formatted_event)

                    # Analyze event patterns
                    suggestions = []
                    follow_up_questions = []

                    if alarm_events:
                        suggestions.append("Review alarm events for safety concerns")
                        follow_up_questions.append("Would you like me to check current device status?")

                    if not formatted_events:
                        suggestions.append("Device may not have recent activity")
                        follow_up_questions.append("Should I run a safety check on this device?")

                    device_name = f"Device {device_id[:8]}"  # We don't have the friendly name here

                    return {
                        "success": True,
                        "operation": "get_device_events",
                        "summary": f"Retrieved {len(formatted_events)} recent events for {device_name} ({len(alarm_events)} alarms, {len(status_events)} status changes)",
                        "result": {
                            "count": len(formatted_events),
                            "events": formatted_events,
                            "analysis": {
                                "total_events": len(formatted_events),
                                "alarm_events": len(alarm_events),
                                "status_events": len(status_events),
                                "event_types": list(event_types),
                                "time_range": {
                                    "newest": formatted_events[0]["timestamp"] if formatted_events else None,
                                    "oldest": formatted_events[-1]["timestamp"] if formatted_events else None,
                                },
                            },
                        },
                        "next_steps": [
                            "Run 'get_device_status' for current device state",
                            "Use 'run_safety_check' to test device functionality",
                        ]
                        if formatted_events
                        else ["Run 'run_safety_check' to verify device is working"],
                        "context": {
                            "operation_details": f"Retrieved event history for device {device_id} (requested {limit} events)",
                            "device_id": device_id,
                            "limit_requested": limit,
                        },
                        "suggestions": suggestions,
                        "follow_up_questions": follow_up_questions,
                    }
                error = await response.json()
                return {
                    "success": False,
                    "error": "Events retrieval failed",
                    "error_code": f"EVENTS_ERROR_{response.status}",
                    "message": f"Could not retrieve event history for device {device_id}",
                    "recovery_options": [
                        "Verify the device ID is correct",
                        "Check device connectivity",
                        "Try a smaller limit value",
                    ],
                    "diagnostic_info": {
                        "root_cause": error.get("error", {}).get("message", "Unknown events error"),
                        "affected_components": [f"Device {device_id} events"],
                        "device_id": device_id,
                        "requested_limit": limit,
                        "http_status": response.status,
                    },
                    "alternative_solutions": [
                        "Run 'get_device_status' to verify device exists",
                        "Try with a smaller event limit (1-10)",
                    ],
                    "estimated_resolution_time": "< 10 minutes",
                    "urgency": "medium",
                }
    except Exception as e:
        return {
            "success": False,
            "error": "Unexpected error occurred",
            "error_code": "INTERNAL_ERROR",
            "message": f"Failed to get events for device {device_id}",
            "recovery_options": [
                "Check server logs for more details",
                "Try again in a few moments",
                "Verify device ID format",
            ],
            "diagnostic_info": {
                "root_cause": str(e),
                "affected_components": [f"Device {device_id} events"],
                "device_id": device_id,
                "requested_limit": limit,
            },
            "alternative_solutions": [
                "Run 'list_devices' to verify device exists",
                "Contact support if issue persists",
            ],
            "estimated_resolution_time": "< 15 minutes",
            "urgency": "medium",
        }
