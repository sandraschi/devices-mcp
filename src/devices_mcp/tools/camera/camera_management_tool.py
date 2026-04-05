"""
Camera Management Portmanteau Tool

Combines camera management operations:
- List cameras
- Add camera
- Remove camera
"""

import logging
import time
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


@tool("camera_management")
class CameraManagementTool(BaseTool):
    """Camera management tool.

    Provides unified camera management including listing, adding, and removing cameras.

    Parameters:
        operation: Type of management operation (list, add, remove).
        camera_id: Camera ID for add/remove operations.
        camera_name: Camera name for add operations.
        camera_ip: Camera IP address for add operations.
        camera_username: Camera username for add operations.
        camera_password: Camera password for add operations.

    Returns:
        A dictionary containing the camera management result.
    """

    class Meta:
        name = "camera_management"
        description = "Unified camera management including listing, adding, and removing cameras"
        category = ToolCategory.CAMERA

        class Parameters(BaseModel):
            operation: str = Field(..., description="Management operation: 'list', 'add', 'remove'")
            camera_id: Optional[str] = Field(None, description="Camera ID for operations")
            camera_name: Optional[str] = Field(None, description="Camera name for add operations")
            camera_ip: Optional[str] = Field(
                None, description="Camera IP address for add operations"
            )
            camera_username: Optional[str] = Field(
                None, description="Camera username for add operations"
            )
            camera_password: Optional[str] = Field(
                None, description="Camera password for add operations"
            )

    async def execute(
        self,
        operation: str,
        camera_id: Optional[str] = None,
        camera_name: Optional[str] = None,
        camera_ip: Optional[str] = None,
        camera_username: Optional[str] = None,
        camera_password: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute camera management operation."""
        try:
            logger.info(f"Camera management {operation} operation")

            if operation == "list":
                return await self._list_cameras()
            if operation == "add":
                return await self._add_camera(
                    camera_name, camera_ip, camera_username, camera_password
                )
            if operation == "remove":
                return await self._remove_camera(camera_id)
            return {
                "success": False,
                "error": f"Invalid operation: {operation}. Must be 'list', 'add', or 'remove'",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception(f"Camera management {operation} operation failed")
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "timestamp": time.time(),
            }

    async def _list_cameras(self) -> Dict[str, Any]:
        """List all cameras."""
        # Simulate camera data
        cameras = [
            {
                "camera_id": "cam_001",
                "name": "Front Door Camera",
                "ip_address": "192.168.1.100",
                "status": "online",
                "model": "Tapo C200",
                "location": "Front Door",
                "last_seen": time.time() - 300,
            },
            {
                "camera_id": "cam_002",
                "name": "Backyard Camera",
                "ip_address": "192.168.1.101",
                "status": "online",
                "model": "Tapo C310",
                "location": "Backyard",
                "last_seen": time.time() - 120,
            },
            {
                "camera_id": "cam_003",
                "name": "Driveway Camera",
                "ip_address": "192.168.1.102",
                "status": "offline",
                "model": "Tapo C210",
                "location": "Driveway",
                "last_seen": time.time() - 3600,
            },
        ]

        online_count = len([c for c in cameras if c["status"] == "online"])

        return {
            "success": True,
            "operation": "list",
            "cameras": cameras,
            "total_cameras": len(cameras),
            "online_cameras": online_count,
            "offline_cameras": len(cameras) - online_count,
            "message": f"Found {len(cameras)} cameras ({online_count} online)",
            "timestamp": time.time(),
        }

    async def _add_camera(
        self,
        camera_name: Optional[str],
        camera_ip: Optional[str],
        camera_username: Optional[str],
        camera_password: Optional[str],
    ) -> Dict[str, Any]:
        """Add a new camera."""
        if not all([camera_name, camera_ip, camera_username, camera_password]):
            return {
                "success": False,
                "error": "All camera parameters (name, ip, username, password) are required for add operation",
                "timestamp": time.time(),
            }

        # Generate new camera ID
        import secrets

        camera_id = f"cam_{secrets.randbelow(1000):03d}"

        # Simulate camera addition
        new_camera = {
            "camera_id": camera_id,
            "name": camera_name,
            "ip_address": camera_ip,
            "status": "online",
            "model": "Tapo C200",
            "location": "Unknown",
            "last_seen": time.time(),
        }

        return {
            "success": True,
            "operation": "add",
            "camera": new_camera,
            "message": f"Camera '{camera_name}' added successfully with ID {camera_id}",
            "timestamp": time.time(),
        }

    async def _remove_camera(self, camera_id: Optional[str]) -> Dict[str, Any]:
        """Remove a camera."""
        if not camera_id:
            return {
                "success": False,
                "error": "Camera ID is required for remove operation",
                "timestamp": time.time(),
            }

        # Simulate camera removal
        return {
            "success": True,
            "operation": "remove",
            "camera_id": camera_id,
            "message": f"Camera {camera_id} removed successfully",
            "timestamp": time.time(),
        }
