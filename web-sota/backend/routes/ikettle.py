"""iKettle smart kettle API endpoints."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ikettle", tags=["ikettle"])

# Global iKettle client instance
_ikettle_client = None


class BoilRequest(BaseModel):
    """Request to boil water."""

    temperature_c: int = 100  # Celsius


class KeepWarmRequest(BaseModel):
    """Request to set keep warm mode."""

    temperature_c: int = 95  # Celsius
    duration_minutes: int = 30


class ScheduleRequest(BaseModel):
    """Request to schedule a boil."""

    temperature_c: int = 100  # Celsius
    delay_minutes: int = 0


class MorningRoutineRequest(BaseModel):
    """Request to setup morning coffee routine."""

    wake_time: str = "07:00"  # HH:MM format
    coffee_temperature: int = 95  # Celsius


async def get_ikettle_client():
    """Get or create iKettle client instance."""
    global _ikettle_client

    if _ikettle_client is None:
        # Import config directly
        from devices_mcp.config import get_config

        config = get_config()

        if not config.get("ikettle", {}).get("enabled", False):
            raise HTTPException(status_code=404, detail="iKettle integration not enabled")

        ikettle_config = config["ikettle"]
        host = ikettle_config.get("host")

        if not host:
            raise HTTPException(status_code=500, detail="iKettle host not configured")

        from devices_mcp.integrations.ikettle_client import IKettleClient

        _ikettle_client = IKettleClient(
            host=host,
            username=ikettle_config.get("username"),
            password=ikettle_config.get("password"),
        )

        # Try to connect
        connected = await _ikettle_client.connect()
        if not connected:
            raise HTTPException(status_code=503, detail="Cannot connect to iKettle")

    return _ikettle_client


@router.get("/status")
async def get_ikettle_status():
    """Get iKettle status."""
    try:
        client = await get_ikettle_client()
        status = await client.get_formatted_status()

        return {"success": True, "status": status}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get iKettle status")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/boil")
async def boil_water(request: BoilRequest):
    """Start boiling water."""
    try:
        client = await get_ikettle_client()
        success = await client.boil(request.temperature_c)

        if success:
            return {
                "success": True,
                "message": f"Started boiling water to {request.temperature_c}°C",
                "temperature_c": request.temperature_c,
                "temperature_f": client.get_temperature_fahrenheit(request.temperature_c),
            }
        raise HTTPException(status_code=500, detail="Failed to start boiling")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to boil water")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/keep-warm")
async def set_keep_warm(request: KeepWarmRequest):
    """Set keep warm mode."""
    try:
        client = await get_ikettle_client()
        success = await client.keep_warm(request.temperature_c, request.duration_minutes)

        if success:
            return {
                "success": True,
                "message": f"Set keep warm to {request.temperature_c}°C for {request.duration_minutes} minutes",
                "temperature_c": request.temperature_c,
                "duration_minutes": request.duration_minutes,
            }
        raise HTTPException(status_code=500, detail="Failed to set keep warm")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to set keep warm")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/stop")
async def stop_kettle():
    """Stop current kettle operation."""
    try:
        client = await get_ikettle_client()
        success = await client.stop()

        if success:
            return {"success": True, "message": "Stopped kettle operation"}
        raise HTTPException(status_code=500, detail="Failed to stop kettle")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to stop kettle")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/schedule")
async def schedule_boil(request: ScheduleRequest):
    """Schedule a boil operation."""
    try:
        client = await get_ikettle_client()
        success = await client.schedule_boil(request.temperature_c, request.delay_minutes)

        if success:
            return {
                "success": True,
                "message": f"Scheduled boil to {request.temperature_c}°C in {request.delay_minutes} minutes",
                "temperature_c": request.temperature_c,
                "delay_minutes": request.delay_minutes,
            }
        raise HTTPException(status_code=500, detail="Failed to schedule boil")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to schedule boil")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/morning-routine")
async def setup_morning_routine(request: MorningRoutineRequest):
    """Setup morning coffee routine."""
    try:
        client = await get_ikettle_client()
        result = await client.setup_morning_routine(request.wake_time, request.coffee_temperature)

        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "wake_time": request.wake_time,
                "coffee_temperature": request.coffee_temperature,
                "delay_minutes": result.get("delay_minutes"),
            }
        raise HTTPException(
            status_code=500, detail=result.get("error", "Failed to setup morning routine")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to setup morning routine")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/mode/{mode}")
async def set_mode(mode: str):
    """Set kettle mode (wake_up, home, formula)."""
    try:
        valid_modes = ["wake_up", "home", "formula"]
        if mode not in valid_modes:
            raise HTTPException(
                status_code=400, detail=f"Invalid mode. Must be one of: {', '.join(valid_modes)}"
            )

        client = await get_ikettle_client()
        success = await client.set_mode(mode)

        if success:
            return {"success": True, "message": f"Set kettle mode to {mode}", "mode": mode}
        raise HTTPException(status_code=500, detail="Failed to set mode")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to set mode {mode}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/info")
async def get_ikettle_info():
    """Get detailed iKettle information."""
    try:
        client = await get_ikettle_client()

        # Get current status
        status = await client.get_formatted_status()

        # Get water level
        water_level = await client.get_water_level()

        # Get current temperature
        current_temp = await client.get_current_temperature()

        # Check if boiling
        is_boiling = await client.is_boiling()

        info = {
            "name": "Smarter iKettle",
            "host": client.host,
            "connected": status.get("connected", False),
            "current_state": status.get("state", "unknown"),
            "current_temperature_c": current_temp,
            "current_temperature_f": status.get("current_temperature_f"),
            "water_level": water_level,
            "mode": status.get("mode", "unknown"),
            "keep_warm_active": status.get("keep_warm_active", False),
            "is_boiling": is_boiling,
            "capabilities": {
                "temperature_control": True,
                "keep_warm": True,
                "scheduling": True,
                "modes": ["wake_up", "home", "formula"],
                "temperature_range_c": [20, 100],
                "temperature_range_f": [68, 212],
            },
            "recommendations": {
                "coffee": 95,  # °C
                "green_tea": 80,
                "black_tea": 100,
                "herbal_tea": 100,
                "white_tea": 85,
            },
        }

        return {"success": True, "info": info}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to get iKettle info")
        raise HTTPException(status_code=500, detail=str(e)) from e
