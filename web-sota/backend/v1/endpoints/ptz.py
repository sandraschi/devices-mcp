"""
PTZ (Pan-Tilt-Zoom) control API endpoints.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import conint

from devices_mcp.core.models import PTZDirection, PTZPosition

router = APIRouter()


@router.get("/{camera_id}/position", response_model=PTZPosition)
async def get_ptz_position(camera_id: str):
    """Get the current PTZ position of a camera."""
    # This would typically query your camera manager
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Camera {camera_id} not found or PTZ not supported",
    )


@router.post("/{camera_id}/move")
async def move_ptz(camera_id: str, direction: PTZDirection, speed: conint(ge=1, le=100) = 50):
    """
    Move the PTZ camera in a specific direction.

    Args:
        camera_id: ID of the camera
        direction: Direction to move (up, down, left, right, etc.)
        speed: Movement speed (1-100)
    """
    # This would typically control the camera through your camera manager
    return {
        "status": "success",
        "message": f"Moving camera {camera_id} {direction} at speed {speed}",
    }


@router.post("/{camera_id}/preset/{preset_id}/save")
async def save_ptz_preset(camera_id: str, preset_id: int, name: Optional[str] = None):
    """Save the current PTZ position as a preset."""
    # This would typically save the preset through your camera manager
    return {
        "status": "success",
        "message": f"Saved PTZ preset {preset_id} for camera {camera_id}",
        "preset_id": preset_id,
        "name": name or f"Preset {preset_id}",
    }


@router.post("/{camera_id}/preset/{preset_id}/goto")
async def goto_ptz_preset(camera_id: str, preset_id: int, speed: conint(ge=1, le=100) = 50):
    """Move the PTZ camera to a saved preset position."""
    # This would typically move the camera to the preset through your camera manager
    return {
        "status": "success",
        "message": f"Moving camera {camera_id} to preset {preset_id}",
        "preset_id": preset_id,
        "speed": speed,
    }
