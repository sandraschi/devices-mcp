"""
Camera-related API endpoints.
"""

from typing import List

from fastapi import APIRouter, HTTPException, status

from devices_mcp.core.models import CameraInfo, CameraStatus

router = APIRouter()


@router.get("/", response_model=List[CameraInfo])
async def list_cameras():
    """List all configured cameras."""
    # This would typically query your camera manager
    return []


@router.get("/{camera_id}", response_model=CameraInfo)
async def get_camera(camera_id: str):
    """Get details for a specific camera."""
    # This would typically query your camera manager
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Camera {camera_id} not found"
    )


@router.get("/{camera_id}/status", response_model=CameraStatus)
async def get_camera_status(camera_id: str):
    """Get the status of a specific camera."""
    # This would typically query your camera manager
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail=f"Camera {camera_id} not found"
    )


@router.post("/{camera_id}/refresh")
async def refresh_camera(camera_id: str):
    """Force a refresh of the camera's connection and status."""
    # This would typically tell your camera manager to refresh the connection
    return {"status": "success", "message": f"Refresh initiated for camera {camera_id}"}
