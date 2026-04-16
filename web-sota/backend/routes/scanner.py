"""Scanner-specific API endpoints for document scanning."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from devices_mcp.camera.scanner import ScannerCamera
from devices_mcp.core.server import DevicesMCPServer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scanner", tags=["scanner"])


class ScannerControlRequest(BaseModel):
    """Base request model for scanner controls."""

    camera_name: str


class ScanRequest(ScannerControlRequest):
    """Request model for scanning documents."""

    filename: str | None = None
    format: str = "png"


class SetScanSettingsRequest(ScannerControlRequest):
    """Request model for setting scan settings."""

    dpi: int | None = None
    color_mode: str | None = None
    brightness: int | None = None
    contrast: int | None = None


class OCRRequest(ScannerControlRequest):
    """Request model for OCR scanning."""

    filename: str | None = None
    language: str = "eng"


class BatchScanRequest(ScannerControlRequest):
    """Request model for batch scanning."""

    count: int = 5
    prefix: str = "batch"


class DeleteScanRequest(ScannerControlRequest):
    """Request model for deleting scans."""

    filename: str


async def _get_scanner_camera(camera_name: str) -> ScannerCamera:
    """Helper to get a scanner camera instance."""
    server = await DevicesMCPServer.get_instance()
    camera = await server.camera_manager.get_camera(camera_name)
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera not found: {camera_name}")
    if not isinstance(camera, ScannerCamera):
        raise HTTPException(status_code=400, detail=f"Camera '{camera_name}' is not a scanner camera.")
    return camera


@router.get("/info/{camera_name}", response_model=dict)
async def get_scanner_info(camera_name: str):
    """Get detailed information about a scanner camera."""
    camera = await _get_scanner_camera(camera_name)
    return await camera.get_status()


@router.post("/scan")
async def scan_document(request: ScanRequest):
    """Scan a document and save it."""
    camera = await _get_scanner_camera(request.camera_name)
    try:
        scan_path = await camera.scan_document(request.filename, request.format)
        return {"success": True, "message": "Document scanned successfully", "scan_path": scan_path}
    except Exception as e:
        logger.exception("Failed to scan document")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preview/{camera_name}")
async def get_scan_preview(camera_name: str):
    """Get a preview of the scanner."""
    camera = await _get_scanner_camera(camera_name)
    try:
        preview_bytes = await camera.preview_scan()
        import io

        from fastapi.responses import StreamingResponse

        return StreamingResponse(io.BytesIO(preview_bytes), media_type="image/jpeg")
    except Exception as e:
        logger.exception("Failed to get scan preview")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/settings")
async def set_scan_settings(request: SetScanSettingsRequest):
    """Set scanner settings (DPI, color mode, brightness, contrast)."""
    camera = await _get_scanner_camera(request.camera_name)
    try:
        await camera.set_scan_settings(
            dpi=request.dpi,
            color_mode=request.color_mode,
            brightness=request.brightness,
            contrast=request.contrast,
        )
        return {"success": True, "message": "Scanner settings updated"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to set scanner settings")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{camera_name}", response_model=list[dict])
async def get_scan_history(camera_name: str):
    """Get history of recent scans."""
    camera = await _get_scanner_camera(camera_name)
    try:
        history = await camera.get_scan_history()
        return history
    except Exception as e:
        logger.exception("Failed to get scan history")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ocr")
async def scan_with_ocr(request: OCRRequest):
    """Scan document and perform OCR to extract text."""
    camera = await _get_scanner_camera(request.camera_name)
    try:
        ocr_result = await camera.scan_to_ocr(request.filename, request.language)
        return {"success": True, "message": "OCR scan completed", "result": ocr_result}
    except Exception as e:
        logger.exception("Failed to perform OCR scan")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_scan(request: BatchScanRequest):
    """Perform batch scanning of multiple pages."""
    camera = await _get_scanner_camera(request.camera_name)
    try:
        scanned_files = await camera.batch_scan(request.count, request.prefix)
        return {
            "success": True,
            "message": f"Batch scan completed - {len(scanned_files)} pages",
            "scanned_files": scanned_files,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Failed to perform batch scan")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
async def delete_scan(request: DeleteScanRequest):
    """Delete a scanned file."""
    camera = await _get_scanner_camera(request.camera_name)
    try:
        success = await camera.delete_scan(request.filename)
        if success:
            return {"success": True, "message": f"Scan '{request.filename}' deleted"}
        raise HTTPException(status_code=404, detail=f"Scan file '{request.filename}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to delete scan")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{camera_name}/{filename}")
async def download_scan(camera_name: str, filename: str):
    """Download a scanned file."""
    camera = await _get_scanner_camera(camera_name)
    try:
        from pathlib import Path

        scan_path = Path(camera._output_dir) / filename
        if not scan_path.exists():
            raise HTTPException(status_code=404, detail=f"Scan file '{filename}' not found")

        return FileResponse(path=scan_path, filename=filename, media_type="application/octet-stream")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to download scan")
        raise HTTPException(status_code=500, detail=str(e))
