"""Unified sensor registry — aggregates device counts from integrations."""

from __future__ import annotations

from typing import Any


async def get_sensor_overview() -> dict[str, Any]:
    """Return a cross-integration sensor summary for dashboards."""
    sources: list[dict[str, Any]] = []

    try:
        from devices_mcp.tools.energy.tapo_plug_tools import tapo_plug_manager

        devices = await tapo_plug_manager.get_all_devices()
        sources.append(
            {
                "id": "tapo_p115",
                "name": "Tapo P115",
                "type": "energy",
                "connected": len(devices) > 0,
                "count": len(devices),
            }
        )
    except Exception as e:
        sources.append({"id": "tapo_p115", "name": "Tapo P115", "type": "energy", "connected": False, "error": str(e)})

    try:
        from devices_mcp.integrations.shelly_client import get_shelly_client

        client = get_shelly_client()
        if client and client.is_initialized:
            summary = await client.get_summary()
            sources.append(
                {
                    "id": "shelly",
                    "name": "Shelly",
                    "type": "temperature",
                    "connected": True,
                    "count": summary.get("sensor_count", 0),
                    "alerts": summary.get("alert_count", 0),
                }
            )
        else:
            sources.append({"id": "shelly", "name": "Shelly", "type": "temperature", "connected": False, "count": 0})
    except Exception as e:
        sources.append({"id": "shelly", "name": "Shelly", "type": "temperature", "connected": False, "error": str(e)})

    try:
        from devices_mcp.integrations.homeassistant_client import get_homeassistant_client

        ha = get_homeassistant_client()
        if ha and ha.is_initialized:
            summary = await ha.get_nest_summary()
            sources.append(
                {
                    "id": "nest_protect",
                    "name": "Nest Protect",
                    "type": "smoke_co",
                    "connected": summary.get("initialized", False),
                    "count": summary.get("total_devices", 0),
                    "all_ok": summary.get("all_ok"),
                }
            )
        else:
            sources.append(
                {
                    "id": "nest_protect",
                    "name": "Nest Protect",
                    "type": "smoke_co",
                    "connected": False,
                    "count": 0,
                }
            )
    except Exception as e:
        sources.append(
            {
                "id": "nest_protect",
                "name": "Nest Protect",
                "type": "smoke_co",
                "connected": False,
                "error": str(e),
            }
        )

    try:
        from devices_mcp.integrations.ring_client import get_ring_client

        ring = get_ring_client()
        if ring and ring.is_initialized:
            summary = await ring.get_summary()
            alarm_total = (summary.get("alarm_devices") or {}).get("total", 0)
            sources.append(
                {
                    "id": "ring",
                    "name": "Ring",
                    "type": "security",
                    "connected": True,
                    "count": summary.get("doorbell_count", 0) + alarm_total,
                    "doorbells": summary.get("doorbell_count", 0),
                    "alarm_sensors": alarm_total,
                }
            )
        else:
            sources.append({"id": "ring", "name": "Ring", "type": "security", "connected": False, "count": 0})
    except Exception as e:
        sources.append({"id": "ring", "name": "Ring", "type": "security", "connected": False, "error": str(e)})

    connected = sum(1 for s in sources if s.get("connected"))
    return {
        "sources": sources,
        "total_sources": len(sources),
        "connected_sources": connected,
        "total_devices": sum(int(s.get("count") or 0) for s in sources),
    }
