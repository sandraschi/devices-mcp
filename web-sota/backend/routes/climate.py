"""Climate endpoints (Midea PortaSplit: mock device now, msmart-ng LAN backend for the real unit).

Every unit dict carries ``mock``; the list response carries ``mock: true`` only when every unit
is simulated. Errors are structured: ``detail = {error, error_type, suggestions}``.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devices_mcp.integrations.midea_client import MOCK_SCENARIOS, MideaError, midea_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/climate", tags=["climate"])

_ERROR_STATUS = {
    "device_offline": 503,
    "connect_failed": 502,
    "device_not_found": 502,
    "command_failed": 502,
    "dependency_missing": 503,
    "invalid_config": 503,
    "unsupported": 422,
    "invalid_setpoint": 422,
    "not_mock": 409,
}


class ClimateControl(BaseModel):
    power: bool | None = None
    mode: str | None = None
    setpoint: float | None = None
    fan_speed: str | None = None
    swing: bool | None = None
    eco: bool | None = None
    turbo: bool | None = None
    sleep: bool | None = None


class MockScenario(BaseModel):
    scenario: str


def _http_error(exc: MideaError) -> HTTPException:
    return HTTPException(
        status_code=_ERROR_STATUS.get(exc.error_type, 502),
        detail={"error": str(exc), "error_type": exc.error_type, "suggestions": exc.suggestions},
    )


async def _unit_or_404(device_id: str):
    unit = await midea_manager.get_unit(device_id)
    if unit is None:
        raise HTTPException(status_code=404, detail=f"Unknown climate device '{device_id}'")
    return unit


@router.get("", summary="List climate units")
async def list_climate() -> dict[str, Any]:
    """All units, advanced to the wall clock first so mock physics are current."""
    units = await midea_manager.list_units()
    for unit in units:
        await unit.status()
    devices = [u.to_dict() for u in units]
    return {
        "success": True,
        "count": len(devices),
        "mock": bool(devices) and all(d["mock"] for d in devices),
        "scenarios": list(MOCK_SCENARIOS),
        "devices": devices,
    }


@router.get("/discover", summary="Find Midea units on the LAN (needs the 'climate' extra)")
async def discover_climate(timeout_s: int = 5) -> dict[str, Any]:
    """Broadcast discovery. Token and key are never returned."""
    try:
        found = await midea_manager.discover(max(1, min(timeout_s, 30)))
    except MideaError as exc:
        raise _http_error(exc) from exc
    return {"success": True, "count": len(found), "devices": found}


@router.get("/{device_id}", summary="Unit status")
async def climate_status(device_id: str) -> dict[str, Any]:
    """Live status snapshot for one unit."""
    unit = await _unit_or_404(device_id)
    await unit.status()
    return {"success": True, **unit.to_dict()}


@router.post("/{device_id}/control", summary="Control a unit")
async def climate_control(device_id: str, ctrl: ClimateControl) -> dict[str, Any]:
    """Power/mode/setpoint/fan/swing/eco/turbo/sleep (any subset)."""
    unit = await _unit_or_404(device_id)
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
        for flag in ("eco", "turbo", "sleep"):
            if (value := getattr(ctrl, flag)) is not None:
                await unit.set_flag(flag, value)
    except MideaError as exc:
        raise _http_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, **unit.to_dict()}


@router.post("/{device_id}/mock", summary="Apply a mock scenario (mock units only)")
async def climate_mock_scenario(device_id: str, body: MockScenario) -> dict[str, Any]:
    """Heatwave, cold snap, offline, fault, filter alert, reset: exercise UI states without hardware."""
    unit = await _unit_or_404(device_id)
    try:
        await unit.apply_scenario(body.scenario)
    except MideaError as exc:
        raise _http_error(exc) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, **unit.to_dict()}
