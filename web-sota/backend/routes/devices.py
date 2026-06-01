"""
Unified device inventory API (config + health + discovery).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import APIRouter

from devices_mcp.config import get_config
from devices_mcp.core.connection_supervisor import get_supervisor
from devices_mcp.core.device_registry import build_device_inventory, discover_devices

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("")
async def list_all_devices(run_discovery: bool = False) -> dict[str, Any]:
    """
    Full device table: configured entries merged with supervisor health.

    Query `run_discovery=true` to append LAN-discovered devices (respects config discovery flags).
    """
    try:
        config = get_config() or {}
        supervisor = get_supervisor()
        try:
            await asyncio.wait_for(supervisor._check_all_devices(), timeout=12.0)
        except TimeoutError:
            logger.warning("Device list: health check timed out, using cache")
        except Exception as e:
            logger.warning("Device list: health check failed: %s", e)

        health = supervisor.get_health_summary()
        extra = await discover_devices(config) if run_discovery else []
        return build_device_inventory(config, health, extra)
    except Exception as e:
        logger.exception("Error building device inventory")
        return {
            "error": str(e),
            "total_devices": 0,
            "online": 0,
            "offline": 0,
            "unknown": 0,
            "devices": [],
        }


@router.post("/discover")
async def trigger_discovery() -> dict[str, Any]:
    """Run LAN discovery (Tapo plugs, USB cameras, etc.) and return updated inventory."""
    try:
        config = get_config() or {}
        discovered = await discover_devices(config)
        supervisor = get_supervisor()
        try:
            await asyncio.wait_for(supervisor._check_all_devices(), timeout=12.0)
        except TimeoutError:
            pass
        health = supervisor.get_health_summary()
        inventory = build_device_inventory(config, health, discovered)
        inventory["discovery_run"] = True
        inventory["newly_discovered"] = len(discovered)
        return inventory
    except Exception as e:
        logger.exception("Discovery failed")
        return {"error": str(e), "devices": [], "discovery_run": False}


@router.get("/presets")
async def list_presets() -> dict[str, Any]:
    """Available home presets for first-time setup."""
    from devices_mcp.config.vienna_defaults import resolve_preset_config

    return {
        "presets": [
            {
                "id": "vienna",
                "label": "Vienna home rig (192.168.0.x)",
                "description": "Tapo cams/plugs, Hue, optional Ring/HA — discovery on by default",
            },
            {
                "id": "generic",
                "label": "Generic LAN",
                "description": "Placeholder IPs with broadcast discovery",
            },
            {"id": "off", "label": "Empty", "description": "No default devices"},
        ],
        "vienna_device_count": len(resolve_preset_config("vienna").get("cameras", {}))
        + len((resolve_preset_config("vienna").get("energy") or {}).get("tapo_p115", {}).get("devices", [])),
    }
