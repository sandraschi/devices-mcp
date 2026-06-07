"""Fleet priority incidents API — Fritz urgent linkage."""

import logging

from fastapi import APIRouter, Query

from devices_mcp.integrations.fritz_priority import collect_priority_incidents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/fleet", tags=["fleet-priority"])


@router.get("/priority")
async def get_fleet_priority(
    ring_window_minutes: int = Query(30, ge=5, le=180, description="Ring events lookback"),
):
    """
    Aggregated home-security priority incidents for Fritz.

    Covers: Shelly temperature (kitchen/freezer), Nest CO/smoke, Ring burglar events,
    unacknowledged device alarm messages.
    """
    try:
        return await collect_priority_incidents(ring_window_minutes=ring_window_minutes)
    except Exception as exc:
        logger.exception("Fleet priority scan failed")
        return {
            "success": False,
            "healthy": False,
            "error": str(exc),
            "incidents": [],
            "incident_count": 0,
            "critical_count": 0,
        }
