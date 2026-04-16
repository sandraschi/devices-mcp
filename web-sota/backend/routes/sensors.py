"""
Sensor API endpoints for real-world ingestion data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from devices_mcp.db import TimeSeriesDB
from devices_mcp.tools.energy.tapo_plug_tools import tapo_plug_manager


class ToggleRequest(BaseModel):
    """Request model for toggling device power state."""

    turn_on: bool

    class Config:
        """Pydantic config."""

        json_schema_extra = {"example": {"turn_on": False}}


router = APIRouter(prefix="/api/sensors", tags=["sensors"])


def get_sensors_db() -> TimeSeriesDB:
    """Lazy initialization of sensors database."""
    if not hasattr(get_sensors_db, "_db"):
        get_sensors_db._db = TimeSeriesDB()
    return get_sensors_db._db


def _model_dump(model: Any) -> dict[str, Any]:
    """Serialize Pydantic models across v1/v2."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()  # type: ignore[attr-defined]


@router.post("/tapo-p115/refresh", summary="Rediscover Tapo P115 plugs")
async def refresh_tapo_p115_devices() -> dict[str, Any]:
    """Force network discovery and return the updated device list."""
    try:
        await tapo_plug_manager.rediscover_devices()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Discovery failed: {e!s}") from e
    devices = await tapo_plug_manager.get_all_devices()
    response = []
    for device in devices:
        data = _model_dump(device)
        data["host"] = tapo_plug_manager.get_device_host(device.device_id)
        data["readonly"] = tapo_plug_manager.is_device_readonly(device.device_id)
        response.append(data)
    return {"devices": response, "count": len(response)}


@router.get("/tapo-p115", summary="List Tapo P115 smart plugs")
async def list_tapo_p115_devices() -> dict[str, Any]:
    """
    Return all Tapo P115 smart plugs with realtime metrics.
    """
    devices = await tapo_plug_manager.get_all_devices()
    response = []
    for device in devices:
        data = _model_dump(device)
        data["host"] = tapo_plug_manager.get_device_host(device.device_id)
        data["readonly"] = tapo_plug_manager.is_device_readonly(device.device_id)
        response.append(data)
    return {"devices": response, "count": len(response)}


@router.get(
    "/tapo-p115/{device_id}/history",
    summary="Get energy usage history",
)
async def get_tapo_p115_history(
    device_id: str,
    hours: int = Query(24, ge=1, le=168),
) -> dict[str, Any]:
    """
    Retrieve energy usage history for the specified Tapo P115 plug from database.
    """
    device = await tapo_plug_manager.get_device_status(device_id)
    if not device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

    # Get historical data from database
    history = get_sensors_db().get_energy_history(device_id=device_id, hours=hours)

    # Format data points for frontend
    data_points = [
        {
            "timestamp": _energy_timestamp_to_iso(point["timestamp"]),
            "power_w": point["power_w"],
            "voltage_v": point["voltage_v"],
            "current_a": point["current_a"],
            "power_consumption": point["power_w"],  # Alias for compatibility
        }
        for point in history
    ]

    if not data_points and device.current_power is not None:
        now = datetime.now(tz=UTC).isoformat()
        data_points = [
            {
                "timestamp": now,
                "power_w": float(device.current_power),
                "voltage_v": getattr(device, "voltage", None),
                "current_a": getattr(device, "current", None),
                "power_consumption": float(device.current_power),
            }
        ]

    return {
        "device_id": device_id,
        "device_name": device.name,
        "hours": hours,
        "data_points": data_points,
        "count": len(data_points),
    }


@router.post(
    "/tapo-p115/{device_id}/toggle",
    summary="Toggle P115 plug power state",
)
async def toggle_tapo_p115(
    device_id: str,
    toggle_request: ToggleRequest,
) -> dict[str, Any]:
    """
    Toggle power state of a Tapo P115 plug.
    """
    import logging

    logger = logging.getLogger(__name__)

    try:
        turn_on = toggle_request.turn_on
        logger.info(f"Toggle request for device {device_id}: turn_on={turn_on}")

        device = await tapo_plug_manager.get_device_status(device_id)
        if not device:
            raise HTTPException(status_code=404, detail=f"Device {device_id} not found")

        # Enforce read-only
        if tapo_plug_manager.is_device_readonly(device_id):
            raise HTTPException(status_code=403, detail="Device is read-only; toggling is disabled")

        logger.info(f"Toggling device {device_id} to {'ON' if turn_on else 'OFF'}")
        success = await tapo_plug_manager.toggle_device(device_id, turn_on)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to toggle device")

        # Refresh device status after a brief delay to allow device to update
        import asyncio

        await asyncio.sleep(0.5)

        # Re-discover devices to get fresh data from the actual device
        await tapo_plug_manager._discover_devices()
        updated_device = await tapo_plug_manager.get_device_status(device_id)

        logger.info(
            f"Device {device_id} toggled successfully, new state: {updated_device.power_state if updated_device else turn_on}"
        )
        return {
            "success": True,
            "device_id": device_id,
            "power_state": updated_device.power_state if updated_device else turn_on,
            "message": f"Device turned {'ON' if turn_on else 'OFF'}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error toggling device {device_id}")
        raise HTTPException(status_code=500, detail=f"Internal error: {e!s}")
