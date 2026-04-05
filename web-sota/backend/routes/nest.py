"""
Nest Protect API endpoints.

Provides REST API for Nest Protect smoke/CO detectors via Home Assistant.
"""

import logging

from fastapi import APIRouter, HTTPException

from devices_mcp.integrations.homeassistant_client import get_homeassistant_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/nest", tags=["nest"])


@router.get("/status")
async def get_nest_status():
    """Get Nest Protect system status and all devices via Home Assistant."""
    client = get_homeassistant_client()

    if not client or not client.is_initialized:
        return {
            "initialized": False,
            "error": "Home Assistant not connected",
            "setup_instructions": [
                "1. Run: cd deploy/homeassistant && docker-compose up -d",
                "2. Open http://localhost:8123 and create account",
                "3. Add Nest integration (Settings > Devices > Add Integration)",
                "4. Sign in with Google account",
                "5. Create Long-Lived Access Token (Profile > Security)",
                "6. Add token to config.yaml under security.integrations.homeassistant.access_token",
                "7. Restart devices-mcp server",
            ],
        }

    return await client.get_nest_summary()


@router.get("/devices")
async def get_nest_devices():
    """Get all Nest Protect devices via Home Assistant."""
    client = get_homeassistant_client()
    if not client or not client.is_initialized:
        raise HTTPException(status_code=400, detail="Home Assistant not connected")

    devices = await client.get_nest_protect_devices()
    return {"devices": [d.to_dict() for d in devices]}


@router.get("/ha/status")
async def get_ha_status():
    """Check Home Assistant connection status."""
    client = get_homeassistant_client()

    if not client:
        return {"connected": False, "error": "Client not initialized"}

    if not client.is_initialized:
        return {"connected": False, "error": "Not connected to Home Assistant"}

    return {
        "connected": True,
        "url": client.base_url,
    }
