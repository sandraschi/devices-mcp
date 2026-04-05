"""
Thermal camera sensor API endpoints.

For hot spot detection using MLX90640/AMG8833 sensors via ESP32.
Detects oven left on, server overheating, electrical issues, etc.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devices_mcp.integrations.thermal_client import (
    get_thermal_client,
    init_thermal_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/thermal", tags=["Thermal"])


class ThermalSensorConfig(BaseModel):
    ip: str
    name: str
    threshold_c: Optional[float] = None
    location: Optional[str] = None


class ThermalInitRequest(BaseModel):
    sensors: list[ThermalSensorConfig]


@router.get("/status")
async def get_thermal_status():
    """Get thermal sensor connection status."""
    client = get_thermal_client()
    if not client:
        return {
            "connected": False,
            "initialized": False,
            "message": "Thermal client not configured",
        }

    return {
        "connected": True,
        "initialized": client.is_initialized,
        "message": "Connected" if client.is_initialized else "Not initialized",
    }


@router.get("/summary")
async def get_thermal_summary():
    """Get thermal sensor summary for dashboard."""
    client = get_thermal_client()
    if not client:
        return {
            "initialized": False,
            "sensor_count": 0,
            "sensors": [],
            "alerts": [],
        }

    try:
        return await client.get_summary()
    except Exception as e:
        logger.exception("Failed to get thermal summary")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sensors")
async def get_all_sensors():
    """Get all thermal sensor readings."""
    client = get_thermal_client()
    if not client or not client.is_initialized:
        raise HTTPException(status_code=503, detail="Thermal sensors not initialized")

    try:
        sensors = await client.get_all_sensors()
        return {
            "sensors": [s.to_dict() for s in sensors],
            "count": len(sensors),
        }
    except Exception as e:
        logger.exception("Failed to get thermal sensors")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/alerts")
async def get_thermal_alerts():
    """Get sensors with active temperature alerts."""
    client = get_thermal_client()
    if not client or not client.is_initialized:
        raise HTTPException(status_code=503, detail="Thermal sensors not initialized")

    try:
        alerts = await client.get_alerts()
        return {
            "alerts": [s.to_dict() for s in alerts],
            "count": len(alerts),
            "has_alerts": len(alerts) > 0,
        }
    except Exception as e:
        logger.exception("Failed to get thermal alerts")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/frame/{ip}")
async def get_thermal_frame(ip: str, include_pixels: bool = False):
    """Get thermal frame from a specific sensor.

    Args:
        ip: Sensor IP address
        include_pixels: Whether to include raw pixel data (larger response)
    """
    client = get_thermal_client()
    if not client or not client.is_initialized:
        raise HTTPException(status_code=503, detail="Thermal sensors not initialized")

    try:
        frame = await client.get_frame(ip, include_pixels=include_pixels)
        if not frame:
            raise HTTPException(status_code=404, detail=f"Sensor {ip} not found or offline")

        return {"frame": frame.to_dict(include_pixels=include_pixels)}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get thermal frame for {ip}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/init")
async def initialize_thermal(request: ThermalInitRequest):
    """Initialize thermal sensors with configurations.

    Example request:
    {
        "sensors": [
            {
                "ip": "192.168.1.100",
                "name": "Kitchen Thermal",
                "threshold_c": 150,
                "location": "Kitchen"
            },
            {
                "ip": "192.168.1.101",
                "name": "Server Rack",
                "threshold_c": 50,
                "location": "Server Room"
            }
        ]
    }
    """
    try:
        sensors = [s.model_dump() for s in request.sensors]
        client = await init_thermal_client(sensors=sensors)

        return {
            "success": client.is_initialized,
            "sensor_count": len(client._sensors),
            "message": (
                f"Initialized with {len(client._sensors)} sensors"
                if client.is_initialized
                else "No sensors found"
            ),
        }
    except Exception as e:
        logger.exception("Failed to initialize thermal sensors")
        raise HTTPException(status_code=500, detail=str(e)) from e
