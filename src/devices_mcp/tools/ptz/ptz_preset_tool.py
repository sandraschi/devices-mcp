"""
PTZ Preset Management Portmanteau Tool

Combines PTZ preset operations into a single tool:
- Get PTZ presets
- Save PTZ preset
- Recall PTZ preset
- Go to home position
"""

import logging
import time
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


@tool("ptz_preset")
class PTZPresetTool(BaseTool):
    """PTZ preset management tool.

    Provides comprehensive preset management including listing, saving,
    recalling presets, and home position control.

    Parameters:
        operation: Type of preset operation (list, save, recall, home).
        camera_id: ID of the camera to control.
        preset_name: Name of the preset for save/recall operations.
        preset_id: ID of the preset for recall operations.

    Returns:
        A dictionary containing the preset operation result.
    """

    class Meta:
        name = "ptz_preset"
        description = (
            "PTZ preset management including listing, saving, recalling, and home position"
        )
        category = ToolCategory.PTZ

        class Parameters(BaseModel):
            operation: str = Field(
                ..., description="Preset operation: 'list', 'save', 'recall', 'home'"
            )
            camera_id: str = Field(..., description="Camera ID to control")
            preset_name: Optional[str] = Field(
                None, description="Preset name for save/recall operations"
            )
            preset_id: Optional[int] = Field(None, description="Preset ID for recall operations")

    async def execute(
        self,
        operation: str,
        camera_id: str,
        preset_name: Optional[str] = None,
        preset_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute PTZ preset operation."""
        try:
            logger.info(f"PTZ preset {operation} operation for camera {camera_id}")

            if operation == "list":
                return await self._list_presets(camera_id)
            if operation == "save":
                return await self._save_preset(camera_id, preset_name)
            if operation == "recall":
                return await self._recall_preset(camera_id, preset_id, preset_name)
            if operation == "home":
                return await self._go_home(camera_id)
            return {
                "success": False,
                "error": f"Invalid operation: {operation}. Must be 'list', 'save', 'recall', or 'home'",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception(f"PTZ preset {operation} operation failed")
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "camera_id": camera_id,
                "timestamp": time.time(),
            }

    async def _list_presets(self, camera_id: str) -> Dict[str, Any]:
        """List all PTZ presets."""
        # Simulate preset data
        presets = [
            {"id": 1, "name": "Front Door", "pan": 0.0, "tilt": 0.0, "zoom": 25.0},
            {"id": 2, "name": "Driveway", "pan": 45.0, "tilt": -10.0, "zoom": 50.0},
            {"id": 3, "name": "Garden", "pan": -30.0, "tilt": 15.0, "zoom": 30.0},
            {"id": 4, "name": "Street View", "pan": 90.0, "tilt": -5.0, "zoom": 75.0},
        ]

        return {
            "success": True,
            "operation": "list",
            "camera_id": camera_id,
            "presets": presets,
            "total_presets": len(presets),
            "message": f"Found {len(presets)} PTZ presets",
            "timestamp": time.time(),
        }

    async def _save_preset(self, camera_id: str, preset_name: Optional[str]) -> Dict[str, Any]:
        """Save current PTZ position as preset."""
        if not preset_name:
            return {
                "success": False,
                "error": "Preset name is required for save operation",
                "timestamp": time.time(),
            }

        # Simulate getting current position and saving
        import secrets

        current_position = {
            "pan": round(-180 + secrets.randbelow(361), 1),
            "tilt": round(-90 + secrets.randbelow(181), 1),
            "zoom": round(secrets.randbelow(101), 1),
        }

        preset_id = secrets.randbelow(100) + 1

        return {
            "success": True,
            "operation": "save",
            "camera_id": camera_id,
            "preset_name": preset_name,
            "preset_id": preset_id,
            "position": current_position,
            "message": f"Preset '{preset_name}' saved with ID {preset_id}",
            "timestamp": time.time(),
        }

    async def _recall_preset(
        self, camera_id: str, preset_id: Optional[int], preset_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Recall PTZ preset by ID or name."""
        # If preset_id is not provided but preset_name is, try to find the ID
        if preset_id is None and preset_name:
            # Get list of presets to find ID by name
            presets_list = await self._list_presets(camera_id)
            if presets_list.get("success") and presets_list.get("presets"):
                for preset in presets_list["presets"]:
                    if preset.get("name") == preset_name:
                        preset_id = preset.get("id")
                        break

        if preset_id is None:
            return {
                "success": False,
                "error": "Preset ID or preset_name is required for recall operation",
                "timestamp": time.time(),
            }

        # Simulate preset recall
        preset_positions = {
            1: {"pan": 0.0, "tilt": 0.0, "zoom": 25.0},
            2: {"pan": 45.0, "tilt": -10.0, "zoom": 50.0},
            3: {"pan": -30.0, "tilt": 15.0, "zoom": 30.0},
            4: {"pan": 90.0, "tilt": -5.0, "zoom": 75.0},
        }

        if preset_id not in preset_positions:
            return {
                "success": False,
                "error": f"Preset ID {preset_id} not found",
                "timestamp": time.time(),
            }

        position = preset_positions[preset_id]

        return {
            "success": True,
            "operation": "recall",
            "camera_id": camera_id,
            "preset_id": preset_id,
            "position": position,
            "message": f"Recalled preset {preset_id}: {position}",
            "timestamp": time.time(),
        }

    async def _go_home(self, camera_id: str) -> Dict[str, Any]:
        """Move PTZ to home position."""
        home_position = {"pan": 0.0, "tilt": 0.0, "zoom": 25.0}

        return {
            "success": True,
            "operation": "home",
            "camera_id": camera_id,
            "position": home_position,
            "message": "PTZ moved to home position",
            "timestamp": time.time(),
        }
