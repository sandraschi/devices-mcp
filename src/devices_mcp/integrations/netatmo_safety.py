"""Netatmo smoke + CO alarm readout (raw API, defensive parsing).

pyatmo 8.1 wraps weather stations only - smoke detectors and CO alarms are not
modelled. Netatmo's own API exposes them in the same home (homesdata modules +
getevents), reachable with the OAuth tokens the NetatmoService already holds.

Design notes (read before "fixing" this file):
- Module/event type strings for smoke + CO are NOT hardcoded to an allow-list.
  Anything that is not a known weather type is surfaced in the ``other`` bucket
  and logged with its raw shape, so a new firmware or model never silently
  disappears. Keyword matching (smoke/co/carbon) only upgrades the label.
- Alarm state comes from recent events touching the module; a module with no
  events reports state "unknown", never "clear". Absence of evidence is not
  evidence of absence - the physical siren is the safety layer, this is the
  visibility layer.
- All HTTP goes through a private httpx client (never the shared aiohttp
  session) to avoid the loop-affinity crashes seen elsewhere.
"""

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_HOMESDATA_URL = "https://api.netatmo.com/api/homesdata"
_GETEVENTS_URL = "https://api.netatmo.com/api/getevents"

# Weather types we own elsewhere; everything else is safety-candidate until proven.
_WEATHER_TYPES = {
    "NAMain",
    "NAModule1",
    "NAModule2",
    "NAModule3",
    "NAModule4",
    "NAPlug",
    "NATherm1",
    "NAValve1",
    "NACamera",
    "NAPresence",
}

_SMOKE_HINTS = ("smoke", "nsd", "fum")
_CO_HINTS = ("carbon", "monoxide", "co_", "_co", "nac")


def _classify(module_type: str) -> str:
    lowered = (module_type or "").lower()
    if module_type in _WEATHER_TYPES:
        return "weather"
    if any(h in lowered for h in _SMOKE_HINTS):
        return "smoke"
    if any(h in lowered for h in _CO_HINTS):
        return "co"
    return "other"


async def _post(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post(url, data=payload, headers={"Authorization": f"Bearer {token}"})
        data = resp.json()
    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"Netatmo API error: {data['error']}")
    return data if isinstance(data, dict) else {}


async def fetch_safety_overview(access_token: str, home_id: str | None = None) -> dict[str, Any]:
    """Enumerate smoke/CO/other modules + recent alarm-ish events for a home.

    Returns {smoke: [...], co: [...], other: [...], recent_events: [...]} where
    each device row is {id, name, type, reachable, battery, last_seen, state}.
    ``state`` is "alarm" only on positive evidence, else "unknown"/"quiet".
    """
    homes_data = await _post(_HOMESDATA_URL, access_token, {})
    homes = ((homes_data.get("body") or {}).get("homes")) or []
    if home_id:
        homes = [h for h in homes if h.get("id") == home_id]
    overview: dict[str, Any] = {"smoke": [], "co": [], "other": [], "recent_events": []}

    for home in homes:
        hid = home.get("id", "")
        for module in home.get("modules", []) or []:
            if not isinstance(module, dict):
                continue
            mtype = str(module.get("type", ""))
            kind = _classify(mtype)
            if kind == "weather":
                continue
            row = {
                "id": module.get("id", ""),
                "name": module.get("name") or mtype or "Unnamed",
                "type": mtype,
                "reachable": module.get("reachable"),
                "battery": module.get("battery_level", module.get("battery")),
                "last_seen": module.get("last_seen"),
                "state": "unknown",
                "home_id": hid,
            }
            if kind == "other":
                logger.info("Netatmo non-weather module (tracked as other): %s", module)
            overview[kind].append(row)

    # Recent events (alarm evidence + expiry). Best effort; never fatal.
    event_types_seen: set[str] = set()
    for home in homes:
        hid = home.get("id", "")
        try:
            events_data = await _post(_GETEVENTS_URL, access_token, {"home_id": hid, "size": 30})
            events = ((events_data.get("body") or {}).get("events")) or []
        except Exception as e:
            logger.debug("Netatmo getevents failed for home %s: %s", hid, e)
            continue
        for event in events:
            if not isinstance(event, dict):
                continue
            etype = str(event.get("type", ""))
            event_types_seen.add(etype)
            lowered = etype.lower()
            is_alarm = any(k in lowered for k in ("alarm", "smoke", "carbon", "monoxide", "emergency", "trigger"))
            is_clear = any(k in lowered for k in ("ok", "clear", "resolved", "end"))
            overview["recent_events"].append(
                {
                    "type": etype,
                    "time": event.get("time"),
                    "module_id": event.get("module_id", ""),
                    "alarm": is_alarm and not is_clear,
                }
            )
            if is_alarm and not is_clear:
                mid = str(event.get("module_id", ""))
                for bucket in ("smoke", "co", "other"):
                    for row in overview[bucket]:
                        if row["id"] == mid or not mid:
                            row["state"] = "alarm"
    if event_types_seen:
        logger.debug("Netatmo event types seen: %s", sorted(event_types_seen))

    # Anything explicitly cleared back to quiet (only with positive evidence).
    for bucket in ("smoke", "co", "other"):
        for row in overview[bucket]:
            if row["state"] == "unknown" and row.get("reachable") is True:
                row["state"] = "quiet"
    overview["checked_at"] = int(time.time())
    return overview
