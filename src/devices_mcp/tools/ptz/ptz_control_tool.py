"""
PTZ Control Portmanteau Tool

Combines multiple PTZ operations into a single, more efficient tool:
- Move PTZ (pan, tilt, zoom)
- Get PTZ position
- Stop PTZ movement
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


@tool("ptz_control")
class PTZControlTool(BaseTool):
    """Comprehensive PTZ control tool.

    Provides unified control for PTZ camera operations including movement,
    position retrieval, and stopping operations.

    Parameters:
        operation: Type of PTZ operation (move, position, stop).
        camera_id: ID of the camera to control.
        pan: Pan direction (-1 to 1) for move operation.
        tilt: Tilt direction (-1 to 1) for move operation.
        zoom: Zoom direction (-1 to 1) for move operation.
        duration: Movement duration in seconds for move operation.

    Returns:
        A dictionary containing the PTZ operation result.
    """

    class Meta:
        name = "ptz_control"
        description = "Unified PTZ control for movement, position, and stopping operations"
        category = ToolCategory.PTZ

        class Parameters(BaseModel):
            operation: str = Field(
                ..., description="PTZ operation type: 'move', 'position', 'stop'"
            )
            camera_id: str = Field(..., description="Camera ID to control")
            pan: Optional[float] = Field(None, description="Pan direction (-1 to 1)")
            tilt: Optional[float] = Field(None, description="Tilt direction (-1 to 1)")
            zoom: Optional[float] = Field(None, description="Zoom direction (-1 to 1)")
            duration: Optional[float] = Field(None, description="Movement duration in seconds")

    async def execute(
        self,
        operation: str,
        camera_id: str,
        pan: Optional[float] = None,
        tilt: Optional[float] = None,
        zoom: Optional[float] = None,
        duration: Optional[float] = None,
        speed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute PTZ control operation."""
        try:
            logger.info(f"PTZ {operation} operation for camera {camera_id}")

            if operation == "move":
                return await self._move_ptz(camera_id, pan, tilt, zoom, duration)
            if operation == "position":
                return await self._get_position(camera_id)
            if operation == "stop":
                return await self._stop_ptz(camera_id)
            return {
                "success": False,
                "error": f"Invalid operation: {operation}. Must be 'move', 'position', or 'stop'",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception(f"PTZ {operation} operation failed")
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "camera_id": camera_id,
                "timestamp": time.time(),
            }

    async def _move_ptz(
        self,
        camera_id: str,
        pan: Optional[float],
        tilt: Optional[float],
        zoom: Optional[float],
        duration: Optional[float],
    ) -> Dict[str, Any]:
        """Move PTZ camera."""
        # Validate parameters
        if pan is None and tilt is None and zoom is None:
            return {
                "success": False,
                "error": "At least one movement parameter (pan, tilt, zoom) must be provided",
                "timestamp": time.time(),
            }

        # Validate ranges
        for param, value in [("pan", pan), ("tilt", tilt), ("zoom", zoom)]:
            if value is not None and not (-1 <= value <= 1):
                return {
                    "success": False,
                    "error": f"{param} value must be between -1 and 1",
                    "timestamp": time.time(),
                }

        # Simulate PTZ movement
        movement = {}
        if pan is not None:
            movement["pan"] = pan
        if tilt is not None:
            movement["tilt"] = tilt
        if zoom is not None:
            movement["zoom"] = zoom

        # Simulate movement duration
        if duration and duration > 0:
            await asyncio.sleep(min(duration, 5.0))  # Cap at 5 seconds for simulation

        return {
            "success": True,
            "operation": "move",
            "camera_id": camera_id,
            "movement": movement,
            "duration": duration,
            "message": f"PTZ movement executed: {movement}",
            "timestamp": time.time(),
        }

    async def _get_position(self, camera_id: str) -> Dict[str, Any]:
        """Get current PTZ position."""
        # Simulate position data
        import secrets

        position = {
            "pan": round(-180 + secrets.randbelow(361), 1),  # -180 to 180
            "tilt": round(-90 + secrets.randbelow(181), 1),  # -90 to 90
            "zoom": round(secrets.randbelow(101), 1),  # 0 to 100
        }

        return {
            "success": True,
            "operation": "position",
            "camera_id": camera_id,
            "position": position,
            "message": f"Current PTZ position: {position}",
            "timestamp": time.time(),
        }

    async def _stop_ptz(self, camera_id: str) -> Dict[str, Any]:
        """Stop PTZ movement."""
        return {
            "success": True,
            "operation": "stop",
            "camera_id": camera_id,
            "message": "PTZ movement stopped",
            "timestamp": time.time(),
        }
