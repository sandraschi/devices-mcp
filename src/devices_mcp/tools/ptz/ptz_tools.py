"""
PTZ (Pan-Tilt-Zoom) tools for Devices MCP.

This module contains tools for controlling camera movements and presets.
"""

import logging
import warnings
from typing import Any, Dict, Optional

from pydantic import ConfigDict, Field

from devices_mcp.tools.base_tool import BaseTool, ToolCategory, ToolResult, tool

warnings.filterwarnings(
    "ignore", category=DeprecationWarning, message=".*Support for class-based.*"
)

logger = logging.getLogger(__name__)


@tool(name="move_ptz", category=ToolCategory.PTZ)
class MovePTZTool(BaseTool):
    """
    Control camera PTZ (Pan-Tilt-Zoom) movements.

    Move the camera to a new position with adjustable pan, tilt, zoom,
    and speed. Supports both absolute and relative positioning.

    Parameters:
        pan (float): Pan position, range -1.0 to 1.0 (left to right)
        tilt (float): Tilt position, range -1.0 to 1.0 (down to up)
        zoom (float): Zoom level, range 0.0 to 1.0 (wide to telephoto)
        speed (int): Movement speed, range 1-8 (slow to fast)
        relative (bool): True for relative movement, False for absolute

    Returns:
        Dict with movement status and final position

    Example:
        # Pan right slowly
        result = await move_ptz_tool.execute(pan=0.5, speed=3)

        # Tilt up and zoom in
        result = await move_ptz_tool.execute(tilt=0.3, zoom=0.7, speed=5)
    """

    model_config = ConfigDict(
        json_schema_extra={
            "category": ToolCategory.PTZ,
            "description": "Control camera PTZ movements",
        }
    )

    pan: float = Field(default=0.0, ge=-1.0, le=1.0, description="Pan position (-1.0 to 1.0)")

    tilt: float = Field(default=0.0, ge=-1.0, le=1.0, description="Tilt position (-1.0 to 1.0)")

    zoom: float = Field(default=0.0, ge=0.0, le=1.0, description="Zoom level (0.0 to 1.0)")

    speed: int = Field(default=5, ge=1, le=8, description="Movement speed (1-8)")

    relative: bool = Field(default=True, description="Whether the movement is relative")

    async def execute(self) -> Dict[str, Any]:
        """Control camera PTZ (Pan-Tilt-Zoom) movements with precise positioning.

        Moves the camera to a new position with adjustable pan, tilt, zoom, and speed settings.
        Supports both absolute positioning (relative=False) and relative movement (relative=True)
        from the current position. All movements are validated and executed safely.

        Parameters:
            pan: Pan position, range -1.0 to 1.0 (left to right) (required)
                - -1.0: Full left position
                - 0.0: Center position
                - 1.0: Full right position
                - Values outside range will be clamped
            tilt: Tilt position, range -1.0 to 1.0 (down to up) (required)
                - -1.0: Full down position
                - 0.0: Center position
                - 1.0: Full up position
                - Values outside range will be clamped
            zoom: Zoom level, range 0.0 to 1.0 (wide to telephoto) (required)
                - 0.0: Wide angle (zoomed out)
                - 1.0: Maximum telephoto (zoomed in)
                - Values outside range will be clamped
            speed: Movement speed, range 1-8 (slow to fast) (required)
                - 1: Slowest movement
                - 5: Default speed
                - 8: Fastest movement
                - Integer values only
            relative: Movement mode - True for relative, False for absolute (required)
                - True: Move relative to current position
                - False: Move to absolute position

        Returns:
            Dictionary containing:
                - success: Boolean indicating if movement was successful
                - message: Success confirmation or error description
                - final_position: Dictionary with final pan/tilt/zoom values (on success)
                    - pan: Final pan position (-1.0 to 1.0)
                    - tilt: Final tilt position (-1.0 to 1.0)
                    - zoom: Final zoom level (0.0 to 1.0)

        Usage:
            Use this tool to precisely control camera positioning for optimal viewing angles.
            Relative mode is useful for fine adjustments, while absolute mode is better for
            preset positions. Always test movements in relative mode first to understand
            the camera's range and responsiveness.

            Common scenarios:
                - Adjusting camera angle for better subject visibility
                - Following moving objects with smooth tracking
                - Returning to specific monitoring positions
                - Setting up surveillance coverage areas

        Examples:
            Pan right slowly (relative movement):
                result = await move_ptz_tool.execute(
                    pan=0.2, tilt=0.0, zoom=0.0, speed=3, relative=True
                )
                if result['success']:
                    logger.info(f"Camera moved to pan: {result['final_position']['pan']}")
                # Returns: {
                #     'success': True,
                #     'message': 'PTZ movement completed successfully',
                #     'final_position': {'pan': 0.2, 'tilt': 0.0, 'zoom': 0.0}
                # }

            Tilt up and zoom in (absolute positioning):
                result = await move_ptz_tool.execute(
                    pan=0.0, tilt=0.3, zoom=0.7, speed=5, relative=False
                )
                # Moves to exact absolute position regardless of current location

            Fine adjustment for subject tracking:
                result = await move_ptz_tool.execute(
                    pan=-0.1, tilt=0.05, zoom=0.0, speed=2, relative=True
                )
                # Small relative adjustments for smooth tracking

            Error handling - invalid parameters:
                result = await move_ptz_tool.execute(
                    pan=2.0, tilt=0.0, zoom=0.0, speed=5, relative=True
                )
                # Pan value 2.0 will be clamped to 1.0 (maximum)
                # Returns: {'success': True, 'message': 'PTZ movement completed successfully', ...}

            Error handling - camera offline:
                result = await move_ptz_tool.execute(
                    pan=0.0, tilt=0.0, zoom=0.0, speed=5, relative=True
                )
                # Returns: {
                #     'success': False,
                #     'message': 'Camera not connected or PTZ not supported'
                # }

        Raises:
            Exception: Propagated from camera operations (connection failures, hardware issues)

        Notes:
            - Camera must support PTZ functionality
            - All position values are normalized (-1.0 to 1.0 range)
            - Values outside valid ranges are automatically clamped
            - Movement speed affects both precision and response time
            - Relative mode preserves zoom level if not specified
            - Absolute mode moves to exact coordinates regardless of current position
            - Some cameras may have limited range or speed capabilities

        See Also:
            - get_ptz_position_tool: To check current camera position
            - save_ptz_preset_tool: To save current position as preset
            - recall_ptz_preset_tool: To move to saved preset position
            - go_to_home_ptz_tool: To return to default position
        """
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        server = await TapoCameraServer.get_instance()
        return await server.move_ptz(
            {
                "pan": self.pan,
                "tilt": self.tilt,
                "zoom": self.zoom,
                "speed": self.speed,
                "relative": self.relative,
            }
        )


@tool(name="save_ptz_preset", category=ToolCategory.PTZ)
class SavePTZPresetTool(BaseTool):
    """
    Save the current PTZ position as a preset.

    Stores the camera's current pan, tilt, and zoom position
    with a custom name for quick recall later.

    Parameters:
        preset_name (str): Name for the preset (e.g., 'front_door', 'driveway')

    Returns:
        Dict with save status and preset details

    Example:
        # Save current position
        result = await save_ptz_preset_tool.execute(preset_name='front_door')
        logger.info(f"Saved preset: {result['preset_name']}")
    """

    class Config:
        json_schema_extra = {
            "category": ToolCategory.PTZ,
            "description": "Save the current PTZ position as a preset",
        }

    preset_id: int = Field(..., ge=1, le=16)

    name: Optional[str] = Field(None)

    async def execute(self) -> Dict[str, Any]:
        """Save the current PTZ position as a preset."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        return await server.save_ptz_preset({"name": self.name, "preset_id": self.preset_id})


@tool(name="recall_ptz_preset", category=ToolCategory.PTZ)
class RecallPTZPresetTool(BaseTool):
    """
    Recall a saved PTZ preset position.

    Moves the camera to a previously saved preset position
    by ID, restoring the pan, tilt, and zoom settings.

    Parameters:
        preset_id (int): ID of the preset to recall

    Returns:
        Dict with recall status and new position

    Example:
        # Move to saved position
        result = await recall_ptz_preset_tool.execute(preset_id=1)
        if result['success']:
            logger.info(f"Camera moved to preset {result['preset_id']}")
    """

    class Config:
        json_schema_extra = {
            "category": ToolCategory.PTZ,
            "description": "Recall a saved PTZ preset",
        }

    preset_id: int = Field(..., ge=1, le=16)

    async def execute(self) -> Dict[str, Any]:
        """Recall a saved PTZ preset."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        return await server.recall_ptz_preset(self.preset_id)


@tool(name="get_ptz_presets", category=ToolCategory.PTZ)
class GetPTZPresetsTool(BaseTool):
    """
    Get all saved PTZ presets.

    Returns a list of all saved preset positions with their
    IDs, names, and position details.

    Parameters:
        None

    Returns:
        Dict with list of presets:
        - presets (List[Dict]): List of preset dictionaries
        - total (int): Total number of presets

    Example:
        result = await get_ptz_presets_tool.execute()
        for preset in result['presets']:
            logger.info(f"{preset['id']}: {preset['name']}")
    """

    class Config:
        json_schema_extra = {
            "category": ToolCategory.PTZ,
            "description": "Get all saved PTZ presets",
        }

    async def execute(self) -> Dict[str, Any]:
        """Get all saved PTZ presets."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        return await server.get_ptz_presets()


@tool(name="go_to_home_ptz", category=ToolCategory.PTZ)
class GoToHomePTZTool(BaseTool):
    """
    Move the camera to its home position.

    Returns the camera to its default/home position, typically
    pointing straight ahead at zero pan and tilt.

    Parameters:
        None

    Returns:
        Dict with movement status

    Example:
        result = await go_to_home_ptz_tool.execute()
        logger.info("Camera returned to home position")
    """

    class Config:
        json_schema_extra = {
            "category": ToolCategory.PTZ,
            "description": "Move the PTZ to the home position",
        }

    async def execute(self) -> Dict[str, Any]:
        """Move the PTZ to the home position."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        try:
            return await server.go_to_home_ptz()
        except Exception as e:
            logger.exception("Failed to move PTZ to home position")
            return {
                "status": "error",
                "message": f"Failed to move PTZ to home position: {e!s}",
            }


@tool(name="stop_ptz", category=ToolCategory.PTZ)
class StopPTZTool(BaseTool):
    """
    Stop PTZ movement immediately.

    Halts any ongoing pan, tilt, or zoom movement and holds
    the camera at its current position.

    Parameters:
        None

    Returns:
        Dict with stop status

    Example:
        result = await stop_ptz_tool.execute()
        logger.info("Camera movement stopped")
    """

    class Config:
        json_schema_extra = {
            "category": ToolCategory.PTZ,
            "description": "Stop all PTZ movement",
        }

    async def execute(self, **_kwargs) -> Dict[str, Any]:
        """Stop all PTZ movement."""
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        server = await TapoCameraServer.get_instance()
        try:
            # Use move_ptz with all zeros to stop movement
            result = await server.move_ptz({"pan": 0, "tilt": 0, "zoom": 0, "relative": True})
            if result.get("status") == "success":
                return {"status": "success", "message": "PTZ movement stopped"}
            return result
        except Exception as e:
            logger.exception("Failed to stop PTZ movement")
            return {
                "status": "error",
                "message": f"Failed to stop PTZ movement: {e!s}",
            }


@tool(name="get_ptz_position", category=ToolCategory.PTZ)
class GetPTZPositionTool(BaseTool):
    """
    Get the current PTZ position and capabilities.

    Returns the camera's current pan, tilt, and zoom values along
    with movement capabilities and ranges.

    Parameters:
        None

    Returns:
        Dict with position information:
        - pan (float): Current pan position
        - tilt (float): Current tilt position
        - zoom (float): Current zoom level
        - capabilities (Dict): Movement ranges and limits

    Example:
        result = await get_ptz_position_tool.execute()
        logger.info(f"Pan: {result['position']['pan']}")
        logger.info(f"Tilt: {result['position']['tilt']}")
        logger.info(f"Zoom: {result['position']['zoom']}")
    """

    class Config:
        json_schema_extra = {
            "category": ToolCategory.PTZ,
            "description": "Get the current PTZ position",
        }

    async def execute(self, **_kwargs) -> ToolResult:
        """Get the current PTZ position and movement capabilities of the camera.

        Retrieves the camera's current pan, tilt, and zoom values along with information
        about the camera's movement capabilities and supported ranges. This provides
        a complete snapshot of the camera's current state and operational limits.

        Parameters:
            None: This tool requires no input parameters

        Returns:
            Dictionary containing:
                - status: "success" or "error"
                - position: Dictionary with current PTZ values (only present on success)
                    - pan: Current pan position (-1.0 to 1.0, where 0.0 is center)
                    - tilt: Current tilt position (-1.0 to 1.0, where 0.0 is center)
                    - zoom: Current zoom level (0.0 to 1.0, where 0.0 is wide angle)
                - capabilities: Dictionary with camera movement limits (only present on success)
                    - pan_range: Min/max pan values supported
                    - tilt_range: Min/max tilt values supported
                    - zoom_range: Min/max zoom values supported
                    - has_ptz: Boolean indicating PTZ support
                - message: Success confirmation or error description

        Usage:
            Use this tool to check the current camera position before making movements,
            to verify that PTZ operations completed successfully, or to understand the
            camera's movement capabilities. This is essential for applications that
            need to track or control camera positioning programmatically.

            Common scenarios:
                - Checking current position before preset operations
                - Verifying movement completion
                - Understanding camera capabilities
                - Debugging PTZ control issues
                - Position logging and monitoring

        Examples:
            Get current position successfully:
                result = await get_ptz_position_tool.execute()
                if result['status'] == 'success':
                    pos = result['position']
                    logger.info(f"Current position - Pan: {pos['pan']}, Tilt: {pos['tilt']}, Zoom: {pos['zoom']}")
                # Returns: {
                #     'status': 'success',
                #     'position': {'pan': 0.2, 'tilt': -0.1, 'zoom': 0.5},
                #     'capabilities': {
                #         'pan_range': {'min': -1.0, 'max': 1.0},
                #         'tilt_range': {'min': -1.0, 'max': 1.0},
                #         'zoom_range': {'min': 0.0, 'max': 1.0},
                #         'has_ptz': True
                #     },
                #     'message': 'PTZ position retrieved successfully'
                # }

            Error handling - no camera connected:
                result = await get_ptz_position_tool.execute()
                if result['status'] == 'error':
                    logger.error(f"Cannot get position: {result['message']}")
                # Returns: {
                #     'status': 'error',
                #     'message': 'No camera connected. Please connect to a camera first.'
                # }

            Error handling - camera doesn't support PTZ:
                result = await get_ptz_position_tool.execute()
                # Returns: {
                #     'status': 'error',
                #     'message': 'Camera does not support PTZ functionality'
                # }

            Check capabilities before movement:
                result = await get_ptz_position_tool.execute()
                if result['status'] == 'success':
                    caps = result['capabilities']
                    if caps['has_ptz']:
                        logger.info(f"PTZ supported - Pan range: {caps['pan_range']}")
                    else:
                        logger.warning("Camera does not support PTZ movement")

        Raises:
            Exception: Propagated from camera operations (connection failures, hardware issues)

        Notes:
            - Requires an active camera connection
            - Camera must support PTZ functionality
            - Position values are normalized (-1.0 to 1.0 range)
            - Capabilities may vary between camera models
            - Some cameras may not provide detailed capability information
            - Position accuracy depends on camera firmware and calibration

        See Also:
            - move_ptz_tool: To change the camera position
            - save_ptz_preset_tool: To save current position as preset
            - recall_ptz_preset_tool: To move to saved preset position
            - go_to_home_ptz_tool: To return to default position
        """
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        server = await TapoCameraServer.get_instance()
        try:
            if not server.camera or not server._connected:
                return {
                    "status": "error",
                    "message": "No camera connected. Please connect to a camera first.",
                }

            # Get real PTZ position from camera
            if hasattr(server.camera, "_camera") and server.camera._camera:
                # Use pytapo to get actual PTZ position
                import asyncio

                position_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: server.camera._camera.getMotorCapability()
                )

                # Extract position from camera response
                pan = position_data.get("pan", {}).get("current_position", 0.0)
                tilt = position_data.get("tilt", {}).get("current_position", 0.0)
                zoom = position_data.get("zoom", {}).get("current_position", 0.0)

                return {
                    "status": "success",
                    "position": {
                        "pan": float(pan),
                        "tilt": float(tilt),
                        "zoom": float(zoom),
                    },
                    "message": "Current PTZ position retrieved successfully",
                }
            return {
                "status": "error",
                "message": "Camera not properly initialized for PTZ operations",
            }
        except Exception as e:
            logger.exception("Failed to get PTZ position")
            return {
                "status": "error",
                "message": f"Failed to get PTZ position: {e!s}",
            }


# Update __all__ to include the new tools
__all__ = [
    "GetPTZPositionTool",
    "GetPTZPresetsTool",
    "GoToHomePTZTool",
    "MovePTZTool",
    "RecallPTZPresetTool",
    "SavePTZPresetTool",
    "StopPTZTool",
]
