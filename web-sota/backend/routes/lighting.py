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
            probe_hue_bridge,
            validate_hue_username,
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

        bridge_probe: dict[str, Any] = {}
        username_valid = False
        username_error: str | None = None
        if bridge_ip:
            bridge_probe = await probe_hue_bridge(bridge_ip)
            if username and bridge_probe.get("reachable"):
                username_valid, username_error = await validate_hue_username(bridge_ip, username)

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
            if mgr._initialized and not mgr.lights:
                try:
                    await mgr.rescan()
                except Exception:
                    logger.debug("Hue rescan after init skipped", exc_info=True)

        connected = bool(mgr._initialized and mgr._bridge is not None)
        err = mgr._connection_error

        needs_pairing = bool(bridge_ip) and (not username or not username_valid)
        needs_reconnect = bool(bridge_ip) and bool(username) and username_valid and not connected

        return {
            "enabled": True,
            "phue_available": True,
            "bridge_ip": bridge_ip,
            "has_username": bool(username),
            "username_valid": username_valid,
            "connected": connected,
            "needs_bridge_ip": not bridge_ip,
            "needs_pairing": needs_pairing,
            "needs_reconnect": needs_reconnect,
            "requires_https": bridge_probe.get("requires_https"),
            "bridge_model": bridge_probe.get("modelid"),
            "bridge_name": bridge_probe.get("name"),
            "bridge_reachable": bridge_probe.get("reachable"),
            "bridge_port": bridge_probe.get("port"),
            "lights_count": len(mgr.lights) if connected else 0,
            "clip_v2_available": getattr(mgr, "_clip_v2_available", False),
            "clip_v2_error": getattr(mgr, "_clip_v2_error", None),
            "message": (
                "Hue is connected." if connected else (err or username_error or "Configure the bridge or pair below.")
            ),
            "last_error": err if not connected else None,
            "username_error": username_error,
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
        try:
            await mgr.rescan()
        except Exception as exc:
            logger.warning("Hue rescan after reconnect failed: %s", exc)
        return {
            "success": True,
            "lights_count": len(mgr.lights),
            "message": "Hue Bridge connected.",
            "bridge_name": mgr._bridge_name,
            "requires_https": mgr._requires_https,
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

        lights = (result.get("result") or {}).get("lights", [])
        logger.info(f"Retrieved {len(lights)} lighting devices from MCP tools")

        return {
            "devices": lights,
            "total_lights": len(lights),
            "active_lights": len([light for light in lights if light.get("is_on", False)]),
            "success": True,
        }

    except Exception as e:
        logger.exception(f"Error in get_lighting_status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/lighting/control")
async def control_lighting_device(device_id: str, action: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Control lighting device using MCP lighting tools."""
    try:
        from devices_mcp.tools.portmanteau.lighting_management import _control_light

        valid_actions = ["on", "off", "toggle", "brightness", "color", "scene"]
        if action not in valid_actions:
            raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {valid_actions}")

        kwargs: dict[str, Any] = {}
        if action == "on":
            kwargs["power_state"] = "on"
        elif action == "off":
            kwargs["power_state"] = "off"
        elif action == "toggle":
            kwargs["power_state"] = "toggle"
        elif action == "brightness":
            kwargs["brightness_percent"] = int((params or {}).get("brightness_percent", 100))
        elif action == "color":
            rgb_val = (params or {}).get("rgb", [255, 255, 255])
            kwargs["rgb"] = rgb_val

        result = await _control_light(device_id, **kwargs)

        if not result.get("success", False):
            raise HTTPException(status_code=400, detail=result.get("error", "Control operation failed"))

        return {
            "success": True,
            "device_id": device_id,
            "action": action,
            "new_state": result.get("result", {}).get("current_state", "unknown"),
            "result": result,
        }

    except Exception as e:
        logger.exception(f"Error controlling lighting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/lighting/scenes")
async def get_lighting_scenes() -> dict[str, Any]:
    """Get available lighting scenes from Hue bridge."""
    try:
        from devices_mcp.tools.lighting.hue_tools import get_hue_manager

        mgr = get_hue_manager()
        if not mgr._initialized:
            await mgr.initialize()

        if not mgr._initialized:
            return {"scenes": [], "success": True, "hint": "Hue bridge not connected"}

        hue_scenes = await mgr.get_all_scenes()
        scene_names = [s.name or str(s.scene_id) for s in hue_scenes]

        return {"scenes": scene_names, "success": True}

    except Exception as e:
        logger.exception(f"Error in get_lighting_scenes: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/lighting/scene")
async def activate_lighting_scene(scene_name: str, group_name: str | None = None) -> dict[str, Any]:
    """Activate a lighting scene on the Hue bridge, optionally on a specific group."""
    try:
        from devices_mcp.tools.lighting.hue_tools import get_hue_manager

        mgr = get_hue_manager()
        if not mgr._initialized:
            await mgr.initialize()

        if not mgr._initialized or not mgr._bridge:
            raise HTTPException(status_code=503, detail="Hue bridge not connected")

        scenes = await mgr.get_all_scenes()
        target = next((s for s in scenes if (s.name or str(s.scene_id)) == scene_name), None)
        if target is None:
            raise HTTPException(status_code=404, detail=f"Scene '{scene_name}' not found")

        group_id: str | None = target.group or None
        if group_name:
            groups = await mgr.get_all_groups()
            matched = next((g for g in groups if g.name == group_name), None)
            if not matched:
                raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")
            group_id = str(matched.group_id)

        await mgr.activate_scene(scene_id=target.scene_id, group_id=group_id)
        return {"success": True, "scene_name": scene_name, "group_name": group_name or target.group}

    except Exception as e:
        logger.exception(f"Error activating lighting scene {scene_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/lighting/device/{device_id}")
async def get_lighting_device_details(device_id: str) -> dict[str, Any]:
    """Get detailed information about a specific lighting device."""
    try:
        from devices_mcp.tools.portmanteau.lighting_management import _get_light_status

        result = await _get_light_status(device_id)

        if not result.get("success", False):
            raise HTTPException(status_code=404, detail=f"Lighting device '{device_id}' not found")

        device = (result.get("result") or {}).get("light", {})
        return {"device": device, "success": True}

    except Exception as e:
        logger.exception(f"Error getting lighting device details for {device_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/lighting/groups")
async def get_lighting_groups() -> dict[str, Any]:
    """Get lighting groups from Hue bridge."""
    try:
        from devices_mcp.tools.lighting.hue_tools import get_hue_manager

        mgr = get_hue_manager()
        if not mgr._initialized:
            await mgr.initialize()

        if not mgr._initialized:
            return {"groups": [], "success": True, "hint": "Hue bridge not connected"}

        hue_groups = await mgr.get_all_groups()
        groups_data = [
            {
                "group_id": str(g.group_id),
                "name": g.name,
                "type": g.type,
                "lights": g.lights,
                "light_count": len(g.lights),
            }
            for g in hue_groups
        ]

        return {"groups": groups_data, "success": True}

    except Exception as e:
        logger.exception(f"Error in get_lighting_groups: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
