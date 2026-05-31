"""
REST-style PTZ routes under /api/cameras/{camera_id}/ptz.

All operations resolve the real camera via DevicesMCPServer and call ONVIF PTZ
methods (same as /api/ptz/*). No mock camera clients.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from devices_mcp.tools.ptz.ptz_models import PTZMoveDirection, PTZPosition, PTZSpeed

from .ptz import get_camera_for_ptz

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cameras/{camera_id}/ptz", tags=["PTZ Control"])


def _speed_factor(speed: PTZSpeed) -> float:
    m = {PTZSpeed.SLOW: 0.35, PTZSpeed.MEDIUM: 0.55, PTZSpeed.FAST: 0.85}
    return m.get(speed, 0.55)


def _direction_to_vectors(direction: PTZMoveDirection, speed: PTZSpeed) -> tuple[float, float, float]:
    """Map directional move to pan/tilt/zoom for continuous_move."""
    s = _speed_factor(speed)
    if direction == PTZMoveDirection.STOP:
        return 0.0, 0.0, 0.0
    if direction == PTZMoveDirection.UP:
        return 0.0, s, 0.0
    if direction == PTZMoveDirection.DOWN:
        return 0.0, -s, 0.0
    if direction == PTZMoveDirection.LEFT:
        return -s, 0.0, 0.0
    if direction == PTZMoveDirection.RIGHT:
        return s, 0.0, 0.0
    if direction == PTZMoveDirection.UP_LEFT:
        return -s * 0.75, s * 0.75, 0.0
    if direction == PTZMoveDirection.UP_RIGHT:
        return s * 0.75, s * 0.75, 0.0
    if direction == PTZMoveDirection.DOWN_LEFT:
        return -s * 0.75, -s * 0.75, 0.0
    if direction == PTZMoveDirection.DOWN_RIGHT:
        return s * 0.75, -s * 0.75, 0.0
    return 0.0, 0.0, 0.0


class PTZMoveRequest(BaseModel):
    """Request model for PTZ movement."""

    direction: PTZMoveDirection
    speed: PTZSpeed = PTZSpeed.MEDIUM
    duration_ms: int = Field(1000, ge=100, le=10000, description="Ignored; use ONVIF continuous move")


class PTZZoomRequest(BaseModel):
    """Request model for PTZ zoom."""

    direction: str = Field(..., pattern="^(in|out)$")
    speed: PTZSpeed = PTZSpeed.MEDIUM


class PTZPresetCreate(BaseModel):
    """Request model for creating a PTZ preset (not supported on most Tapo ONVIF stacks)."""

    name: str
    description: str | None = None
    position: PTZPosition | None = None


class PTZPresetUpdate(BaseModel):
    """Request model for updating a PTZ preset (not supported on most Tapo ONVIF stacks)."""

    name: str | None = None
    description: str | None = None
    position: PTZPosition | None = None


@router.post("/move", status_code=status.HTTP_202_ACCEPTED)
async def move_ptz(camera_id: str, move_request: PTZMoveRequest):
    """Move camera using ONVIF continuous move (same backend as POST /api/ptz/move)."""
    camera = await get_camera_for_ptz(camera_id)
    if not hasattr(camera, "ptz_move"):
        raise HTTPException(status_code=400, detail="Camera does not support PTZ controls")

    # Diagonal: reduce vectors so combined speed is similar to cardinal
    if move_request.direction == PTZMoveDirection.STOP:
        if hasattr(camera, "ptz_stop"):
            await camera.ptz_stop()
            return {"status": "success", "message": f"PTZ stop for {camera_id}"}
        raise HTTPException(status_code=400, detail="Camera does not support PTZ stop")

    pan, tilt, zoom = _direction_to_vectors(move_request.direction, move_request.speed)
    min_threshold = 0.05
    if abs(pan) < min_threshold and abs(tilt) < min_threshold and abs(zoom) < min_threshold:
        try:
            await camera.ptz_stop()
            return {"status": "success", "message": "PTZ stopped (zero vector)"}
        except Exception:
            pass

    try:
        await camera.ptz_move(pan=pan, tilt=tilt, zoom=zoom)
        return {
            "status": "success",
            "message": f"Moving {camera_id} {move_request.direction}",
            "pan": pan,
            "tilt": tilt,
            "zoom": zoom,
        }
    except Exception as e:
        logger.exception("PTZ move failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/zoom", status_code=status.HTTP_202_ACCEPTED)
async def zoom_ptz(camera_id: str, zoom_request: PTZZoomRequest):
    """Zoom in/out via ONVIF."""
    camera = await get_camera_for_ptz(camera_id)
    if not hasattr(camera, "ptz_move"):
        raise HTTPException(status_code=400, detail="Camera does not support PTZ controls")

    z = _speed_factor(zoom_request.speed) * 0.55
    if zoom_request.direction == "out":
        z = -z

    try:
        await camera.ptz_move(pan=0.0, tilt=0.0, zoom=z)
        return {"status": "success", "message": f"Zoom {zoom_request.direction} for {camera_id}"}
    except Exception as e:
        logger.exception("PTZ zoom failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stop", status_code=status.HTTP_202_ACCEPTED)
async def stop_ptz(camera_id: str):
    """Stop all PTZ movement."""
    camera = await get_camera_for_ptz(camera_id)
    if not hasattr(camera, "ptz_stop"):
        raise HTTPException(status_code=400, detail="Camera does not support PTZ stop")
    try:
        await camera.ptz_stop()
        return {"status": "success", "message": "PTZ movement stopped"}
    except Exception as e:
        logger.exception("PTZ stop failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/presets")
async def list_presets(camera_id: str) -> dict[str, Any]:
    """List PTZ presets from the camera (ONVIF)."""
    camera = await get_camera_for_ptz(camera_id)
    if not hasattr(camera, "ptz_get_presets"):
        raise HTTPException(status_code=400, detail="Camera does not list PTZ presets")
    try:
        presets = await camera.ptz_get_presets()
        # Normalize to JSON-serializable
        if isinstance(presets, list):
            out = []
            for p in presets:
                if isinstance(p, dict):
                    out.append(p)
                else:
                    out.append(getattr(p, "__dict__", str(p)))
        else:
            out = [presets]
        return {"camera_id": camera_id, "presets": out, "count": len(out)}
    except Exception as e:
        logger.exception("list presets failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/presets", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_preset(_camera_id: str, _preset_data: PTZPresetCreate):
    """Creating presets via the API is not implemented for Tapo/ONVIF in this stack."""
    raise HTTPException(
        status_code=501,
        detail="Preset create is not supported on this integration; use the Tapo app or ONVIF SetPreset from a vendor tool.",
    )


@router.get("/presets/{preset_ref}")
async def get_preset(camera_id: str, preset_ref: str):
    """Return preset if present in list (best-effort match)."""
    camera = await get_camera_for_ptz(camera_id)
    if not hasattr(camera, "ptz_get_presets"):
        raise HTTPException(status_code=400, detail="Camera does not list PTZ presets")
    try:
        presets = await camera.ptz_get_presets()
        plist: list[Any] = presets if isinstance(presets, list) else ([presets] if presets is not None else [])
        for p in plist:
            if isinstance(p, dict):
                token = str(p.get("token", p.get("Token", "")))
                if token == preset_ref or str(p.get("name", "")) == preset_ref:
                    return {"camera_id": camera_id, "preset": p}
            elif str(p) == preset_ref:
                return {"camera_id": camera_id, "preset": p}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    raise HTTPException(status_code=404, detail=f"Preset {preset_ref} not found")


@router.put("/presets/{preset_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def update_preset(_camera_id: str, _preset_id: int, _preset_data: PTZPresetUpdate):
    raise HTTPException(status_code=501, detail="Preset update not supported on this integration.")


@router.delete("/presets/{preset_id}", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def delete_preset(_camera_id: str, _preset_id: int):
    raise HTTPException(status_code=501, detail="Preset delete not supported on this integration.")


@router.post("/presets/{preset_ref}/recall", status_code=status.HTTP_202_ACCEPTED)
async def recall_preset(camera_id: str, preset_ref: str):
    """Go to preset by token or name (passed as path segment)."""
    camera = await get_camera_for_ptz(camera_id)
    if not hasattr(camera, "ptz_go_to_preset"):
        raise HTTPException(status_code=400, detail="Camera does not support preset recall")
    try:
        await camera.ptz_go_to_preset(preset_ref)
        return {"status": "success", "message": f"Recalling preset {preset_ref} on {camera_id}"}
    except Exception as e:
        logger.exception("recall preset failed")
        raise HTTPException(status_code=500, detail=str(e)) from e
