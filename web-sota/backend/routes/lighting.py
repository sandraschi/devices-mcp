"""Lighting routes - Connects to real MCP lighting tools."""

import logging

# Add src to Python path for MCP imports
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

router = APIRouter()
logger = logging.getLogger(__name__)


class HueBridgeIpBody(BaseModel):
    bridge_ip: str = Field(..., min_length=1, max_length=64, description="LAN IP of the Hue Bridge")


class HuePairBody(BaseModel):
    bridge_ip: str = Field(..., min_length=1, max_length=64)


@router.get("/api/lighting/hue/status")
async def get_philips_hue_status() -> dict[str, Any]:
    """Hue Bridge v2 setup status for the Lighting page (LAN + link button pairing)."""
    try:
        from devices_mcp.config import get_config
        from devices_mcp.tools.lighting.hue_tools import (
            PHUE_AVAILABLE,
            get_hue_manager,
            load_hue_bridge_cache,
        )

        raw = get_config() or {}
        hue_cfg = (raw.get("lighting") or {}).get("philips_hue") or {}

        if hue_cfg.get("enabled") is False:
            return {
                "enabled": False,
                "message": "Philips Hue is disabled in config (lighting.philips_hue.enabled).",
                "config_issue": True,
            }

        cache = load_hue_bridge_cache()
        bridge_ip = (hue_cfg.get("bridge_ip") or cache.get("bridge_ip") or "").strip() or None
        username = (hue_cfg.get("username") or cache.get("username") or "").strip() or None

        if not PHUE_AVAILABLE:
            return {
                "enabled": True,
                "phue_available": False,
                "message": "Install phue (pip install phue) to control Hue from this server.",
                "needs_bridge_ip": not bridge_ip,
                "needs_pairing": bool(bridge_ip) and not username,
                "bridge_ip": bridge_ip,
                "has_username": bool(username),
            }

        mgr = get_hue_manager()
        if not mgr._initialized and bridge_ip and username:
            await mgr.initialize()

        connected = bool(mgr._initialized and mgr._bridge is not None)
        err = mgr._connection_error

        return {
            "enabled": True,
            "phue_available": True,
            "bridge_ip": bridge_ip,
            "has_username": bool(username),
            "connected": connected,
            "needs_bridge_ip": not bridge_ip,
            "needs_pairing": bool(bridge_ip) and not username,
            "needs_reconnect": bool(bridge_ip) and bool(username) and not connected,
            "lights_count": len(mgr.lights) if connected else 0,
            "clip_v2_available": getattr(mgr, "_clip_v2_available", False),
            "clip_v2_error": getattr(mgr, "_clip_v2_error", None),
            "message": ("Hue is connected." if connected else (err or "Configure the bridge or pair below.")),
            "last_error": err if not connected else None,
        }
    except Exception as e:
        logger.exception("Hue status failed")
        return {"enabled": True, "error": str(e), "phue_available": True}


@router.get("/api/lighting/hue/discover")
async def discover_philips_hue_bridges() -> dict[str, Any]:
    """Discover Hue bridges via Philips cloud (same LAN usually required for control)."""
    try:
        from devices_mcp.tools.lighting.hue_tools import discover_hue_bridges_cloud

        bridges = await discover_hue_bridges_cloud()
        return {
            "bridges": bridges,
            "success": True,
            "hint": (
                "If this list is empty, open the Hue app → Settings → Hue bridges → "
                "note the IP, or set lighting.philips_hue.bridge_ip manually."
            ),
        }
    except Exception as e:
        logger.exception("Hue discover failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/lighting/hue/bridge")
async def set_philips_hue_bridge_ip(body: HueBridgeIpBody) -> dict[str, Any]:
    """Remember bridge IP in hue_bridge.cache (no link button yet)."""
    try:
        from devices_mcp.tools.lighting.hue_tools import (
            load_hue_bridge_cache,
            reset_hue_manager,
            save_hue_bridge_cache,
        )

        cache = load_hue_bridge_cache()
        cache["bridge_ip"] = body.bridge_ip.strip()
        save_hue_bridge_cache(cache)
        reset_hue_manager()
        return {"success": True, "bridge_ip": cache["bridge_ip"]}
    except Exception as e:
        logger.exception("Hue set bridge IP failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/lighting/hue/pair")
async def hue_pair_route(body: HuePairBody) -> dict[str, Any]:
    """Pair with the bridge (press link button first). Saves API username to hue_bridge.cache."""
    try:
        from devices_mcp.tools.lighting.hue_tools import pair_philips_hue_bridge as run_hue_pair

        return await run_hue_pair(body.bridge_ip)
    except Exception as e:
        logger.exception("Hue pair failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _hue_motionaware_status_body() -> dict[str, Any]:
    from devices_mcp.tools.lighting.hue_tools import get_hue_manager

    mgr = get_hue_manager()
    if not mgr._initialized:
        await mgr.initialize()
    status = await mgr.get_homeaware_status()
    return {"success": True, "motionaware": status, "homeaware": status}


@router.get("/api/lighting/hue/motionaware/status")
@router.get("/api/lighting/hue/homeaware/status")
async def hue_motionaware_status() -> dict[str, Any]:
    """MotionAware motion areas — Signify Hue API v2 (CLIP)."""
    try:
        return await _hue_motionaware_status_body()
    except Exception as e:
        logger.exception("Hue MotionAware status failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/lighting/hue/motionaware/motion")
@router.get("/api/lighting/hue/homeaware/motion")
async def hue_motionaware_motion_poll() -> dict[str, Any]:
    """Poll MotionAware areas for new motion edges (same logic as MCP monitor)."""
    try:
        from devices_mcp.tools.lighting.hue_tools import get_hue_manager

        mgr = get_hue_manager()
        if not mgr._initialized:
            await mgr.initialize()
        events = await mgr.monitor_homeaware_motion()
        return {"success": True, "events": events, "count": len(events)}
    except Exception as e:
        logger.exception("Hue MotionAware motion poll failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/lighting/hue/reconnect")
async def reconnect_philips_hue() -> dict[str, Any]:
    """Re-run Hue manager initialize after config/cache changes."""
    try:
        from devices_mcp.tools.lighting.hue_tools import get_hue_manager, reset_hue_manager

        reset_hue_manager()
        mgr = get_hue_manager()
        ok = await mgr.initialize()
        if not ok:
            raise HTTPException(
                status_code=503,
                detail=mgr._connection_error or "Hue initialization failed",
            )
        return {
            "success": True,
            "lights_count": len(mgr.lights),
            "message": "Hue Bridge connected.",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Hue reconnect failed")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/lighting/status")
async def get_lighting_status() -> dict[str, Any]:
    """Get all lighting devices status using MCP lighting tools."""
    try:
        # Import MCP lighting tools
        from devices_mcp.tools.portmanteau.lighting_management import _list_lights

        # Execute the MCP tool function to get real lighting data
        result = await _list_lights()

        if not result.get("success", False):
            logger.error(f"Failed to get lighting status: {result.get('error', 'Unknown error')}")
            raise HTTPException(status_code=500, detail="Failed to retrieve lighting data")

        lights = result.get("lights", [])
        logger.info(f"Retrieved {len(lights)} lighting devices from MCP tools")

        return {
            "devices": lights,
            "total_lights": len(lights),
            "active_lights": len([l for l in lights if l.get("is_on", False)]),
            "success": True,
        }

    except Exception as e:
        logger.exception(f"Error in get_lighting_status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/lighting/control")
async def control_lighting_device(device_id: str, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Control lighting device using MCP lighting tools."""
    try:
        # Import MCP lighting tools
        from devices_mcp.tools.portmanteau.lighting_management import LightingManagementTool

        # Validate action
        valid_actions = ["on", "off", "toggle", "brightness", "color", "scene"]
        if action not in valid_actions:
            raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {valid_actions}")

        # Execute the MCP tool to control device
        tool = LightingManagementTool()
        result = await tool.execute(operation="control", device_id=device_id, action=action, **(params or {}))

        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "Control operation failed"))

        return {
            "success": True,
            "device_id": device_id,
            "action": action,
            "new_state": result.get("new_state", "unknown"),
            "result": result,
        }

    except Exception as e:
        logger.exception(f"Error controlling lighting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/lighting/scenes")
async def get_lighting_scenes() -> dict[str, Any]:
    """Get available lighting scenes using MCP lighting tools."""
    try:
        # Import MCP lighting tools
        from devices_mcp.tools.portmanteau.lighting_management import LightingManagementTool

        # Execute the MCP tool to get scenes
        tool = LightingManagementTool()
        result = await tool.execute(operation="scenes")

        if not result.get("success", False):
            logger.error(f"Failed to get lighting scenes: {result.get('error', 'Unknown error')}")
            raise HTTPException(status_code=500, detail="Failed to retrieve lighting scenes")

        return {"scenes": result.get("scenes", []), "success": True}

    except Exception as e:
        logger.exception(f"Error in get_lighting_scenes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/lighting/scene")
async def activate_lighting_scene(scene_name: str) -> dict[str, Any]:
    """Activate a lighting scene using MCP lighting tools."""
    try:
        # Import MCP lighting tools
        from devices_mcp.tools.portmanteau.lighting_management import LightingManagementTool

        # Execute the MCP tool to activate scene
        tool = LightingManagementTool()
        result = await tool.execute(operation="activate_scene", scene_name=scene_name)

        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "Scene activation failed"))

        return {"success": True, "scene_name": scene_name, "result": result}

    except Exception as e:
        logger.exception(f"Error activating lighting scene {scene_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/lighting/device/{device_id}")
async def get_lighting_device_details(device_id: str) -> dict[str, Any]:
    """Get detailed information about a specific lighting device."""
    try:
        # Import MCP lighting tools
        from devices_mcp.tools.portmanteau.lighting_management import LightingManagementTool

        # Execute the MCP tool to get device details
        tool = LightingManagementTool()
        result = await tool.execute(operation="device_info", device_id=device_id)

        if not result.get("success", False):
            raise HTTPException(status_code=404, detail=f"Lighting device '{device_id}' not found")

        device = result.get("device", {})

        return {"device": device, "success": True}

    except Exception as e:
        logger.exception(f"Error getting lighting device details for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/lighting/groups")
async def get_lighting_groups() -> dict[str, Any]:
    """Get lighting groups using MCP lighting tools."""
    try:
        # Import MCP lighting tools
        from devices_mcp.tools.portmanteau.lighting_management import LightingManagementTool

        # Execute the MCP tool to get groups
        tool = LightingManagementTool()
        result = await tool.execute(operation="groups")

        if not result.get("success", False):
            logger.error(f"Failed to get lighting groups: {result.get('error', 'Unknown error')}")
            raise HTTPException(status_code=500, detail="Failed to retrieve lighting groups")

        return {"groups": result.get("groups", []), "success": True}

    except Exception as e:
        logger.exception(f"Error in get_lighting_groups: {e}")
        raise HTTPException(status_code=500, detail=str(e))
