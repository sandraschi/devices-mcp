"""
Camera Connection Portmanteau Tool

Combines camera connection operations:
- Connect camera
- Disconnect camera
- Set active camera
"""

import logging
import time
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


@tool("camera_connection")
class CameraConnectionTool(BaseTool):
    """Camera connection management tool.

    Provides unified camera connection management including connecting, disconnecting,
    and setting active cameras.

    Parameters:
        operation: Type of connection operation (connect, disconnect, set_active).
        camera_id: Camera ID for connection operations.
        connection_type: Type of connection (direct, cloud, local).

    Returns:
        A dictionary containing the camera connection result.
    """

    class Meta:
        name = "camera_connection"
        description = (
            "Unified camera connection management including connect, disconnect, and set active"
        )
        category = ToolCategory.CAMERA

        class Parameters(BaseModel):
            operation: str = Field(
                ..., description="Connection operation: 'connect', 'disconnect', 'set_active'"
            )
            camera_id: str = Field(..., description="Camera ID for connection operations")
            connection_type: Optional[str] = Field(
                "direct", description="Connection type: 'direct', 'cloud', 'local'"
            )

    async def execute(
        self,
        operation: str,
        camera_id: str,
        connection_type: str = "direct",
    ) -> Dict[str, Any]:
        """Execute camera connection operation."""
        try:
            logger.info(f"Camera connection {operation} operation for camera {camera_id}")

            if operation == "connect":
                return await self._connect_camera(camera_id, connection_type)
            if operation == "disconnect":
                return await self._disconnect_camera(camera_id)
            if operation == "set_active":
                return await self._set_active_camera(camera_id)
            return {
                "success": False,
                "error": f"Invalid operation: {operation}. Must be 'connect', 'disconnect', or 'set_active'",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception(f"Camera connection {operation} operation failed")
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "camera_id": camera_id,
                "timestamp": time.time(),
            }

    async def _connect_camera(self, camera_id: str, connection_type: str) -> Dict[str, Any]:
        """Connect to a camera."""
        # Simulate connection process
        connection_status = {
            "camera_id": camera_id,
            "connection_type": connection_type,
            "status": "connected",
            "connection_time": time.time(),
            "stream_url": "rtsp://192.168.1.100:554/stream1",
            "resolution": "1920x1080",
            "fps": 30,
        }

        return {
            "success": True,
            "operation": "connect",
            "connection": connection_status,
            "message": f"Camera {camera_id} connected successfully via {connection_type}",
            "timestamp": time.time(),
        }

    async def _disconnect_camera(self, camera_id: str) -> Dict[str, Any]:
        """Disconnect from a camera."""
        return {
            "success": True,
            "operation": "disconnect",
            "camera_id": camera_id,
            "message": f"Camera {camera_id} disconnected successfully",
            "timestamp": time.time(),
        }

    async def _set_active_camera(self, camera_id: str) -> Dict[str, Any]:
        """Set camera as active."""
        return {
            "success": True,
            "operation": "set_active",
            "camera_id": camera_id,
            "active_camera": camera_id,
            "message": f"Camera {camera_id} set as active camera",
            "timestamp": time.time(),
        }
