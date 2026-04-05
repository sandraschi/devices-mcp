"""Custom PTZ Preset API endpoints."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devices_mcp.tools.ptz.custom_preset_manager import get_custom_preset_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ptz/presets/custom", tags=["ptz-presets"])


class SavePresetRequest(BaseModel):
    """Request to save a preset."""

    camera_name: str
    preset_name: str
    description: str = ""


class RenamePresetRequest(BaseModel):
    """Request to rename a preset."""

    camera_name: str
    old_name: str
    new_name: str


class DeletePresetRequest(BaseModel):
    """Request to delete a preset."""

    camera_name: str
    preset_name: str


class GotoPresetRequest(BaseModel):
    """Request to go to a preset position."""

    camera_name: str
    preset_name: str


@router.get("/{camera_name}")
async def get_camera_presets(camera_name: str) -> dict:
    """Get all custom presets for a camera."""
    try:
        manager = get_custom_preset_manager()
        presets = manager.get_camera_presets(camera_name)
        return {
            "success": True,
            "presets": [
                {
                    "name": p.name,
                    "camera_name": p.camera_name,
                    "pan": p.pan,
                    "tilt": p.tilt,
                    "zoom": p.zoom,
                    "description": p.description,
                }
                for p in presets
            ],
        }
    except Exception as e:
        logger.exception("Failed to get camera presets")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/save")
async def save_current_position(request: SavePresetRequest):
    """Save current PTZ position as a preset."""
    try:
        # Get camera to read current position
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()
        camera = await server.camera_manager.get_camera(request.camera_name)
        if not camera:
            raise HTTPException(status_code=404, detail=f"Camera not found: {request.camera_name}")

        # Get current position
        current_pos = await camera.ptz_get_current_position()
        if not current_pos:
            raise HTTPException(status_code=500, detail="Could not get current PTZ position")

        # Save preset
        manager = get_custom_preset_manager()
        success = manager.save_preset(
            camera_name=request.camera_name,
            preset_name=request.preset_name,
            pan=current_pos.get("pan", 0),
            tilt=current_pos.get("tilt", 0),
            zoom=current_pos.get("zoom", 0),
            description=request.description,
        )

        if success:
            return {
                "success": True,
                "message": f"Saved preset '{request.preset_name}'",
                "position": current_pos,
            }
        raise HTTPException(status_code=500, detail="Failed to save preset")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to save preset")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/goto")
async def goto_preset(request: GotoPresetRequest):
    """Move camera to a saved preset position."""
    try:
        # Get preset
        manager = get_custom_preset_manager()
        preset = manager.get_preset(request.camera_name, request.preset_name)
        if not preset:
            raise HTTPException(status_code=404, detail=f"Preset not found: {request.preset_name}")

        # Get camera
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()
        camera = await server.camera_manager.get_camera(request.camera_name)
        if not camera:
            raise HTTPException(status_code=404, detail=f"Camera not found: {request.camera_name}")

        # Move to position
        await camera.ptz_goto_position(preset.pan, preset.tilt, preset.zoom)

        return {
            "success": True,
            "message": f"Moving to preset '{request.preset_name}'",
            "position": {"pan": preset.pan, "tilt": preset.tilt, "zoom": preset.zoom},
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to go to preset")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/rename")
async def rename_preset(request: RenamePresetRequest):
    """Rename a preset."""
    try:
        manager = get_custom_preset_manager()
        success = manager.rename_preset(request.camera_name, request.old_name, request.new_name)

        if success:
            return {
                "success": True,
                "message": f"Renamed preset '{request.old_name}' to '{request.new_name}'",
            }
        raise HTTPException(status_code=404, detail=f"Preset not found: {request.old_name}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to rename preset")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/delete")
async def delete_preset(request: DeletePresetRequest):
    """Delete a preset."""
    try:
        manager = get_custom_preset_manager()
        success = manager.delete_preset(request.camera_name, request.preset_name)

        if success:
            return {"success": True, "message": f"Deleted preset '{request.preset_name}'"}
        raise HTTPException(status_code=404, detail=f"Preset not found: {request.preset_name}")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete preset")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/all")
async def get_all_presets():
    """Get all presets for all cameras."""
    try:
        manager = get_custom_preset_manager()
        all_presets = manager.get_all_presets()

        result = {}
        for camera_name, presets in all_presets.items():
            result[camera_name] = [
                {
                    "name": p.name,
                    "camera_name": p.camera_name,
                    "pan": p.pan,
                    "tilt": p.tilt,
                    "zoom": p.zoom,
                    "description": p.description,
                }
                for p in presets
            ]

        return {"success": True, "presets": result}

    except Exception as e:
        logger.exception("Failed to get all presets")
        raise HTTPException(status_code=500, detail=str(e)) from e
