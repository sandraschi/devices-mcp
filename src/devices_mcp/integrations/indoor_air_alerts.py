"""
Indoor air quality alerts (Netatmo CO₂) merged into the same Alert model as Vienna/Meteoalarm.

CO₂ is a leading indicator of poor ventilation; sustained high levels are a real health risk
in small, crowded spaces. Thresholds are conservative; tune via config later if needed.
"""

from __future__ import annotations

import logging
from datetime import datetime

from .vienna_alerts_client import Alert, AlertSeverity, AlertType

logger = logging.getLogger(__name__)

# ppm — advisory bands (not medical advice); align with common indoor-air guidance
_CO2_MINOR = 1000
_CO2_MODERATE = 1500
_CO2_SEVERE = 2000
_CO2_EXTREME = 2500


async def _primary_netatmo_station_id() -> str | None:
    try:
        from devices_mcp.config import get_config
        from .netatmo_client import NetatmoService

        raw = get_config()
        netatmo_cfg = ((raw.get("weather") or {}).get("integrations") or {}).get("netatmo") or {}
        preferred_id = str(netatmo_cfg.get("primary_station_id") or "").strip()
        preferred_name = str(netatmo_cfg.get("primary_station_name") or "").strip().lower()

        svc = await NetatmoService.get_instance()
        stations = await svc.list_stations()
        if not stations:
            return None

        if preferred_id:
            for s in stations:
                sid = s.get("station_id")
                if sid and str(sid) == preferred_id:
                    return str(sid)

        if preferred_name:
            for s in stations:
                name = str(s.get("station_name") or "")
                if preferred_name in name.lower():
                    sid = s.get("station_id")
                    return str(sid) if sid else None

        sid = stations[0].get("station_id")
        return str(sid) if sid else None
    except Exception:
        logger.debug("Could not resolve Netatmo station for CO₂ alert", exc_info=True)
        return None


def _co2_severity(ppm: float) -> AlertSeverity | None:
    if ppm < _CO2_MINOR:
        return None
    if ppm >= _CO2_EXTREME:
        return AlertSeverity.EXTREME
    if ppm >= _CO2_SEVERE:
        return AlertSeverity.SEVERE
    if ppm >= _CO2_MODERATE:
        return AlertSeverity.MODERATE
    return AlertSeverity.MINOR


async def get_netatmo_co2_alerts() -> list[Alert]:
    """
    If Netatmo indoor CO₂ is elevated, return one active Alert (same schema as weather alerts).

    Returns an empty list if Netatmo is off, fails, or CO₂ is below the warning band.
    """
    try:
        from ..tools.weather.netatmo_weather_tool import NetatmoWeatherTool

        station_id = await _primary_netatmo_station_id()
        tool = NetatmoWeatherTool()
        result = await tool.execute(operation="data", station_id=station_id)
        if not result.get("success"):
            return []

        wd = result.get("weather_data")
        if not isinstance(wd, dict):
            return []

        indoor = wd.get("indoor") or {}
        raw = indoor.get("co2")
        if raw is None:
            return []

        ppm = float(raw)
        severity = _co2_severity(ppm)
        if severity is None:
            return []

        sid = str(wd.get("station_id") or station_id or "indoor")
        label = sid[:24]

        titles = {
            AlertSeverity.MINOR: f"Indoor CO₂ elevated ({ppm:.0f} ppm)",
            AlertSeverity.MODERATE: f"High indoor CO₂ ({ppm:.0f} ppm) — ventilate",
            AlertSeverity.SEVERE: f"Very high indoor CO₂ ({ppm:.0f} ppm) — health risk",
            AlertSeverity.EXTREME: f"Extreme indoor CO₂ ({ppm:.0f} ppm) — ventilate now",
        }
        bodies = {
            AlertSeverity.MINOR: (
                "CO₂ above ~1000 ppm usually means stale air. Open a window or run "
                "mechanical ventilation; especially important with several people in a small flat."
            ),
            AlertSeverity.MODERATE: (
                "Sustained levels here often correlate with headaches, drowsiness, and reduced "
                "focus. This is not “just discomfort” — reduce occupancy duration and increase fresh air."
            ),
            AlertSeverity.SEVERE: (
                "Prolonged exposure at this level is a serious ventilation failure for a residential "
                "space. Prioritize cross-ventilation or exhaust; check that vents are not blocked."
            ),
            AlertSeverity.EXTREME: (
                "Treat as an urgent indoor-air emergency: ventilate immediately and limit time in "
                "the room until levels fall. Small flats with multiple occupants and no fresh air "
                "for days can reach this range."
            ),
        }

        now = datetime.now()
        return [
            Alert(
                id=f"netatmo_co2_{sid}",
                source="netatmo",
                alert_type=AlertType.AIR_QUALITY,
                severity=severity,
                title=titles[severity],
                description=bodies[severity],
                region=f"Indoor ({label})",
                start_time=None,
                end_time=None,
                issued_time=now,
                raw_data={"co2_ppm": ppm, "station_id": sid},
            )
        ]
    except Exception:
        logger.debug("Netatmo CO₂ alert skipped", exc_info=True)
        return []
