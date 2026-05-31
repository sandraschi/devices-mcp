"""Otoscope camera API — TBD: verify OtoscopeCamera bindings and workflows before clinical use."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devices_mcp.camera.otoscope import OtoscopeCamera
from devices_mcp.core.server import DevicesMCPServer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/otoscope", tags=["otoscope", "TBD"])


class OtoscopeControlRequest(BaseModel):
    """Base request model for otoscope controls."""

    camera_name: str


class SetLightIntensityRequest(OtoscopeControlRequest):
    """Request model for setting light intensity."""

    intensity: int


class SetFocusModeRequest(OtoscopeControlRequest):
    """Request model for setting focus mode."""

    mode: str


class SetSpecimenTypeRequest(OtoscopeControlRequest):
    """Request model for setting specimen type."""

    specimen_type: str


class SetMagnificationRequest(OtoscopeControlRequest):
    """Request model for setting magnification."""

    magnification: float


class CalibrateRequest(OtoscopeControlRequest):
    """Request model for calibration."""

    reference_size_mm: float
    pixels: float


class MeasureRequest(OtoscopeControlRequest):
    """Request model for measurement."""

    pixels: float


class CaptureMedicalImageRequest(OtoscopeControlRequest):
    """Request model for capturing medical images."""

    filename: str
    metadata: dict | None = None


class StartRecordingRequest(OtoscopeControlRequest):
    """Request model for starting medical recording."""

    filename: str
    duration_seconds: int | None = None


class ApplyPresetRequest(OtoscopeControlRequest):
    """Request model for applying medical presets."""

    preset_name: str


async def _get_otoscope_camera(camera_name: str) -> OtoscopeCamera:
    """Helper to get an otoscope camera instance."""
    server = await DevicesMCPServer.get_instance()
    camera = await server.camera_manager.get_camera(camera_name)
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera not found: {camera_name}")
    if not isinstance(camera, OtoscopeCamera):
        raise HTTPException(status_code=400, detail=f"Camera '{camera_name}' is not an otoscope camera.")
    return camera


@router.get("/info/{camera_name}", response_model=dict)
async def get_otoscope_info(camera_name: str):
    """Get detailed information about an otoscope camera."""
    camera = await _get_otoscope_camera(camera_name)
    return await camera.get_status()


@router.post("/light_intensity")
async def set_light_intensity(request: SetLightIntensityRequest):
    """Set the LED light intensity of the otoscope (0-100)."""
    camera = await _get_otoscope_camera(request.camera_name)
    try:
        await camera.set_light_intensity(request.intensity)
        return {"success": True, "message": f"Light intensity set to {request.intensity}%"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to set light intensity")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/focus_mode")
async def set_focus_mode(request: SetFocusModeRequest):
    """Set the focus mode of the otoscope (auto, manual, fixed)."""
    camera = await _get_otoscope_camera(request.camera_name)
    try:
        await camera.set_focus_mode(request.mode)
        return {"success": True, "message": f"Focus mode set to '{request.mode}'"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to set focus mode")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/specimen_type")
async def set_specimen_type(request: SetSpecimenTypeRequest):
    """Set the specimen type for examination (ear, throat, nose, etc.)."""
    camera = await _get_otoscope_camera(request.camera_name)
    try:
        await camera.set_specimen_type(request.specimen_type)
        return {"success": True, "message": f"Specimen type set to '{request.specimen_type}'"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to set specimen type")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/magnification")
async def set_magnification(request: SetMagnificationRequest):
    """Set the digital magnification level of the otoscope."""
    camera = await _get_otoscope_camera(request.camera_name)
    try:
        await camera.set_magnification(request.magnification)
        return {"success": True, "message": f"Magnification set to {request.magnification}x"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to set magnification")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/calibrate")
async def calibrate_otoscope(request: CalibrateRequest):
    """Calibrate the otoscope for accurate measurements."""
    camera = await _get_otoscope_camera(request.camera_name)
    try:
        await camera.calibrate(request.reference_size_mm, request.pixels)
        return {"success": True, "message": "Otoscope calibrated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to calibrate otoscope")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/measure_distance")
async def measure_distance(request: MeasureRequest):
    """Convert a distance in pixels to real-world millimeters."""
    camera = await _get_otoscope_camera(request.camera_name)
    try:
        distance_mm = await camera.measure_distance(request.pixels)
        return {
            "success": True,
            "distance_mm": distance_mm,
            "message": f"{request.pixels} pixels = {distance_mm:.4f} mm",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to measure distance")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/measure_area")
async def measure_area(request: MeasureRequest):
    """Convert an area in square pixels to real-world square millimeters."""
    camera = await _get_otoscope_camera(request.camera_name)
    try:
        area_sq_mm = await camera.measure_area(request.pixels)
        return {
            "success": True,
            "area_sq_mm": area_sq_mm,
            "message": f"{request.pixels} sq pixels = {area_sq_mm:.4f} sq mm",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to measure area")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/capture_medical")
async def capture_medical_image(request: CaptureMedicalImageRequest):
    """Capture a medical image with embedded metadata."""
    camera = await _get_otoscope_camera(request.camera_name)
    try:
        filename = await camera.capture_medical_image(request.filename, request.metadata)
        return {"success": True, "message": f"Medical image captured: {filename}"}
    except Exception as e:
        logger.exception("Failed to capture medical image")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/start_recording")
async def start_medical_recording(request: StartRecordingRequest):
    """Start recording a medical examination video."""
    camera = await _get_otoscope_camera(request.camera_name)
    try:
        recording_id = await camera.start_medical_recording(request.filename, request.duration_seconds)
        return {"success": True, "message": f"Medical recording started: {recording_id}"}
    except Exception as e:
        logger.exception("Failed to start medical recording")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stop_recording")
async def stop_medical_recording(camera_name: str):
    """Stop the current medical recording."""
    camera = await _get_otoscope_camera(camera_name)
    try:
        await camera.stop_medical_recording()
        return {"success": True, "message": "Medical recording stopped"}
    except Exception as e:
        logger.exception("Failed to stop medical recording")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/presets/{camera_name}")
async def get_medical_presets(camera_name: str):
    """Get available medical examination presets."""
    camera = await _get_otoscope_camera(camera_name)
    try:
        presets = await camera.get_medical_presets()
        return {"success": True, "presets": presets}
    except Exception as e:
        logger.exception("Failed to get medical presets")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/apply_preset")
async def apply_medical_preset(request: ApplyPresetRequest):
    """Apply a medical examination preset."""
    camera = await _get_otoscope_camera(request.camera_name)
    try:
        await camera.apply_medical_preset(request.preset_name)
        return {"success": True, "message": f"Applied medical preset '{request.preset_name}'"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Failed to apply medical preset")
        raise HTTPException(status_code=500, detail=str(e)) from e
