"""
Health check API endpoints for connection supervisor.

Provides real-time device health status and connection monitoring.
"""

import logging
from typing import Any

from fastapi import APIRouter

from devices_mcp.core.connection_supervisor import get_supervisor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/connection-health")
async def get_connection_health() -> dict[str, Any]:
    """
    Get comprehensive device connection health status.

    Returns health for all devices: cameras, plugs, lights, weather, ring.
    Shows which devices are online/offline and error details.
    Triggers a fresh health check before returning data.
    """
    try:
        import asyncio

        supervisor = get_supervisor()
        # Trigger a fresh health check first (with timeout)
        try:
            await asyncio.wait_for(supervisor._check_all_devices(), timeout=10.0)
        except TimeoutError:
            logger.warning("Health check timed out, returning cached data")
        except Exception as e:
            logger.warning(f"Health check failed: {e}, returning cached data")

        from devices_mcp.config import get_config
        from devices_mcp.core.device_registry import build_device_inventory

        health = supervisor.get_health_summary()
        config = get_config() or {}
        inventory = build_device_inventory(config, health)
        health["devices_table"] = inventory.get("devices", [])
        health["home_preset"] = inventory.get("home_preset")
        return health
    except Exception as e:
        logger.exception("Error getting connection health")
        return {"error": str(e), "total_devices": 0, "online": 0, "offline": 0, "devices": []}


@router.get("/offline-devices")
async def get_offline_devices() -> dict[str, Any]:
    """Get list of currently offline devices."""
    try:
        supervisor = get_supervisor()
        offline = supervisor.get_offline_devices()

        return {
            "count": len(offline),
            "devices": [
                {
                    "name": h.name,
                    "type": h.device_type,
                    "error": h.last_error,
                    "error_count": h.error_count,
                    "last_success": h.last_success.isoformat() if h.last_success else None,
                }
                for h in offline
            ],
        }
    except Exception as e:
        logger.exception("Error getting offline devices")
        return {"count": 0, "devices": [], "error": str(e)}


@router.post("/trigger-health-check")
async def trigger_health_check() -> dict[str, Any]:
    """Manually trigger an immediate health check of all devices."""
    try:
        import asyncio

        supervisor = get_supervisor()
        # Add timeout to prevent hanging
        await asyncio.wait_for(supervisor._check_all_devices(), timeout=10.0)
        return {"success": True, "message": "Health check completed"}
    except TimeoutError:
        logger.warning("Health check trigger timed out")
        return {"success": False, "error": "Health check timed out"}
    except Exception as e:
        logger.exception("Error triggering health check")
        return {"success": False, "error": str(e)}
