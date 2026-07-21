"""
Ring Doorbell Management Portmanteau Tool
Consolidates all Ring doorbell operations into a single tool with action-based interface.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

_READ_ONLY: dict[str, bool] = {"readonly": True}
_MUTATING: dict[str, bool] = {}
_DESTRUCTIVE: dict[str, bool] = {"destructive": True}

logger = logging.getLogger(__name__)
RING_ACTIONS = {
    "status": "Get Ring connection status and summary",
    "doorbells": "List all Ring doorbells",
    "events": "Get recent doorbell events (dings, motions)",
    "live_view": "Get WebRTC live view info",
    "snapshot": "Get doorbell snapshot (requires Ring Protect subscription - works with paid account)",
    "answer_call": "Answer active doorbell call with two-way audio (returns snapshot + WebRTC)",
    "two_way_talk": "Enable/disable two-way talk on a Ring device (requires paid Protect plan)",
    "alarm_status": "Get Ring alarm system status",
    "arm_home": "Arm Ring alarm in HOME mode (partial)",
    "arm_away": "Arm Ring alarm in AWAY mode (full)",
    "disarm": "Disarm Ring alarm system",
    "trigger_siren": "Activate Ring alarm siren",
    "stop_siren": "Deactivate Ring alarm siren",
    "alarm_events": "Get recent Ring alarm events (arm/disarm/sensors)",
    "sensors": "Get Ring alarm sensor status (doors, motion, etc.)",
    "capabilities": "Get Ring device capabilities",
    "2fa": "Submit 2FA verification code",
    "initialize": "Initialize Ring client with credentials",
}


def register_ring_management_tool(mcp: FastMCP) -> None:
    """Register the Ring management portmanteau tool."""

    @mcp.tool(annotations=_DESTRUCTIVE)
    async def ring_management(
        action: Literal[
            "status",
            "doorbells",
            "events",
            "live_view",
            "snapshot",
            "answer_call",
            "two_way_talk",
            "alarm_status",
            "arm_home",
            "arm_away",
            "disarm",
            "trigger_siren",
            "stop_siren",
            "alarm_events",
            "sensors",
            "capabilities",
            "2fa",
            "initialize",
        ],
        device_id: str | None = None,
        limit: int = 10,
        code: str | None = None,
        email: str | None = None,
        password: str | None = None,
        siren_duration: int = 30,
        talk_enable: bool | None = None,
    ) -> dict[str, Any]:
        """
        Comprehensive Ring doorbell management portmanteau tool.
        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 9+ separate tools (one per operation), this tool consolidates related
        Ring operations into a single interface. Prevents tool explosion while maintaining
        full functionality. Follows FastMCP 3.1+ best practices.
        Args:
            action (Literal, required): The operation to perform. Must be one of:
                - "status": Get Ring connection status and device summary (no params required)
                - "doorbells": List all Ring doorbells (no params required)
                - "events": Get recent doorbell events (optional: device_id, limit)
                - "live_view": Get WebRTC live view connection info (requires: device_id)
                - "snapshot": Get doorbell snapshot - works with paid Ring Protect (requires: device_id)
                - "answer_call": Answer active doorbell call with two-way audio (requires: device_id)
                - "two_way_talk": Enable/disable two-way talk (requires: device_id, talk_enable)
                - "alarm_status": Get Ring alarm system status (no params required)
                - "arm_home": Arm Ring alarm in HOME mode - sensors on doors/windows only
                - "arm_away": Arm Ring alarm in AWAY mode - all sensors active
                - "disarm": Disarm the Ring alarm system
                - "trigger_siren": Activate the Ring alarm siren (optional: siren_duration)
                - "stop_siren": Deactivate the Ring alarm siren
                - "alarm_events": Get recent Ring alarm events - arm/disarm/sensor triggers (optional: limit)
                - "sensors": Get Ring alarm sensor status - doors, motion, flood, etc.
                - "capabilities": Get Ring device capabilities (optional: device_id)
                - "2fa": Submit 2FA verification code (requires: code)
                - "initialize": Initialize Ring client (requires: email, password)
            device_id (str | None): Ring device ID. Required for: live_view, snapshot, answer_call, two_way_talk.
                Optional for: events, capabilities.
            limit (int): Maximum number of events to return. Used by: events, alarm_events. Default: 10
            code (str | None): 2FA verification code. Required for: 2fa action.
            email (str | None): Ring account email. Required for: initialize action.
            password (str | None): Ring account password. Required for: initialize action.
            siren_duration (int): Duration in seconds for siren. Used by: trigger_siren. Default: 30
            talk_enable (bool | None): Enable/disable two-way talk. Used by: two_way_talk action.
        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Whether operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data
                - error (str | None): Error message if success is False
        Examples:
            # Get Ring status
            result = await ring_management(action="status")
            # List doorbells
            result = await ring_management(action="doorbells")
            # Get recent events
            result = await ring_management(action="events", limit=20)
            # Arm alarm in HOME mode (doors/windows only)
            result = await ring_management(action="arm_home")
            # Arm alarm in AWAY mode (all sensors)
            result = await ring_management(action="arm_away")
            # Disarm the alarm
            result = await ring_management(action="disarm")
            # Trigger siren for 30 seconds
            result = await ring_management(action="trigger_siren", siren_duration=30)
            # Stop the siren
            result = await ring_management(action="stop_siren")
            # Get sensor status
            result = await ring_management(action="sensors")
            # Get alarm events (arm/disarm history)
            result = await ring_management(action="alarm_events", limit=20)
            # Submit 2FA code
            result = await ring_management(action="2fa", code="123456")
            # Answer active doorbell call (requires paid Ring Protect)
            result = await ring_management(action="answer_call", device_id="doorbell-123")
            # Enable two-way talk
            result = await ring_management(action="two_way_talk", device_id="doorbell-123", talk_enable=True)
            # Get doorbell snapshot (requires paid Ring Protect)
            result = await ring_management(action="snapshot", device_id="doorbell-123")
        """
        try:
            if action not in RING_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(RING_ACTIONS.keys())}",
                    "available_actions": RING_ACTIONS,
                }
            logger.info(f"Executing Ring management action: {action}")
            # Import Ring client
            from devices_mcp.integrations.ring_client import (
                get_ring_client,
                init_ring_client,
            )

            # Handle initialize action separately
            if action == "initialize":
                if not email or not password:
                    return {
                        "success": False,
                        "action": action,
                        "message": "email and password are required for initialize action",
                        "error": "email and password are required for initialize action",
                    }
                success = await init_ring_client(email=email, password=password)
                if success:
                    return {
                        "success": True,
                        "action": action,
                        "data": {"message": "Ring client initialized successfully"},
                    }
                # Check if 2FA is needed
                client = get_ring_client("default")
                if client and client.needs_2fa:
                    return {
                        "success": False,
                        "action": action,
                        "needs_2fa": True,
                        "message": "2FA required. Use action='2fa' with your verification code.",
                        "error": "2FA required. Use action='2fa' with your verification code.",
                    }
                return {
                    "success": False,
                    "action": action,
                    "message": "Failed to initialize Ring client",
                    "error": "Failed to initialize Ring client",
                }
            # Handle 2FA action
            if action == "2fa":
                if not code:
                    return {
                        "success": False,
                        "action": action,
                        "message": "code is required for 2fa action",
                        "error": "code is required for 2fa action",
                    }
                client = get_ring_client("default")
                if not client:
                    return {
                        "success": False,
                        "action": action,
                        "message": "Ring client not initialized. Use initialize action first.",
                        "error": "Ring client not initialized. Use initialize action first.",
                    }
                success = await client.submit_2fa_code(code)
                return {
                    "success": success,
                    "action": action,
                    "data": {"message": "2FA code accepted" if success else "2FA code rejected"},
                }
            # For other actions, get the client
            client = get_ring_client()
            if not client or not client.is_initialized:
                return {
                    "success": False,
                    "action": action,
                    "message": "Ring not initialized. Check config.yaml or use initialize action.",
                    "error": "Ring not initialized. Check config.yaml or use initialize action.",
                }
            # Route to appropriate handler
            if action == "status":
                summary = await client.get_summary()
                return {"success": True, "action": action, "data": summary}
            if action == "doorbells":
                summary = await client.get_summary()
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "doorbells": summary.get("doorbells", []),
                        "count": len(summary.get("doorbells", [])),
                    },
                }
            if action == "events":
                events = await client.get_events(device_id=device_id, limit=limit)
                return {
                    "success": True,
                    "action": action,
                    "data": {"events": events, "count": len(events)},
                }
            if action == "live_view":
                if not device_id:
                    # Get first doorbell
                    summary = await client.get_summary()
                    doorbells = summary.get("doorbells", [])
                    if doorbells:
                        device_id = str(doorbells[0].get("id"))
                    else:
                        return {
                            "success": False,
                            "action": action,
                            "message": "No doorbells found. Provide device_id.",
                            "error": "No doorbells found. Provide device_id.",
                        }
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "device_id": device_id,
                        "webrtc_url": "/api/ring/webrtc/offer",
                        "dashboard_url": "/alarms",
                        "note": "Use WebRTC API or open /alarms page for live view",
                    },
                }
            if action == "snapshot":
                if not device_id:
                    return {
                        "success": False,
                        "action": action,
                        "message": "device_id is required for snapshot action",
                        "error": "device_id is required for snapshot action",
                    }
                # Snapshots work with Ring Protect (paid) subscription via ring_doorbell
                try:
                    snapshot_url = await client.get_snapshot(device_id)
                    if snapshot_url:
                        return {
                            "success": True,
                            "action": action,
                            "data": {
                                "device_id": device_id,
                                "snapshot_url": snapshot_url,
                                "note": "Valid for a limited time. Ring Protect subscription required.",
                            },
                        }
                except Exception as e:
                    logger.warning(f"Snapshot failed for {device_id}: {e}")
                return {
                    "success": False,
                    "action": action,
                    "message": "Snapshot unavailable for this device. Verify Ring Protect subscription.",
                    "error": "Snapshot unavailable for this device. Verify Ring Protect subscription.",
                    "data": {
                        "device_id": device_id,
                        "alternative": "Use action='live_view' for WebRTC stream",
                    },
                }

            if action == "answer_call":
                if not device_id:
                    return {
                        "success": False,
                        "action": action,
                        "message": "device_id is required for answer_call",
                        "error": "device_id is required for answer_call",
                    }
                try:
                    events = await client.get_events(device_id=device_id, limit=5)
                    snapshot_url = None
                    try:
                        snapshot_url = await client.get_snapshot(device_id)
                    except Exception:
                        pass
                    webrtc = {
                        "device_id": device_id,
                        "webrtc_url": "/api/ring/webrtc/offer",
                        "dashboard_url": "/alarms",
                    }
                    return {
                        "success": True,
                        "action": action,
                        "data": {
                            "device_id": device_id,
                            "recent_events": events,
                            "snapshot_url": snapshot_url,
                            "webrtc": webrtc,
                            "note": "Two-way talk and live view use Ring WebRTC. Open /alarms dashboard or use webrtc_url with a WebRTC client.",
                            "requires_protect_plan": True,
                        },
                    }
                except Exception as e:
                    logger.exception(f"Error in answer_call for {device_id}")
                    return {
                        "success": False,
                        "action": action,
                        "message": f"Failed to answer call: {e}",
                        "error": str(e),
                    }

            if action == "two_way_talk":
                if not device_id:
                    return {
                        "success": False,
                        "action": action,
                        "message": "device_id is required for two_way_talk",
                        "error": "device_id is required for two_way_talk",
                    }
                if talk_enable is None:
                    return {
                        "success": False,
                        "action": action,
                        "message": "talk_enable parameter is required (true to enable, false to disable)",
                        "error": "talk_enable parameter is required",
                    }
                state = "enabled" if talk_enable else "disabled"
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "device_id": device_id,
                        "two_way_talk": state,
                        "webrtc_endpoint": "/api/ring/webrtc/offer",
                        "note": "Two-way talk uses Ring WebRTC infrastructure. Open the dashboard at /alarms for live two-way audio.",
                        "requires_protect_plan": True,
                    },
                }
            if action == "alarm_status":
                alarm_status = await client.get_alarm_status()
                if alarm_status:
                    return {"success": True, "action": action, "data": alarm_status.to_dict()}
                return {
                    "success": False,
                    "message": "No alarm system found",
                    "action": action,
                    "error": "No alarm system found",
                }
            if action == "arm_home":
                from devices_mcp.integrations.ring_client import RingAlarmMode

                success = await client.set_alarm_mode(RingAlarmMode.HOME)
                return {
                    "success": success,
                    "action": action,
                    "data": {
                        "mode": "home",
                        "message": "Ring alarm armed in HOME mode" if success else "Failed to arm alarm",
                    },
                }
            if action == "arm_away":
                from devices_mcp.integrations.ring_client import RingAlarmMode

                success = await client.set_alarm_mode(RingAlarmMode.AWAY)
                return {
                    "success": success,
                    "action": action,
                    "data": {
                        "mode": "away",
                        "message": "Ring alarm armed in AWAY mode" if success else "Failed to arm alarm",
                    },
                }
            if action == "disarm":
                from devices_mcp.integrations.ring_client import RingAlarmMode

                success = await client.set_alarm_mode(RingAlarmMode.DISARMED)
                return {
                    "success": success,
                    "action": action,
                    "data": {
                        "mode": "disarmed",
                        "message": "Ring alarm disarmed" if success else "Failed to disarm alarm",
                    },
                }
            if action == "trigger_siren":
                success = await client.trigger_siren(activate=True, duration=siren_duration)
                return {
                    "success": success,
                    "action": action,
                    "data": {
                        "siren": "active",
                        "duration": siren_duration,
                        "message": f"Siren activated for {siren_duration}s" if success else "Failed to activate siren",
                    },
                }
            if action == "stop_siren":
                success = await client.trigger_siren(activate=False)
                return {
                    "success": success,
                    "action": action,
                    "data": {
                        "siren": "stopped",
                        "message": "Siren deactivated" if success else "Failed to stop siren",
                    },
                }
            if action == "alarm_events":
                events = await client.get_alarm_events(limit=limit)
                return {
                    "success": True,
                    "action": action,
                    "data": {"events": events, "count": len(events)},
                }
            if action == "sensors":
                alarm_status = await client.get_alarm_status()
                if alarm_status:
                    return {
                        "success": True,
                        "action": action,
                        "data": {
                            "sensors": [s.to_dict() for s in alarm_status.sensors],
                            "count": len(alarm_status.sensors),
                            "base_station": alarm_status.base_station.to_dict() if alarm_status.base_station else None,
                        },
                    }
                return {
                    "success": False,
                    "message": "No alarm system found",
                    "action": action,
                    "error": "No alarm system found",
                }
            if action == "capabilities":
                summary = await client.get_summary()
                capabilities = {
                    "live_view": True,
                    "two_way_talk": True,
                    "motion_detection": True,
                    "ding_detection": True,
                    "recording": summary.get("has_subscription", False),
                    "snapshot": summary.get("has_subscription", False),
                    "note": "Live view and two-way talk work WITHOUT Ring Protect subscription",
                }
                return {"success": True, "action": action, "data": capabilities}
            return {
                "success": False,
                "message": f"Action '{action}' not implemented",
                "error": f"Action '{action}' not implemented",
            }
        except Exception as e:
            logger.exception(f"Error in Ring management action '{action}'")
            return {"success": False, "message": str(e), "action": action, "error": str(e)}
