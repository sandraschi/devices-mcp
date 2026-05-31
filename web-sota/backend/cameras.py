"""Camera routes - Connects to real MCP camera tools."""

import logging

# Add src to Python path for MCP imports
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/api/cameras")
async def get_cameras() -> dict[str, Any]:
    """Get all cameras using MCP camera tools."""
    try:
        # Import MCP camera tools
        from devices_mcp.tools.camera.camera_tools import ListCamerasTool

        # Execute the MCP tool to get real camera data
        tool = ListCamerasTool()
        result = await tool.execute()

        if not result.get("success", False):
            logger.error(f"Failed to get cameras: {result.get('error', 'Unknown error')}")
            raise HTTPException(status_code=500, detail="Failed to retrieve camera data")

        cameras = result.get("cameras", [])
        logger.info(f"Retrieved {len(cameras)} cameras from MCP tools")

        return {"cameras": cameras, "total": result.get("total", len(cameras)), "success": True}

    except Exception as e:
        logger.exception(f"Error in get_cameras: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/cameras/{camera_name}/snapshot")
async def get_camera_snapshot(camera_name: str) -> JSONResponse:
    """Get camera snapshot using MCP tools."""
    try:
        # Import MCP camera tools
        from devices_mcp.tools.camera.camera_info_tool import GetCameraInfoTool

        # Get camera info first to verify camera exists
        info_tool = GetCameraInfoTool()
        info_result = await info_tool.execute(camera_name=camera_name)

        if not info_result.get("success", False):
            raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")

        # For now, return a placeholder snapshot URL
        # In a real implementation, this would generate an actual snapshot
        camera = info_result.get("camera", {})

        # Return snapshot URL or error based on camera status
        if camera.get("status") == "online":
            return JSONResponse(
                {
                    "snapshot_url": f"/api/cameras/{camera_name}/snapshot.jpg",
                    "timestamp": "2025-02-13T00:00:00Z",
                    "status": "success",
                }
            )
        return JSONResponse({"error": "Camera is offline", "status": "offline"})

    except Exception as e:
        logger.exception(f"Error getting snapshot for {camera_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/cameras/{camera_name}/stream")
async def get_camera_stream(camera_name: str) -> JSONResponse:
    """Get camera stream URL using MCP tools."""
    try:
        # Import MCP camera tools
        from devices_mcp.tools.camera.camera_info_tool import GetCameraInfoTool

        # Get camera info first to verify camera exists
        info_tool = GetCameraInfoTool()
        info_result = await info_tool.execute(camera_name=camera_name)

        if not info_result.get("success", False):
            raise HTTPException(status_code=404, detail=f"Camera '{camera_name}' not found")

        camera = info_result.get("camera", {})

        # Return stream URL based on camera type and status
        if camera.get("status") == "online":
            if camera.get("type") == "ring":
                stream_url = f"/api/ring/stream/{camera_name}"
            else:
                stream_url = f"/api/cameras/{camera_name}/stream.m3u8"

            return JSONResponse(
                {
                    "stream_url": stream_url,
                    "format": "hls" if camera.get("type") != "ring" else "rtmp",
                    "status": "success",
                }
            )
        return JSONResponse({"error": "Camera is offline", "status": "offline"})

    except Exception as e:
        logger.exception(f"Error getting stream for {camera_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/ring/snapshot/{camera_id}")
async def get_ring_snapshot(camera_id: str) -> JSONResponse:
    """Get Ring doorbell snapshot."""
    try:
        # Import Ring camera tools
        from devices_mcp.ring.tools.camera_tools import RingCameraTools

        RingCameraTools()
        # This would implement actual Ring snapshot functionality
        # For now, return placeholder

        return JSONResponse(
            {
                "snapshot_url": f"/api/ring/snapshots/{camera_id}.jpg",
                "timestamp": "2025-02-13T00:00:00Z",
                "status": "success",
            }
        )

    except Exception as e:
        logger.exception(f"Error getting Ring snapshot for {camera_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/ring/stream/{camera_id}")
async def get_ring_stream(camera_id: str) -> JSONResponse:
    """Get Ring doorbell stream."""
    try:
        # Import Ring camera tools
        from devices_mcp.ring.tools.camera_tools import RingCameraTools

        RingCameraTools()
        # This would implement actual Ring stream functionality
        # For now, return placeholder

        return JSONResponse(
            {
                "stream_url": f"/api/ring/streams/{camera_id}.m3u8",
                "format": "hls",
                "status": "success",
            }
        )

    except Exception as e:
        logger.exception(f"Error getting Ring stream for {camera_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/cameras/{camera_name}/ptz/move")
async def move_camera_ptz(camera_name: str, direction: str, amount: float = 1.0) -> JSONResponse:
    """Move camera using PTZ controls via MCP tools."""
    try:
        # Import MCP PTZ tools
        from devices_mcp.tools.camera.camera_management_tool import CameraManagementTool

        tool = CameraManagementTool()
        result = await tool.execute(camera_name=camera_name, operation="move", direction=direction, amount=amount)

        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "PTZ operation failed"))

        camera_type = result.get("type", "unknown")
        if isinstance(camera_type, str):
            type_str = camera_type
        else:
            # Try to get the value if it's an enum
            type_str = getattr(camera_type, "value", str(camera_type))

        return JSONResponse(
            {
                "success": True,
                "operation": "move",
                "direction": direction,
                "amount": amount,
                "result": result,
                "camera": {
                    "name": camera_name,
                    "type": type_str,
                    "status": result.get("status", "unknown"),
                    "model": result.get("model", "unknown"),
                    "firmware": result.get("firmware", "unknown"),
                    "ip_address": result.get("ip_address", "unknown"),
                    "mac_address": result.get("mac_address", "unknown"),
                    "rtsp_stream_url": result.get("rtsp_stream_url", "N/A"),
                    "hls_stream_url": result.get("hls_stream_url", "N/A"),
                    "capabilities": result.get("capabilities", []),
                    "last_seen": result.get("last_seen", "unknown"),
                    "recording": result.get("recording", False),
                    "motion_detection": result.get("motion_detection", False),
                    "night_vision": result.get("night_vision", False),
                    "audio": result.get("audio", False),
                    "privacy": result.get("privacy", False),
                },
            }
        )

    except Exception as e:
        logger.exception(f"Error moving camera {camera_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/cameras/{camera_name}/audio/toggle")
async def toggle_camera_audio(camera_name: str) -> JSONResponse:
    """Toggle camera audio via MCP tools."""
    try:
        # Import MCP audio tools
        from devices_mcp.tools.camera.camera_management_tool import CameraManagementTool

        tool = CameraManagementTool()
        result = await tool.execute(camera_name=camera_name, operation="toggle_audio")

        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "Audio toggle failed"))

        return JSONResponse({"success": True, "operation": "toggle_audio", "result": result})

    except Exception as e:
        logger.exception(f"Error toggling audio for {camera_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
