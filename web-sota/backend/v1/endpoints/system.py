"""
System and administration API endpoints.
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from devices_mcp.config import ServerConfig
from devices_mcp.core.models import SystemInfo, SystemStatus

router = APIRouter()

# API key header for authentication
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str = Depends(api_key_header),
    config: ServerConfig = Depends(lambda: ServerConfig()),
) -> None:
    """Verify the API key from the request header."""
    if config.api_key and api_key != config.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")


@router.get("/info", response_model=SystemInfo)
async def get_system_info():
    """Get system information."""
    return {
        "name": "Devices MCP",
        "version": "1.0.0",
        "uptime": 0,  # Would be calculated from startup time
        "startup_time": datetime.utcnow().isoformat(),
        "status": "running",
    }


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get system status and health."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "api": "ok",
            "database": "ok",
            "camera_manager": "ok",
            "storage": "ok",
        },
    }


@router.get("/config")
async def get_system_config(_: None = Depends(verify_api_key)) -> Dict[str, Any]:
    """Get the current system configuration (requires authentication)."""
    # This would return the current configuration
    return {"status": "success", "config": {}}


@router.post("/restart")
async def restart_system(_: None = Depends(verify_api_key)):
    """Restart the system (requires authentication)."""
    # This would trigger a system restart
    return {"status": "success", "message": "System restart initiated"}


@router.get("/logs")
async def get_system_logs(
    _: None = Depends(verify_api_key), _lines: int = 100, _level: str = "INFO"
):
    """Get system logs (requires authentication)."""
    # This would return the system logs
    return {
        "status": "success",
        "logs": [f"{datetime.utcnow().isoformat()} - INFO - Example log entry"],
    }
