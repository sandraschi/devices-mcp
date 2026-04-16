"""
Log management API endpoints for manual log operations.
"""

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException

from devices_mcp.utils.log_manager import get_log_stats, sanitize_logs_now

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/logs", tags=["log-management"])


@router.post("/sanitize", summary="Sanitize log files")
async def sanitize_logs(background_tasks: BackgroundTasks, log_files: list[str] = None) -> dict[str, Any]:
    """
    Manually trigger log sanitization (rotation, compression, cleanup).

    Args:
        log_files: Optional list of specific log files to sanitize.
                  If not provided, all log files will be processed.

    Returns:
        Dict containing the results of sanitization operations.
    """
    try:
        # Run sanitization in background to avoid blocking
        background_tasks.add_task(_sanitize_logs_background, log_files)
        return {"message": "Log sanitization started in background", "status": "running"}
    except Exception as e:
        logger.exception(f"Failed to start log sanitization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start log sanitization: {e!s}")


@router.get("/stats", summary="Get log statistics")
async def get_logs_stats() -> dict[str, Any]:
    """
    Get statistics about log files in the managed directory.

    Returns:
        Dict containing log statistics and configuration info.
    """
    try:
        return get_log_stats()
    except Exception as e:
        logger.exception(f"Failed to get log stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get log stats: {e!s}")


@router.post("/rotate/{log_file}", summary="Rotate specific log file")
async def rotate_log_file(log_file: str, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """
    Manually rotate a specific log file.

    Args:
        log_file: Name of the log file to rotate (without path).

    Returns:
        Dict indicating rotation status.
    """
    try:
        from devices_mcp.utils.log_manager import LogManager

        log_manager = LogManager()

        # Run rotation in background
        background_tasks.add_task(_rotate_log_background, log_manager, log_file)
        return {"message": f"Log rotation started for {log_file}", "status": "running"}
    except Exception as e:
        logger.exception(f"Failed to start log rotation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start log rotation: {e!s}")


async def _sanitize_logs_background(log_files: list[str] = None):
    """Background task for log sanitization"""
    try:
        results = sanitize_logs_now(log_files)
        logger.info(f"Background log sanitization completed: {results}")
    except Exception as e:
        logger.exception(f"Background log sanitization failed: {e}")


async def _rotate_log_background(log_manager: "LogManager", log_file: str):
    """Background task for log rotation"""
    try:
        success = log_manager.rotate_log(log_file, force=True)
        if success:
            logger.info(f"Background log rotation completed for {log_file}")
        else:
            logger.warning(f"Background log rotation failed or not needed for {log_file}")
    except Exception as e:
        logger.exception(f"Background log rotation failed for {log_file}: {e}")
