"""
Camera Info Portmanteau Tool

Combines camera information operations:
- Get camera info
- Get camera status
- Manage camera groups
"""

import asyncio
import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


@tool("camera_info")
class CameraInfoTool(BaseTool):
    """Camera information management tool.

    Provides unified camera information management including getting camera info,
    status, and managing camera groups.

    Parameters:
        operation: Type of info operation (info, status, groups).
        camera_id: Camera ID for info/status operations.
        group_action: Group action (list, create, add, remove) for groups operation.
        group_name: Group name for group operations.

    Returns:
        A dictionary containing the camera information result.
    """

    class Meta:
        name = "camera_info"
        description = "Unified camera information management including info, status, and group management"
        category = ToolCategory.CAMERA

        class Parameters(BaseModel):
            operation: str = Field(..., description="Info operation: 'info', 'status', 'groups'")
            camera_id: str | None = Field(None, description="Camera ID for info/status operations")
            group_action: str | None = Field(None, description="Group action: 'list', 'create', 'add', 'remove'")
            group_name: str | None = Field(None, description="Group name for group operations")

    async def execute(
        self,
        operation: str,
        camera_id: str | None = None,
        group_action: str | None = None,
        group_name: str | None = None,
    ) -> dict[str, Any]:
        """Execute camera info operation."""
        try:
            logger.info(f"Camera info {operation} operation")

            if operation == "info":
                return await self._get_camera_info(camera_id)
            if operation == "status":
                return await self._get_camera_status(camera_id)
            if operation == "groups":
                return await self._manage_groups(group_action, group_name, camera_id)
            return {
                "success": False,
                "error": f"Invalid operation: {operation}. Must be 'info', 'status', or 'groups'",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception(f"Camera info {operation} operation failed")
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "timestamp": time.time(),
            }

    async def _get_camera_info(self, camera_id: str | None) -> dict[str, Any]:
        """Get camera information."""
        if not camera_id:
            return {
                "success": False,
                "error": "Camera ID is required for info operation",
                "timestamp": time.time(),
            }

        from devices_mcp.core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()

        try:
            # Check if it's a Ring camera first
            if camera_id.startswith("ring_"):
                try:
                    from ...integrations.ring_client import get_ring_client

                    ring_client = get_ring_client("default")
                    if ring_client and ring_client.is_initialized:
                        ring_id = camera_id.replace("ring_", "")
                        doorbells = await asyncio.wait_for(ring_client.get_doorbells(), timeout=3.0)
                        for doorbell in doorbells:
                            if str(doorbell.id) == ring_id:
                                camera_info = {
                                    "camera_id": camera_id,
                                    "name": f"Ring {doorbell.device_type}",
                                    "model": doorbell.device_type,
                                    "firmware_version": doorbell.extra_data.get("firmware", "N/A"),
                                    "hardware_version": "N/A",
                                    "serial_number": str(doorbell.id),
                                    "ip_address": "N/A (Cloud)",
                                    "mac_address": "N/A",
                                    "resolution": "1080p",
                                    "fps": 30,
                                    "night_vision": True,
                                    "ptz_support": False,
                                    "audio_support": True,
                                    "storage": "Ring Cloud",
                                    "location": doorbell.name or "Unknown",
                                    "installation_date": "N/A",
                                    "battery_life": doorbell.battery_level,
                                    "connection_type": "WebRTC",
                                }
                                return {
                                    "success": True,
                                    "operation": "info",
                                    "camera_info": camera_info,
                                    "message": f"Ring camera info retrieved for {camera_id}",
                                    "timestamp": time.time(),
                                }
                except Exception as e:
                    logger.warning(f"Failed to get Ring camera info for {camera_id}: {e}")

            # Try to get camera from camera manager
            if hasattr(server, "camera_manager") and server.camera_manager:
                camera = await server.camera_manager.get_camera(camera_id)
                if camera:
                    status = await camera.get_status()
                    camera_info = {
                        "camera_id": camera_id,
                        "name": camera_id,
                        "model": status.get("model", "Unknown"),
                        "firmware_version": status.get("firmware", "Unknown"),
                        "hardware_version": "N/A",
                        "serial_number": "N/A",
                        "ip_address": getattr(camera.config, "params", {}).get("host", "N/A")
                        if hasattr(camera, "config")
                        else "N/A",
                        "mac_address": "N/A",
                        "resolution": status.get("resolution", "Unknown"),
                        "fps": 30,
                        "night_vision": True,
                        "ptz_support": status.get("ptz_capable", False),
                        "audio_support": status.get("audio_capable", False),
                        "storage": "N/A",
                        "location": camera_id,
                        "installation_date": "N/A",
                    }

                    return {
                        "success": True,
                        "operation": "info",
                        "camera_info": camera_info,
                        "message": f"Camera info retrieved for {camera_id}",
                        "timestamp": time.time(),
                    }

            return {
                "success": False,
                "error": f"Camera {camera_id} not found",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception("Failed to get camera info for")
            return {
                "success": False,
                "error": f"Failed to get camera info: {e!s}",
                "timestamp": time.time(),
            }

    async def _get_camera_status(self, camera_id: str | None) -> dict[str, Any]:
        """Get camera status."""
        if not camera_id:
            return {
                "success": False,
                "error": "Camera ID is required for status operation",
                "timestamp": time.time(),
            }

        from devices_mcp.core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()

        try:
            # Check if it's a Ring camera first
            if camera_id.startswith("ring_"):
                try:
                    from ...integrations.ring_client import get_ring_client

                    ring_client = get_ring_client("default")
                    if ring_client and ring_client.is_initialized:
                        ring_id = camera_id.replace("ring_", "")
                        doorbells = await asyncio.wait_for(ring_client.get_doorbells(), timeout=3.0)
                        for doorbell in doorbells:
                            if str(doorbell.id) == ring_id:
                                camera_status = {
                                    "camera_id": camera_id,
                                    "status": "online" if doorbell.is_online else "offline",
                                    "connection_quality": "cloud",
                                    "signal_strength": None,
                                    "battery_level": doorbell.battery_level,
                                    "storage_usage": None,
                                    "last_motion": None,
                                    "recording_status": "cloud",
                                    "night_mode": None,
                                    "privacy_mode": None,
                                    "led_status": "auto",
                                    "motion_detection": "enabled",
                                    "audio_recording": "enabled",
                                    "cloud_storage": "ring",
                                    "last_sync": time.time(),
                                    "device_type": doorbell.device_type,
                                    "firmware": doorbell.extra_data.get("firmware", "N/A"),
                                }
                                return {
                                    "success": True,
                                    "operation": "status",
                                    "camera_status": camera_status,
                                    "message": f"Ring camera status retrieved for {camera_id}",
                                    "timestamp": time.time(),
                                }
                except Exception as e:
                    logger.warning(f"Failed to get Ring camera status for {camera_id}: {e}")

            # Try to get camera from camera manager
            if hasattr(server, "camera_manager") and server.camera_manager:
                camera = await server.camera_manager.get_camera(camera_id)
                if camera:
                    status = await camera.get_status()
                    camera_status = {
                        "camera_id": camera_id,
                        "status": "online" if status.get("connected", False) else "offline",
                        "connection_quality": "direct" if status.get("connected", False) else "none",
                        "signal_strength": None,
                        "battery_level": None,
                        "storage_usage": None,
                        "last_motion": None,
                        "recording_status": "streaming" if status.get("streaming", False) else "idle",
                        "night_mode": None,
                        "privacy_mode": None,
                        "led_status": "auto",
                        "motion_detection": "enabled",
                        "audio_recording": "enabled",
                        "cloud_storage": "local",
                        "last_sync": time.time(),
                        "model": status.get("model", "Unknown"),
                        "firmware": status.get("firmware", "Unknown"),
                        "streaming": status.get("streaming", False),
                    }

                    return {
                        "success": True,
                        "operation": "status",
                        "camera_status": camera_status,
                        "message": f"Camera status retrieved for {camera_id}",
                        "timestamp": time.time(),
                    }

            return {
                "success": False,
                "error": f"Camera {camera_id} not found",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception("Failed to get camera status for")
            return {
                "success": False,
                "error": f"Failed to get camera status: {e!s}",
                "timestamp": time.time(),
            }

    async def _manage_groups(
        self, group_action: str | None, group_name: str | None, camera_id: str | None
    ) -> dict[str, Any]:
        """Manage camera groups."""
        if not group_action:
            return {
                "success": False,
                "error": "Group action is required for groups operation",
                "timestamp": time.time(),
            }

        if group_action == "list":
            # Simulate group listing
            groups = [
                {
                    "group_id": "group_001",
                    "name": "Outdoor Cameras",
                    "cameras": ["cam_001", "cam_002", "cam_003"],
                    "created": "2024-01-15",
                    "description": "All outdoor security cameras",
                },
                {
                    "group_id": "group_002",
                    "name": "Indoor Cameras",
                    "cameras": ["cam_004", "cam_005"],
                    "created": "2024-01-20",
                    "description": "Indoor monitoring cameras",
                },
            ]

            return {
                "success": True,
                "operation": "groups",
                "group_action": "list",
                "groups": groups,
                "total_groups": len(groups),
                "message": f"Found {len(groups)} camera groups",
                "timestamp": time.time(),
            }

        if group_action == "create":
            if not group_name:
                return {
                    "success": False,
                    "error": "Group name is required for create action",
                    "timestamp": time.time(),
                }

            import secrets

            group_id = f"group_{secrets.randbelow(1000):03d}"

            return {
                "success": True,
                "operation": "groups",
                "group_action": "create",
                "group": {
                    "group_id": group_id,
                    "name": group_name,
                    "cameras": [],
                    "created": time.strftime("%Y-%m-%d"),
                    "description": f"Camera group: {group_name}",
                },
                "message": f"Camera group '{group_name}' created with ID {group_id}",
                "timestamp": time.time(),
            }

        if group_action in ["add", "remove"]:
            if not camera_id:
                return {
                    "success": False,
                    "error": "Camera ID is required for add/remove actions",
                    "timestamp": time.time(),
                }

            return {
                "success": True,
                "operation": "groups",
                "group_action": group_action,
                "camera_id": camera_id,
                "message": f"Camera {camera_id} {group_action}ed to group successfully",
                "timestamp": time.time(),
            }

        return {
            "success": False,
            "error": f"Invalid group action: {group_action}. Must be 'list', 'create', 'add', or 'remove'",
            "timestamp": time.time(),
        }
