"""
Aggregate home-security priority incidents for Fritz / fleet urgent dispatch.

Sources: Shelly temperature thresholds, Nest CO/smoke (HA), Ring alarm events,
in-app unacknowledged alarm messages.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Absolute kitchen / appliance danger (°C) — e.g. freezer failure, runaway heat
_KITCHEN_ABSOLUTE_HIGH_C = 45.0
_RING_INTRUSION_KEYWORDS = (
    "contact",
    "motion",
    "entry",
    "opened",
    "intrusion",
    "break",
    "alarm",
    "sensor",
)


def _urgency_for_temp(sensor: dict[str, Any]) -> float:
    temp = float(sensor.get("temperature_c") or 0)
    name = (sensor.get("name") or sensor.get("device_name") or "").lower()
    high = sensor.get("high_threshold_c")
    low = sensor.get("low_threshold_c")

    if temp >= _KITCHEN_ABSOLUTE_HIGH_C or ("kitchen" in name and temp >= 40.0):
        return min(10.0, 8.5 + (temp - 40.0) * 0.1)

    if sensor.get("alert_active"):
        if high is not None and temp >= float(high):
            over = temp - float(high)
            return min(10.0, 8.0 + over * 0.2)
        if low is not None and temp <= float(low):
            under = float(low) - temp
            return min(9.5, 7.5 + under * 0.15)
        return 8.0
    return 0.0


def _nest_incidents(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in devices:
        name = d.get("name") or d.get("friendly_name") or "Nest Protect"
        loc = d.get("location") or ""
        co = (d.get("co_status") or "idle").lower()
        smoke = (d.get("smoke_status") or "idle").lower()

        if co in ("emergency", "warning"):
            out.append(
                {
                    "id": f"nest-co-{d.get('entity_id', name)}",
                    "kind": "co_alarm",
                    "source": "nest_protect",
                    "title": f"CO alert — {name}",
                    "description": f"CO status: {co}" + (f" ({loc})" if loc else ""),
                    "urgency": 10.0 if co == "emergency" else 9.0,
                    "critical": co == "emergency",
                    "location": loc,
                    "raw": d,
                }
            )
        if smoke in ("emergency", "warning"):
            out.append(
                {
                    "id": f"nest-smoke-{d.get('entity_id', name)}",
                    "kind": "smoke_alarm",
                    "source": "nest_protect",
                    "title": f"Smoke alert — {name}",
                    "description": f"Smoke status: {smoke}" + (f" ({loc})" if loc else ""),
                    "urgency": 10.0 if smoke == "emergency" else 9.0,
                    "critical": smoke == "emergency",
                    "location": loc,
                    "raw": d,
                }
            )
    return out


def _shelly_incidents(sensors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for s in sensors:
        urgency = _urgency_for_temp(s)
        if urgency < 8.0 and not s.get("alert_active"):
            continue
        if urgency < 8.0:
            urgency = 8.0
        temp = s.get("temperature_c")
        name = s.get("name") or s.get("device_name") or "sensor"
        out.append(
            {
                "id": f"shelly-temp-{s.get('id', name)}",
                "kind": "temperature",
                "source": "shelly",
                "title": f"Temperature alert — {name}",
                "description": f"{temp}°C (threshold breach)" if temp is not None else "Threshold breach",
                "urgency": urgency,
                "critical": urgency >= 9.5,
                "location": name,
                "raw": s,
            }
        )
    return out


def _ring_incidents(events: list[dict[str, Any]], *, minutes: int = 30) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    for ev in events:
        kind = (ev.get("event_type") or "").lower()
        if not any(k in kind for k in _RING_INTRUSION_KEYWORDS):
            continue
        ts_raw = ev.get("timestamp") or ""
        try:
            ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            if ts < cutoff:
                continue
        except (ValueError, TypeError):
            pass

        device = ev.get("device_name") or "Ring sensor"
        out.append(
            {
                "id": f"ring-{ev.get('id', kind)}",
                "kind": "burglar_alarm",
                "source": "ring",
                "title": f"Ring alarm — {device}",
                "description": f"Event: {kind}",
                "urgency": 9.5,
                "critical": True,
                "location": device,
                "raw": ev,
            }
        )
    return out


def _message_incidents(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        sev = (m.get("severity") or "").lower()
        if sev != "alarm":
            continue
        out.append(
            {
                "id": f"msg-{m.get('id', m.get('timestamp', 'x'))}",
                "kind": "device_alarm",
                "source": m.get("source") or "devices-mcp",
                "title": m.get("title") or "Device alarm",
                "description": (m.get("description") or "")[:300],
                "urgency": 8.5,
                "critical": True,
                "location": m.get("source") or "",
                "raw": m,
            }
        )
    return out


async def collect_priority_incidents(
    *,
    ring_window_minutes: int = 30,
) -> dict[str, Any]:
    """Gather all priority incidents from configured integrations."""
    incidents: list[dict[str, Any]] = []
    sources_ok: dict[str, bool] = {}

    # Shelly temperatures
    try:
        from devices_mcp.integrations.shelly_client import get_shelly_client

        client = get_shelly_client()
        if client and client.is_initialized:
            sensors = await client.get_all_temperatures()
            sensor_dicts = [s.to_dict() for s in sensors]
            incidents.extend(_shelly_incidents(sensor_dicts))
            sources_ok["shelly"] = True
        else:
            sources_ok["shelly"] = False
    except Exception as exc:
        logger.debug("Shelly priority scan failed: %s", exc)
        sources_ok["shelly"] = False

    # Nest via Home Assistant
    try:
        from devices_mcp.integrations.homeassistant_client import get_homeassistant_client

        ha = get_homeassistant_client()
        if ha and ha.is_initialized:
            devices = await ha.get_nest_protect_devices()
            incidents.extend(_nest_incidents([d.to_dict() for d in devices]))
            sources_ok["nest"] = True
        else:
            sources_ok["nest"] = False
    except Exception as exc:
        logger.debug("Nest priority scan failed: %s", exc)
        sources_ok["nest"] = False

    # Ring alarm events
    try:
        from devices_mcp.integrations.ring_client import get_ring_client

        ring = get_ring_client("default")
        if ring and ring.is_initialized:
            events = await ring.get_alarm_events(limit=30)
            incidents.extend(_ring_incidents(events, minutes=ring_window_minutes))
            sources_ok["ring"] = True
        else:
            sources_ok["ring"] = False
    except Exception as exc:
        logger.debug("Ring priority scan failed: %s", exc)
        sources_ok["ring"] = False

    # In-app alarm queue
    try:
        from devices_mcp.core.messaging_service import get_messaging_service

        messaging = get_messaging_service()
        alarms = messaging.get_unacknowledged_alarms()
        incidents.extend(_message_incidents([a.to_dict() for a in alarms]))
        sources_ok["messages"] = True
    except Exception as exc:
        logger.debug("Messages priority scan failed: %s", exc)
        sources_ok["messages"] = False

    incidents.sort(key=lambda i: float(i.get("urgency") or 0), reverse=True)
    critical = [i for i in incidents if i.get("critical")]
    highest = float(incidents[0]["urgency"]) if incidents else 0.0

    return {
        "success": True,
        "timestamp": datetime.now(UTC).isoformat(),
        "incident_count": len(incidents),
        "critical_count": len(critical),
        "highest_urgency": highest,
        "healthy": len(critical) == 0,
        "incidents": incidents,
        "sources": sources_ok,
    }
