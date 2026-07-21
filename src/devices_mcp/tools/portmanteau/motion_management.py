"""
Motion Detection Management Portmanteau Tool
Consolidates all motion detection operations into a single tool with action-based interface.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

_READ_ONLY: dict[str, bool] = {"readonly": True}
_MUTATING: dict[str, bool] = {}
_DESTRUCTIVE: dict[str, bool] = {"destructive": True}

logger = logging.getLogger(__name__)
MOTION_ACTIONS = {
    "status": "Get motion detection subscription status",
    "events": "Get recent motion events",
    "subscribe": "Subscribe to motion events from a camera",
    "unsubscribe": "Unsubscribe from motion events",
    "test": "Test if camera supports ONVIF motion events",
    "capabilities": "Get motion detection capabilities overview",
}


def register_motion_management_tool(mcp: FastMCP) -> None:
    """Register the motion management portmanteau tool."""

    @mcp.tool(annotations=_READ_ONLY)
    async def motion_management(
        action: Literal["status", "events", "subscribe", "unsubscribe", "test", "capabilities"],
        camera_id: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """
        Comprehensive motion detection management portmanteau tool.
        PORTMANTEAU PATTERN RATIONALE:
        Consolidates motion detection operations into a single interface.
        Note: Tapo C200 cameras have limited ONVIF event support. For reliable
        motion alerts, use the Tapo app. Ring doorbell motion events work fully.
        Args:
            action (Literal, required): The operation to perform. Must be one of:
                - "status": Get motion subscription status (no params required)
                - "events": Get recent motion events (optional: camera_id, limit)
                - "subscribe": Subscribe to camera motion (requires: camera_id)
                - "unsubscribe": Unsubscribe from camera (requires: camera_id)
                - "test": Test ONVIF event support (requires: camera_id)
                - "capabilities": Get motion capabilities overview (no params required)
            camera_id (str | None): Camera identifier. Required for: subscribe, unsubscribe, test.
                Optional for: events (filters by camera).
            limit (int): Maximum events to return. Used by: events action. Default: 20
        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Whether operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data
                - error (str | None): Error message if success is False
        Examples:
            # Get motion capabilities
            result = await motion_management(action="capabilities")
            # Get subscription status
            result = await motion_management(action="status")
            # Get all recent motion events
            result = await motion_management(action="events", limit=50)
            # Get events for specific camera
            result = await motion_management(action="events", camera_id="kitchen_cam")
            # Test if camera supports motion events
            result = await motion_management(action="test", camera_id="kitchen_cam")
            # Subscribe to motion events
            result = await motion_management(action="subscribe", camera_id="kitchen_cam")
        """
        try:
            if action not in MOTION_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(MOTION_ACTIONS.keys())}",
                    "available_actions": MOTION_ACTIONS,
                }
            logger.info(f"Executing motion management action: {action}")
            # Import motion event functions
            from devices_mcp.integrations.onvif_events import (
                get_recent_events,
                get_subscription_status,
                subscribe_to_camera,
                unsubscribe_from_camera,
            )

            if action == "capabilities":
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "onvif_cameras": {
                            "motion_detection": "Limited",
                            "note": "Tapo C200 has Events service but no PullPointSubscription. "
                            "Use Tapo app for reliable motion alerts.",
                        },
                        "ring_doorbell": {
                            "motion_detection": "Full",
                            "note": "Ring motion/ding events work via API. See /alarms page.",
                        },
                        "tapo_app": {
                            "motion_detection": "Full",
                            "note": "Best option for Tapo camera motion alerts with zones and sensitivity.",
                        },
                        "recommendation": "For Tapo cameras, use Tapo app for motion notifications. "
                        "This dashboard is best for live viewing and PTZ control.",
                    },
                }
            if action == "status":
                status = await get_subscription_status()
                return {"success": True, "action": action, "data": status}
            if action == "events":
                events = get_recent_events(camera_id=camera_id, limit=limit)
                return {
                    "success": True,
                    "action": action,
                    "data": {"events": events, "count": len(events), "camera_id": camera_id},
                }
            # Actions requiring camera_id
            if not camera_id:
                return {
                    "success": False,
                    "action": action,
                    "message": f"camera_id is required for '{action}' action",
                }
            if action == "test":
                # Test ONVIF event support
                from devices_mcp.core.server import TapoCameraServer

                server = await TapoCameraServer.get_instance()
                camera = await server.camera_manager.get_camera(camera_id)
                if not camera:
                    return {
                        "success": False,
                        "action": action,
                        "message": f"Camera '{camera_id}' not found",
                    }
                camera_type = camera.config.type
                if hasattr(camera_type, "value"):
                    camera_type = camera_type.value
                if camera_type != "onvif":
                    return {
                        "success": True,
                        "action": action,
                        "data": {
                            "camera_id": camera_id,
                            "camera_type": camera_type,
                            "onvif_events_support": False,
                            "note": "Not an ONVIF camera - motion events not supported via this tool",
                        },
                    }
                # Try to check ONVIF event capabilities
                try:
                    import asyncio

                    from onvif import ONVIFCamera

                    host = camera.config.params.get("host")
                    port = camera.config.params.get("onvif_port", 2020)
                    username = camera.config.params.get("username")
                    password = camera.config.params.get("password")
                    loop = asyncio.get_event_loop()

                    def check_events():
                        cam = ONVIFCamera(host, port, username, password)
                        try:
                            cam.create_events_service()  # Test if service exists
                            return {"has_events_service": True}
                        except Exception as e:
                            return {"has_events_service": False, "error": str(e)}

                    details = await loop.run_in_executor(None, check_events)
                    return {
                        "success": True,
                        "action": action,
                        "data": {
                            "camera_id": camera_id,
                            "camera_type": camera_type,
                            "onvif_events_support": details.get("has_events_service", False),
                            "details": details,
                            "note": "Has Events service but PullPointSubscription may not work. "
                            "Use Tapo app for reliable motion alerts.",
                        },
                    }
                except Exception as e:
                    return {
                        "success": False,
                        "action": action,
                        "message": f"Failed to test event support: {e}",
                    }
            if action == "subscribe":
                # Get camera info for subscription
                from devices_mcp.core.server import TapoCameraServer

                server = await TapoCameraServer.get_instance()
                camera = await server.camera_manager.get_camera(camera_id)
                if not camera:
                    return {
                        "success": False,
                        "action": action,
                        "message": f"Camera '{camera_id}' not found",
                    }
                camera_type = camera.config.type
                if hasattr(camera_type, "value"):
                    camera_type = camera_type.value
                if camera_type != "onvif":
                    return {
                        "success": False,
                        "action": action,
                        "message": f"Camera '{camera_id}' is not ONVIF. Motion events only for ONVIF cameras.",
                    }
                host = camera.config.params.get("host")
                port = camera.config.params.get("onvif_port", 2020)
                username = camera.config.params.get("username")
                password = camera.config.params.get("password")
                success = await subscribe_to_camera(camera_id, host, port, username, password)
                if success:
                    return {
                        "success": True,
                        "action": action,
                        "data": {
                            "camera_id": camera_id,
                            "subscribed": True,
                            "note": "Subscribed to motion events. Use events action to retrieve them.",
                        },
                    }
                return {
                    "success": False,
                    "action": action,
                    "message": f"Failed to subscribe to '{camera_id}'. Camera may not support ONVIF events.",
                    "note": "Tapo C200 has limited ONVIF event support. Use Tapo app for motion alerts.",
                }
            if action == "unsubscribe":
                await unsubscribe_from_camera(camera_id)
                return {
                    "success": True,
                    "action": action,
                    "data": {"camera_id": camera_id, "unsubscribed": True},
                }
            return {
                "success": False,
                "message": f"Action '{action}' not implemented",
                "error": f"Action '{action}' not implemented",
            }
        except Exception as e:
            logger.exception(f"Error in motion management action '{action}'")
            return {"success": False, "message": str(e), "action": action, "error": str(e)}
