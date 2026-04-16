"""USB Microscope API endpoints."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/microscope", tags=["microscope"])


class MagnificationRequest(BaseModel):
    """Request to set magnification."""

    camera_name: str
    magnification: float


class LEDRequest(BaseModel):
    """Request to set LED brightness."""

    camera_name: str
    brightness: int


class CalibrationRequest(BaseModel):
    """Request to calibrate microscope."""

    camera_name: str
    known_distance_pixels: int
    actual_distance_mm: float


class MeasurementRequest(BaseModel):
    """Request to measure distance."""

    camera_name: str
    pixel_distance: int


class StartTimelapseRequest(BaseModel):
    """Request to start a timelapse session."""

    camera_name: str
    session_name: str
    interval_minutes: int = 10  # Every 10 minutes
    duration_hours: int = 24  # For 24 hours (adjust for multi-day)
    auto_focus: bool = True


class CreateVideoRequest(BaseModel):
    """Request to create a timelapse video."""

    session_dir: str
    output_path: str | None = None
    fps: int = 30
    add_timestamp: bool = True


class AnalyzeGrowthRequest(BaseModel):
    """Request to analyze plant growth."""

    session_dir: str


async def _get_microscope_camera(camera_name: str):
    """Get microscope camera instance."""
    from devices_mcp.core.server import DevicesMCPServer

    server = await DevicesMCPServer.get_instance()
    camera = await server.camera_manager.get_camera(camera_name)
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera not found: {camera_name}")

    # Check if it's a microscope camera
    if not hasattr(camera, "set_magnification"):
        raise HTTPException(status_code=400, detail=f"Camera {camera_name} is not a microscope camera")

    return camera


@router.post("/magnification")
async def set_magnification(request: MagnificationRequest):
    """Set microscope magnification."""
    try:
        camera = await _get_microscope_camera(request.camera_name)
        success = await camera.set_magnification(request.magnification)

        if success:
            return {
                "success": True,
                "message": f"Set magnification to {request.magnification}x",
                "magnification": request.magnification,
            }
        raise HTTPException(status_code=500, detail="Failed to set magnification")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to set magnification")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/led")
async def set_led_brightness(request: LEDRequest):
    """Set microscope LED brightness."""
    try:
        camera = await _get_microscope_camera(request.camera_name)
        success = await camera.set_led_brightness(request.brightness)

        if success:
            return {
                "success": True,
                "message": f"Set LED brightness to {request.brightness}%",
                "brightness": request.brightness,
            }
        raise HTTPException(status_code=500, detail="Failed to set LED brightness")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to set LED brightness")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/calibrate")
async def calibrate_microscope(request: CalibrationRequest):
    """Calibrate microscope for measurements."""
    try:
        camera = await _get_microscope_camera(request.camera_name)
        success = await camera.calibrate(request.known_distance_pixels, request.actual_distance_mm)

        if success:
            calibration_factor = request.actual_distance_mm / request.known_distance_pixels
            return {
                "success": True,
                "message": "Microscope calibrated successfully",
                "calibration_factor": calibration_factor,
                "units": "mm/pixel",
            }
        raise HTTPException(status_code=500, detail="Failed to calibrate microscope")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to calibrate microscope")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/measure")
async def measure_distance(request: MeasurementRequest):
    """Convert pixel distance to actual distance."""
    try:
        camera = await _get_microscope_camera(request.camera_name)
        actual_distance = await camera.measure_distance(request.pixel_distance)

        if actual_distance is not None:
            return {
                "success": True,
                "pixel_distance": request.pixel_distance,
                "actual_distance": actual_distance,
                "units": "mm",
            }
        raise HTTPException(status_code=500, detail="Microscope not calibrated")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to measure distance")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/autofocus/{camera_name}")
async def auto_focus(camera_name: str):
    """Perform auto-focus on microscope."""
    try:
        camera = await _get_microscope_camera(camera_name)
        success = await camera.auto_focus()

        if success:
            return {"success": True, "message": "Auto-focus completed successfully"}
        return {"success": False, "message": "Auto-focus not supported or failed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to auto-focus")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/info/{camera_name}")
async def get_microscope_info(camera_name: str):
    """Get detailed microscope information."""
    try:
        camera = await _get_microscope_camera(camera_name)
        info = camera.get_microscope_info()

        return {"success": True, "camera_name": camera_name, "info": info}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get microscope info")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/timelapse/start")
async def start_timelapse(request: StartTimelapseRequest):
    """Start a timelapse photography session for plant growth monitoring."""
    try:
        camera = await _get_microscope_camera(request.camera_name)

        # Check if camera supports timelapse
        if not hasattr(camera, "start_timelapse"):
            raise HTTPException(status_code=400, detail=f"Camera {request.camera_name} does not support timelapse")

        session_info = await camera.start_timelapse(
            interval_minutes=request.interval_minutes,
            duration_hours=request.duration_hours,
            session_name=request.session_name,
            auto_focus=request.auto_focus,
        )

        return {
            "success": True,
            "message": f"Timelapse session '{request.session_name}' started",
            "session_info": session_info,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to start timelapse")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/timelapse/stop/{camera_name}")
async def stop_timelapse(camera_name: str, session_name: str):
    """Stop a running timelapse session."""
    try:
        camera = await _get_microscope_camera(camera_name)

        if not hasattr(camera, "stop_timelapse"):
            raise HTTPException(status_code=400, detail=f"Camera {camera_name} does not support timelapse")

        result = await camera.stop_timelapse(session_name)

        return {
            "success": True,
            "message": f"Timelapse session '{session_name}' stop requested",
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to stop timelapse")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/timelapse/status/{camera_name}")
async def get_timelapse_status(camera_name: str):
    """Get status of timelapse sessions for a camera."""
    try:
        camera = await _get_microscope_camera(camera_name)

        if not hasattr(camera, "get_timelapse_status"):
            raise HTTPException(status_code=400, detail=f"Camera {camera_name} does not support timelapse")

        status = await camera.get_timelapse_status()

        return {"success": True, "camera_name": camera_name, "status": status}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get timelapse status")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/timelapse/video")
async def create_timelapse_video(request: CreateVideoRequest):
    """Create a time-lapse video from captured images."""
    try:
        # We need to get a camera instance to use the method
        # This is a bit hacky, but since the method is on the camera class,
        # we'll get the first microscope camera available
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()
        cameras = await server.camera_manager.get_all_cameras()

        microscope_camera = None
        for camera in cameras.values():
            if hasattr(camera, "create_growth_video"):
                microscope_camera = camera
                break

        if not microscope_camera:
            raise HTTPException(status_code=404, detail="No microscope camera available")

        video_path = await microscope_camera.create_growth_video(
            session_dir=request.session_dir,
            output_path=request.output_path,
            fps=request.fps,
            add_timestamp=request.add_timestamp,
        )

        return {
            "success": True,
            "message": f"Timelapse video created: {video_path}",
            "video_path": video_path,
            "fps": request.fps,
            "timestamp_overlay": request.add_timestamp,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to create timelapse video")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/analyze-growth")
async def analyze_growth(request: AnalyzeGrowthRequest):
    """Analyze plant growth patterns from timelapse images."""
    try:
        # Get first available microscope camera
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()
        cameras = await server.camera_manager.get_all_cameras()

        microscope_camera = None
        for camera in cameras.values():
            if hasattr(camera, "analyze_growth"):
                microscope_camera = camera
                break

        if not microscope_camera:
            raise HTTPException(status_code=404, detail="No microscope camera available")

        analysis = await microscope_camera.analyze_growth(request.session_dir)

        return {
            "success": True,
            "message": f"Growth analysis completed for {request.session_dir}",
            "analysis": analysis,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to analyze growth")
        raise HTTPException(status_code=500, detail=str(e)) from e
