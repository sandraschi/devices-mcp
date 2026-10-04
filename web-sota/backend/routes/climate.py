"""Climate endpoints (Midea PortaSplit, mock until winter hardware).

Every response carries mock=true while the demo unit serves. Winter flip:
real units appear here automatically once climate.midea.mock=false with LAN creds.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devices_mcp.integrations.midea_client import midea_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/climate", tags=["climate"])


class ClimateControl(BaseModel):
    power: bool | None = None
    mode: str | None = None
    setpoint: float | None = None
    fan_speed: str | None = None
    swing: bool | None = None


@router.get("", summary="List climate units")
async def list_climate() -> dict[str, Any]:
    """All units (demo mock present until winter hardware)."""
    units = await midea_manager.list_units()
    devices = [u.to_dict() for u in units]
    return {
        "success": True,
        "count": len(devices),
        "mock": all(d["mock"] for d in devices),
        "devices": devices,
    }


@router.get("/{device_id}", summary="Unit status")
async def climate_status(device_id: str) -> dict[str, Any]:
    """Live status snapshot for one unit."""
    unit = await midea_manager.get_unit(device_id)
    if unit is None:
        raise HTTPException(status_code=404, detail=f"Unknown climate device '{device_id}'")
    return {"success": True, **unit.to_dict()}


@router.post("/{device_id}/control", summary="Control a unit")
async def climate_control(device_id: str, ctrl: ClimateControl) -> dict[str, Any]:
    """Power/mode/setpoint/fan/swing (any subset)."""
    unit = await midea_manager.get_unit(device_id)
    if unit is None:
        raise HTTPException(status_code=404, detail=f"Unknown climate device '{device_id}'")
    try:
        if ctrl.power is not None:
            await unit.set_power(ctrl.power)
        if ctrl.mode is not None:
            await unit.set_mode(ctrl.mode)
        if ctrl.setpoint is not None:
            await unit.set_setpoint(ctrl.setpoint)
        if ctrl.fan_speed is not None:
            await unit.set_fan(ctrl.fan_speed)
        if ctrl.swing is not None:
            await unit.set_swing(ctrl.swing)
    except (ValueError, NotImplementedError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"success": True, **unit.to_dict()}
