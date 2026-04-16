"""
PTZ (Pan-Tilt-Zoom) tools for Devices MCP.

This module contains tools for controlling PTZ functionality of Tapo cameras.
"""

from typing import Any

from pydantic import Field

from .base_tool import BaseTool, ToolCategory, tool


@tool(name="move_ptz", category=ToolCategory.CAMERA)
class MovePTZTool(BaseTool):
    """Move the PTZ camera to a specific position."""

    class Meta:
        name = "move_ptz"
        description = "Move the PTZ camera to a specific position"
        category = ToolCategory.CAMERA

        class Parameters:
            pan: float = Field(..., ge=-1.0, le=1.0, description="Pan position (-1.0 to 1.0)")
            tilt: float = Field(..., ge=-1.0, le=1.0, description="Tilt position (-1.0 to 1.0)")
            zoom: float = Field(..., ge=0.0, le=1.0, description="Zoom level (0.0 to 1.0)")

    pan: float
    tilt: float
    zoom: float

    async def execute(self) -> dict[str, Any]:
        """Execute the move PTZ tool."""
        return {
            "status": "moved",
            "position": {"pan": self.pan, "tilt": self.tilt, "zoom": self.zoom},
        }


@tool(name="save_ptz_preset", category=ToolCategory.CAMERA)
class SavePTZPresetTool(BaseTool):
    """Save the current PTZ position as a preset."""

    class Meta:
        name = "save_ptz_preset"
        description = "Save the current PTZ position as a preset"
        category = ToolCategory.CAMERA

        class Parameters:
            preset_name: str = Field(..., description="Name for the preset")

    preset_name: str

    async def execute(self) -> dict[str, Any]:
        """Execute the save PTZ preset tool."""
        return {"status": "preset_saved", "preset_name": self.preset_name}


@tool(name="recall_ptz_preset", category=ToolCategory.CAMERA)
class RecallPTZPresetTool(BaseTool):
    """Recall a saved PTZ preset."""

    class Meta:
        name = "recall_ptz_preset"
        description = "Recall a saved PTZ preset"
        category = ToolCategory.CAMERA

        class Parameters:
            preset_name: str = Field(..., description="Name of the preset to recall")

    preset_name: str

    async def execute(self) -> dict[str, Any]:
        """Execute the recall PTZ preset tool."""
        return {"status": "preset_recalled", "preset_name": self.preset_name}


@tool(name="get_ptz_presets", category=ToolCategory.CAMERA)
class GetPTZPresetsTool(BaseTool):
    """Get a list of saved PTZ presets."""

    class Meta:
        name = "get_ptz_presets"
        description = "Get a list of saved PTZ presets"
        category = ToolCategory.CAMERA

        class Parameters:
            pass

    async def execute(self) -> list[dict[str, Any]]:
        """Execute the get PTZ presets tool."""
        return []


@tool(name="go_to_home_ptz", category=ToolCategory.CAMERA)
class GoToHomePTZTool(BaseTool):
    """Move the PTZ camera to its home position."""

    class Meta:
        name = "go_to_home_ptz"
        description = "Move the PTZ camera to its home position"
        category = ToolCategory.CAMERA

        class Parameters:
            pass

    async def execute(self) -> dict[str, Any]:
        """Execute the go to home PTZ tool."""
        return {"status": "moved_to_home"}


@tool(name="stop_ptz", category=ToolCategory.CAMERA)
class StopPTZTool(BaseTool):
    """Stop all PTZ movement."""

    class Meta:
        name = "stop_ptz"
        description = "Stop all PTZ movement"
        category = ToolCategory.CAMERA

        class Parameters:
            pass

    async def execute(self) -> dict[str, Any]:
        """Execute the stop PTZ tool."""
        return {"status": "stopped"}


@tool(name="get_ptz_position", category=ToolCategory.CAMERA)
class GetPTZPositionTool(BaseTool):
    """Get the current PTZ position."""

    class Meta:
        name = "get_ptz_position"
        description = "Get the current PTZ position"
        category = ToolCategory.CAMERA

        class Parameters:
            pass

    async def execute(self) -> dict[str, float]:
        """Execute the get PTZ position tool."""
        return {"pan": 0.0, "tilt": 0.0, "zoom": 0.0}
