"""Camera naming and labeling API endpoints."""

import json
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/camera-names", tags=["camera-names"])

# In-memory storage for camera names (persisted to file)
_camera_names = {}
_camera_names_file = "data/camera_names.json"


def load_camera_names():
    """Load camera names from file."""
    global _camera_names
    try:
        with open(_camera_names_file, encoding="utf-8") as f:
            _camera_names = json.load(f)
        logger.info(f"Loaded camera names for {len(_camera_names)} cameras")
    except FileNotFoundError:
        _camera_names = {}
    except Exception as e:
        logger.exception(f"Failed to load camera names: {e}")
        _camera_names = {}


def save_camera_names():
    """Save camera names to file."""
    try:
        import os

        os.makedirs("data", exist_ok=True)
        with open(_camera_names_file, "w", encoding="utf-8") as f:
            json.dump(_camera_names, f, indent=2, ensure_ascii=False)
        logger.debug("Saved camera names")
    except Exception as e:
        logger.exception(f"Failed to save camera names: {e}")


# Load on startup
load_camera_names()


class SetCameraNameRequest(BaseModel):
    """Request to set a camera name."""

    camera_id: str
    name: str


class RenameCameraRequest(BaseModel):
    """Request to rename a camera."""

    old_id: str
    new_id: str


@router.get("/")
async def get_camera_names() -> dict:
    """Get all camera names."""
    return {"success": True, "names": _camera_names.copy()}


@router.post("/set")
async def set_camera_name(request: SetCameraNameRequest):
    """Set or update a camera name."""
    try:
        _camera_names[request.camera_id] = request.name.strip()
        save_camera_names()
        return {
            "success": True,
            "message": f"Camera '{request.camera_id}' named '{request.name}'",
            "name": request.name,
        }
    except Exception as e:
        logger.exception("Failed to set camera name")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/rename")
async def rename_camera(request: RenameCameraRequest):
    """Rename a camera ID (for when camera IDs change)."""
    try:
        if request.old_id in _camera_names:
            _camera_names[request.new_id] = _camera_names[request.old_id]
            del _camera_names[request.old_id]
            save_camera_names()
            return {
                "success": True,
                "message": f"Renamed camera from '{request.old_id}' to '{request.new_id}'",
            }
        raise HTTPException(status_code=404, detail=f"Camera '{request.old_id}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to rename camera")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{camera_id}")
async def delete_camera_name(camera_id: str):
    """Delete a camera name."""
    try:
        if camera_id in _camera_names:
            del _camera_names[camera_id]
            save_camera_names()
            return {"success": True, "message": f"Deleted name for camera '{camera_id}'"}
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete camera name")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/display/{camera_id}")
async def get_display_name(camera_id: str) -> dict:
    """Get display name for a camera (custom name or fallback to ID)."""
    custom_name = _camera_names.get(camera_id)
    return {
        "camera_id": camera_id,
        "display_name": custom_name or camera_id,
        "has_custom_name": custom_name is not None,
        "custom_name": custom_name,
    }
