"""
PTZ Management Portmanteau Tool
Consolidates all PTZ-related operations into a single tool with action-based interface.
"""

import asyncio
import logging
import math
import random
from typing import Any, Literal

from fastmcp import FastMCP

_READ_ONLY: dict[str, bool] = {"readonly": True}
_MUTATING: dict[str, bool] = {}
_DESTRUCTIVE: dict[str, bool] = {"destructive": True}

from devices_mcp.tools.ptz.ptz_control_tool import PTZControlTool
from devices_mcp.tools.ptz.ptz_preset_tool import PTZPresetTool

logger = logging.getLogger(__name__)


async def _ptz_prank_nod(tool: PTZControlTool, camera_name: str, duration: float) -> dict[str, Any]:
    """Nod mode - enthusiastic up/down nodding like 'yes yes yes!'."""
    end_time = asyncio.get_event_loop().time() + duration
    cycles = 0
    while asyncio.get_event_loop().time() < end_time:
        # Look up
        await tool.execute(operation="move", camera_id=camera_name, pan=0, tilt=0.8, zoom=0, speed=8)
        await asyncio.sleep(0.2)
        # Look down
        await tool.execute(operation="move", camera_id=camera_name, pan=0, tilt=-0.8, zoom=0, speed=8)
        await asyncio.sleep(0.2)
        cycles += 1
    # Return to center
    await tool.execute(operation="move", camera_id=camera_name, pan=0, tilt=0, zoom=0, speed=5)
    return {"mode": "nod", "cycles": cycles}


async def _ptz_prank_shake(tool: PTZControlTool, camera_name: str, duration: float) -> dict[str, Any]:
    """Shake mode - rapid left/right like 'no no no!'."""
    end_time = asyncio.get_event_loop().time() + duration
    cycles = 0
    while asyncio.get_event_loop().time() < end_time:
        # Look left
        await tool.execute(operation="move", camera_id=camera_name, pan=-0.7, tilt=0, zoom=0, speed=8)
        await asyncio.sleep(0.15)
        # Look right
        await tool.execute(operation="move", camera_id=camera_name, pan=0.7, tilt=0, zoom=0, speed=8)
        await asyncio.sleep(0.15)
        cycles += 1
    # Return to center
    await tool.execute(operation="move", camera_id=camera_name, pan=0, tilt=0, zoom=0, speed=5)
    return {"mode": "shake", "cycles": cycles}


async def _ptz_prank_dizzy(tool: PTZControlTool, camera_name: str, duration: float) -> dict[str, Any]:
    """Dizzy mode - circular motion like camera is drunk."""
    end_time = asyncio.get_event_loop().time() + duration
    cycles = 0
    angle = 0.0
    while asyncio.get_event_loop().time() < end_time:
        # Circular motion using sin/cos
        pan = 0.6 * math.sin(angle)
        tilt = 0.6 * math.cos(angle)
        await tool.execute(operation="move", camera_id=camera_name, pan=pan, tilt=tilt, zoom=0, speed=6)
        angle += 0.5
        if angle >= 2 * math.pi:
            angle = 0
            cycles += 1
        await asyncio.sleep(0.1)
    # Return to center
    await tool.execute(operation="move", camera_id=camera_name, pan=0, tilt=0, zoom=0, speed=5)
    return {"mode": "dizzy", "cycles": cycles}


async def _ptz_prank_chaos(tool: PTZControlTool, camera_name: str, duration: float) -> dict[str, Any]:
    """Chaos mode - random crazy movements."""
    end_time = asyncio.get_event_loop().time() + duration
    moves = 0
    while asyncio.get_event_loop().time() < end_time:
        pan = random.uniform(-1.0, 1.0)
        tilt = random.uniform(-1.0, 1.0)
        zoom = random.uniform(0, 0.5)
        speed = random.randint(5, 8)
        await tool.execute(operation="move", camera_id=camera_name, pan=pan, tilt=tilt, zoom=zoom, speed=speed)
        await asyncio.sleep(random.uniform(0.1, 0.3))
        moves += 1
    # Return to center
    await tool.execute(operation="move", camera_id=camera_name, pan=0, tilt=0, zoom=0, speed=5)
    return {"mode": "chaos", "moves": moves}


PTZ_ACTIONS = {
    "move": "Move PTZ camera",
    "position": "Get PTZ position",
    "stop": "Stop PTZ movement",
    "save_preset": "Save PTZ preset",
    "recall_preset": "Recall PTZ preset",
    "list_presets": "List all PTZ presets",
    "delete_preset": "Delete PTZ preset",
    "home": "Move to home position",
    "prank": "Fun camera movements: nod, shake, dizzy, chaos (max 10 sec)",
}


def register_ptz_management_tool(mcp: FastMCP) -> None:
    """Register the PTZ management portmanteau tool."""

    @mcp.tool(annotations=_MUTATING)
    async def ptz_management(
        action: Literal[
            "move",
            "position",
            "stop",
            "save_preset",
            "recall_preset",
            "list_presets",
            "delete_preset",
            "home",
            "prank",
        ],
        camera_name: str | None = None,
        pan: float | None = None,
        tilt: float | None = None,
        zoom: float | None = None,
        speed: int | None = None,
        preset_name: str | None = None,
        preset_id: int | None = None,
        prank_mode: Literal["nod", "shake", "dizzy", "chaos"] | None = None,
        duration: int = 5,
    ) -> dict[str, Any]:
        """
        Comprehensive PTZ (Pan-Tilt-Zoom) management portmanteau tool.
        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 8+ separate tools (one per operation), this tool consolidates related
        PTZ operations into a single interface. Prevents tool explosion (8+ tools → 1 tool) while maintaining
        full functionality and improving discoverability. Follows FastMCP 3.1+ best practices.
        Args:
            action (Literal, required): The operation to perform. Must be one of: "move", "position", "stop",
                "save_preset", "recall_preset", "list_presets", "delete_preset", "home".
                - "move": Move PTZ camera (requires: camera_name, pan/tilt/zoom, speed)
                - "position": Get current PTZ position (requires: camera_name)
                - "stop": Stop PTZ movement (requires: camera_name)
                - "save_preset": Save current position as preset (requires: camera_name, preset_name)
                - "recall_preset": Move to saved preset (requires: camera_name, preset_name or preset_id)
                - "list_presets": List all saved presets (requires: camera_name)
                - "delete_preset": Delete a preset (requires: camera_name, preset_name or preset_id)
                - "home": Move to home position (requires: camera_name)
                - "prank": Fun camera movement modes (requires: camera_name, prank_mode, optional: duration)
            camera_name (str | None): Camera name/ID. Required for: all operations.
            pan (float | None): Pan value (-1.0 to 1.0, left to right). Required for: move operation. Default: 0.0
            tilt (float | None): Tilt value (-1.0 to 1.0, down to up). Required for: move operation. Default: 0.0
            zoom (float | None): Zoom value (0.0 to 1.0, wide to telephoto). Required for: move operation. Default: 0.0
            speed (int | None): Movement speed (1-8, slow to fast). Required for: move operation. Default: 5
            preset_name (str | None): Preset name. Required for: save_preset operation.
                Optional for: recall_preset, delete_preset operations.
            preset_id (int | None): Preset ID. Required for: recall_preset, delete_preset operations when
                preset_name not provided.
            prank_mode (Literal["nod", "shake", "dizzy", "chaos"] | None): Prank mode for fun camera movements:
                - "nod": Enthusiastic up/down nodding like 'yes yes yes!'
                - "shake": Rapid left/right like 'no no no!'
                - "dizzy": Circular motion like camera is drunk
                - "chaos": Random crazy movements
            duration (int): Duration in seconds for prank mode (1-10, default 5). Max 10 sec for safety.
        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data
                - error (str | None): Error message if success is False
        Examples:
            # Move PTZ camera
            result = await ptz_management(action="move", camera_name="Front Door", pan=0.5, tilt=0.3, zoom=0.7, speed=5)
            # Get current position
            result = await ptz_management(action="position", camera_name="Front Door")
            # Save preset
            result = await ptz_management(action="save_preset", camera_name="Front Door", preset_name="Front View")
            # Recall preset
            result = await ptz_management(action="recall_preset", camera_name="Front Door", preset_name="Front View")
        """
        try:
            if action not in PTZ_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(PTZ_ACTIONS.keys())}",
                }
            logger.info(f"Executing PTZ management action: {action}")
            if action in ["move", "position", "stop"]:
                if not camera_name:
                    return {
                        "success": False,
                        "message": "camera_name is required for this action",
                        "error": "camera_name is required for this action",
                    }
                tool = PTZControlTool()
                operation_map = {"move": "move", "position": "position", "stop": "stop"}
                # Only pass speed for move operation
                execute_params = {
                    "operation": operation_map[action],
                    "camera_id": camera_name,
                }
                if action == "move":
                    execute_params.update(
                        {
                            "pan": pan or 0.0,
                            "tilt": tilt or 0.0,
                            "zoom": zoom or 0.0,
                            "speed": speed or 5,
                        }
                    )
                result = await tool.execute(**execute_params)
                return {"success": True, "action": action, "data": result}
            if action in ["save_preset", "recall_preset", "list_presets", "delete_preset", "home"]:
                if not camera_name:
                    return {
                        "success": False,
                        "message": "camera_name is required for this action",
                        "error": "camera_name is required for this action",
                    }
                if action == "save_preset":
                    if not preset_name:
                        return {
                            "success": False,
                            "message": "preset_name is required for save_preset action",
                            "error": "preset_name is required for save_preset action",
                        }
                elif action in ["recall_preset", "delete_preset"]:
                    if not preset_name and not preset_id:
                        return {
                            "success": False,
                            "message": "preset_name or preset_id is required for this action",
                            "error": "preset_name or preset_id is required for this action",
                        }
                tool = PTZPresetTool()
                operation_map = {
                    "save_preset": "save",
                    "recall_preset": "recall",
                    "list_presets": "list",
                    "delete_preset": "delete",
                    "home": "home",
                }
                result = await tool.execute(
                    operation=operation_map[action],
                    camera_id=camera_name,
                    preset_name=preset_name,
                    preset_id=preset_id,
                )
                return {"success": True, "action": action, "data": result}
            if action == "prank":
                if not camera_name:
                    return {
                        "success": False,
                        "message": "camera_name is required for prank action",
                        "error": "camera_name is required for prank action",
                    }
                if not prank_mode:
                    return {
                        "success": False,
                        "message": "prank_mode is required (nod, shake, dizzy, chaos)",
                        "error": "prank_mode is required (nod, shake, dizzy, chaos)",
                    }
                # Cap duration at 10 seconds for safety
                safe_duration = min(max(1, duration), 10)
                logger.info(f"Starting PTZ prank mode '{prank_mode}' on {camera_name} for {safe_duration} seconds")
                tool = PTZControlTool()
                if prank_mode == "nod":
                    result = await _ptz_prank_nod(tool, camera_name, safe_duration)
                elif prank_mode == "shake":
                    result = await _ptz_prank_shake(tool, camera_name, safe_duration)
                elif prank_mode == "dizzy":
                    result = await _ptz_prank_dizzy(tool, camera_name, safe_duration)
                elif prank_mode == "chaos":
                    result = await _ptz_prank_chaos(tool, camera_name, safe_duration)
                else:
                    return {
                        "success": False,
                        "message": f"Unknown prank mode: {prank_mode}",
                        "error": f"Unknown prank mode: {prank_mode}",
                    }
                return {
                    "success": True,
                    "action": action,
                    "data": {"camera": camera_name, "duration": safe_duration, **result},
                }
            return {
                "success": False,
                "message": f"Action '{action}' not implemented",
                "error": f"Action '{action}' not implemented",
            }
        except Exception as e:
            logger.exception("Error in PTZ management action '{action}':")
            return {
                "success": False,
                "message": f"Failed to execute action '{action}': {e!s}",
                "error": f"Failed to execute action '{action}': {e!s}",
            }
