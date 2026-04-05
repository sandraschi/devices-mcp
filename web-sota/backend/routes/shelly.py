"""
Shelly temperature sensor API endpoints.

For monitoring freezers, fridges, and other temperature-critical areas
using Shelly Plus devices with DS18B20 probes.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devices_mcp.integrations.shelly_client import (
    get_shelly_client,
    init_shelly_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/shelly", tags=["Shelly"])


class ShellyDeviceConfig(BaseModel):
    ip: str
    name: str
    thresholds: Optional[dict] = None


class ShellyInitRequest(BaseModel):
    devices: list[ShellyDeviceConfig]


@router.get("/status")
async def get_shelly_status():
    """Get Shelly connection status."""
    client = get_shelly_client()
    if not client:
        return {
            "connected": False,
            "initialized": False,
            "message": "Shelly client not configured",
        }

    return {
        "connected": True,
        "initialized": client.is_initialized,
        "message": "Connected" if client.is_initialized else "Not initialized",
    }


@router.get("/summary")
async def get_shelly_summary():
    """Get Shelly summary for dashboard."""
    client = get_shelly_client()
    if not client:
        return {
            "initialized": False,
            "device_count": 0,
            "sensor_count": 0,
            "sensors": [],
            "alerts": [],
        }

    try:
        return await client.get_summary()
    except Exception as e:
        logger.exception("Failed to get Shelly summary")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/temperatures")
async def get_temperatures():
    """Get all temperature readings from Shelly sensors.

    Returns temperature data from all configured Shelly devices
    with DS18B20 probes (Add-On sensors).
    """
    client = get_shelly_client()
    if not client or not client.is_initialized:
        raise HTTPException(status_code=503, detail="Shelly not initialized")

    try:
        sensors = await client.get_all_temperatures()
        return {
            "sensors": [s.to_dict() for s in sensors],
            "count": len(sensors),
            "alerts": [s.to_dict() for s in sensors if s.alert_active],
        }
    except Exception as e:
        logger.exception("Failed to get Shelly temperatures")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/device/{ip}")
async def get_device_status(ip: str):
    """Get full status of a specific Shelly device."""
    client = get_shelly_client()
    if not client or not client.is_initialized:
        raise HTTPException(status_code=503, detail="Shelly not initialized")

    try:
        status = await client.get_device_status(ip)
        if not status:
            raise HTTPException(status_code=404, detail=f"Device {ip} not found")
        return {"status": status}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get Shelly device status for {ip}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/init")
async def initialize_shelly(request: ShellyInitRequest):
    """Initialize Shelly client with device configurations.

    Example request:
    {
        "devices": [
            {
                "ip": "192.168.1.100",
                "name": "Freezer",
                "thresholds": {"high_c": -10, "low_c": -25}
            },
            {
                "ip": "192.168.1.101",
                "name": "Fridge",
                "thresholds": {"high_c": 8, "low_c": 2}
            }
        ]
    }
    """
    try:
        devices = [d.model_dump() for d in request.devices]
        client = await init_shelly_client(devices=devices)

        return {
            "success": client.is_initialized,
            "device_count": len(client._devices),
            "message": (
                f"Initialized with {len(client._devices)} devices"
                if client.is_initialized
                else "No devices found"
            ),
        }
    except Exception as e:
        logger.exception("Failed to initialize Shelly")
        raise HTTPException(status_code=500, detail=str(e)) from e
