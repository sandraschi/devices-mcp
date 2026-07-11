"""
Sensor Health Scan Tool

Fleet-wide sensor health check: gathers all device readings (Netatmo indoor/outdoor/bathroom,
Tapo P115 energy plugs), checks against safety thresholds (CO2, temperature, humidity, battery,
power consumption), and returns a Prefab report card with per-zone OK/warning/danger status.
"""

import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.server import ToolResult
from prefab_ui import PrefabApp
from prefab_ui.components import H1, H2, Badge, Row, Separator, Span

logger = logging.getLogger(__name__)

_CO2_WARN = 1000
_CO2_DANGER = 2000
_TEMP_WARN = 35.0
_TEMP_DANGER = 40.0
_TEMP_LOW_WARN = 10.0
_TEMP_LOW_DANGER = 5.0
_HUMID_WARN = 70.0
_BATTERY_WARN = 20
_POWER_WARN = 1000.0
_POWER_DANGER = 2000.0


def _check_temp(value: float | None) -> tuple[str, str]:
    if value is None:
        return "unknown", "N/A"
    if value >= _TEMP_DANGER:
        return "danger", f"{value:.1f}°C"
    if value >= _TEMP_WARN:
        return "warning", f"{value:.1f}°C"
    if value <= _TEMP_LOW_DANGER:
        return "danger", f"{value:.1f}°C"
    if value <= _TEMP_LOW_WARN:
        return "warning", f"{value:.1f}°C"
    return "ok", f"{value:.1f}°C"


def _check_co2(value: float | None) -> tuple[str, str]:
    if value is None:
        return "unknown", "N/A"
    if value >= _CO2_DANGER:
        return "danger", f"{value:.0f} ppm"
    if value >= _CO2_WARN:
        return "warning", f"{value:.0f} ppm"
    return "ok", f"{value:.0f} ppm"


def _check_humidity(value: float | None) -> tuple[str, str]:
    if value is None:
        return "unknown", "N/A"
    if value >= _HUMID_WARN:
        return "warning", f"{value:.0f}%"
    return "ok", f"{value:.0f}%"


def _check_battery(value: float | None) -> tuple[str, str]:
    if value is None:
        return "unknown", "N/A"
    if value <= _BATTERY_WARN:
        return "warning", f"{value:.0f}%"
    return "ok", f"{value:.0f}%"


def _check_power(value: float | None) -> tuple[str, str]:
    if value is None:
        return "unknown", "N/A"
    if value >= _POWER_DANGER:
        return "danger", f"{value:.0f} W"
    if value >= _POWER_WARN:
        return "warning", f"{value:.0f} W"
    return "ok", f"{value:.0f} W"


_VARIANT_MAP = {
    "ok": "success",
    "warning": "warning",
    "danger": "destructive",
    "unknown": "secondary",
}


def _badge(status: str, label: str) -> Badge:
    return Badge(label, variant=_VARIANT_MAP.get(status, "default"))


def _add_zone(app: PrefabApp, name: str, sensors: dict[str, Any]) -> None:
    H2(name)
    for label, value_fn, check_fn, skip_condition in [
        ("Temperature", lambda d: d.get("temperature"), _check_temp, lambda d: False),
        ("Humidity", lambda d: d.get("humidity"), _check_humidity, lambda d: False),
        ("CO\u2082", lambda d: d.get("co2"), _check_co2, lambda d: False),
        ("Power", lambda d: d.get("power"), _check_power, lambda d: d.get("power") is None),
        (
            "Battery",
            lambda d: d.get("battery_percent") or d.get("battery"),
            _check_battery,
            lambda d: d.get("battery") is None and d.get("battery_percent") is None,
        ),
    ]:
        if skip_condition(sensors):
            continue
        raw = value_fn(sensors)
        status, display = check_fn(raw)
        Row(children=[Span(f"{label}: {display}"), _badge(status, status.upper())])


def register_sensor_health_tool(mcp: FastMCP) -> None:
    """Register the sensor health scan tool."""

    @mcp.tool()
    async def sensor_health_scan() -> dict[str, Any]:
        """
        Fleet-wide sensor health check across all connected devices.

        Gathers temperature, CO2, humidity, and battery readings from Netatmo modules
        plus power readings from Tapo P115 energy plugs, and flags any values outside
        safe thresholds.

        Thresholds:
          - CO2: >= 1000ppm warning, >= 2000ppm danger
          - Temperature: >= 35C or <= 10C warning, >= 40C or <= 5C danger
          - Humidity: >= 70% warning
          - Battery: <= 20% warning
          - Power: >= 1000W warning (e.g. oven/microwave sustained high draw), >= 2000W danger

        Returns:
            A Prefab report card with per-zone status and a plain-text summary.
        """
        try:
            modules = await _fetch_modules()

            ok_count = 0
            warn_count = 0
            danger_count = 0
            zone_statuses: list[tuple[str, str, str]] = []

            with PrefabApp(title="Sensor Health Report") as app:
                H1("Sensor Health Report")
                Separator()

                for key, zone in sorted(modules.items()):
                    name = zone.get("name", key)
                    sensors = {
                        "temperature": zone.get("temperature"),
                        "humidity": zone.get("humidity"),
                        "co2": zone.get("co2"),
                        "battery": zone.get("battery"),
                        "battery_percent": zone.get("battery_percent"),
                    }

                    statuses = []
                    temp_s, _ = _check_temp(sensors["temperature"])
                    statuses.append(temp_s)
                    co2_s, _ = _check_co2(sensors["co2"])
                    statuses.append(co2_s)
                    hum_s, _ = _check_humidity(sensors["humidity"])
                    statuses.append(hum_s)
                    bat_s, _ = _check_battery(sensors.get("battery") or sensors.get("battery_percent"))
                    if sensors.get("battery") is not None or sensors.get("battery_percent") is not None:
                        statuses.append(bat_s)

                    zone_status = "ok"
                    if "danger" in statuses:
                        zone_status = "danger"
                    elif "warning" in statuses:
                        zone_status = "warning"

                    zone_statuses.append((name, zone_status, ", ".join(s for s in statuses if s != "ok")))
                    if zone_status == "ok":
                        ok_count += 1
                    elif zone_status == "warning":
                        warn_count += 1
                    else:
                        danger_count += 1

                    _add_zone(app, name, sensors)
                    Separator()

                H1(f"Summary: {ok_count} OK, {warn_count} Warnings, {danger_count} Dangers")

            plain_lines = [f"Sensor Health Report — {ok_count} OK, {warn_count} Warnings, {danger_count} Dangers"]
            for name, zs, issues in zone_statuses:
                icon = {"ok": "✓", "warning": "⚠", "danger": "✗"}.get(zs, "?")
                if issues:
                    plain_lines.append(f"  {icon} {name}: {issues}")
                else:
                    plain_lines.append(f"  {icon} {name}: all clear")

            return ToolResult(
                content="\n".join(plain_lines),
                structured_content=app.model_dump(),
            )

        except Exception as e:
            logger.exception("Sensor health scan failed")
            return {
                "success": False,
                "error": str(e),
                "message": f"Sensor health scan failed: {e!s}",
            }


async def _fetch_modules() -> dict[str, Any]:
    modules: dict[str, Any] = {}
    await _fetch_netatmo_modules(modules)
    await _fetch_energy_plugs(modules)
    return modules


async def _fetch_netatmo_modules(modules: dict[str, Any]) -> None:
    from devices_mcp.tools.weather.netatmo_weather_tool import NetatmoWeatherTool

    tool = NetatmoWeatherTool()
    station_id = await _primary_netatmo_station_id()
    result = await tool.execute(operation="data", station_id=station_id)
    if not result.get("success"):
        return

    wd = result.get("weather_data") or {}

    indoor = wd.get("indoor")
    if indoor and indoor.get("temperature") is not None:
        modules["indoor"] = {
            "name": "Indoor",
            "temperature": indoor.get("temperature"),
            "humidity": indoor.get("humidity"),
            "co2": indoor.get("co2"),
            "pressure": indoor.get("pressure"),
        }

    outdoor = wd.get("outdoor")
    if outdoor and outdoor.get("temperature") is not None:
        modules["outdoor"] = {
            "name": "Outdoor",
            "temperature": outdoor.get("temperature"),
            "humidity": outdoor.get("humidity"),
        }

    extra = wd.get("extra_indoor")
    if extra:
        extras = extra if isinstance(extra, list) else [extra]
        for ex in extras:
            if ex.get("temperature") is not None:
                ename = ex.get("name", "Extra")
                key = f"extra_{ename.lower().replace(' ', '_')}"
                modules[key] = {
                    "name": str(ename).title(),
                    "temperature": ex.get("temperature"),
                    "humidity": ex.get("humidity"),
                    "co2": ex.get("co2"),
                    "battery": ex.get("battery_percent") or ex.get("battery"),
                }


async def _fetch_energy_plugs(modules: dict[str, Any]) -> None:
    try:
        from devices_mcp.tools.energy.energy_management_tool import EnergyManagementTool

        tool = EnergyManagementTool()
        result = await tool.execute(operation="status")
        devices = result.get("devices") or []
        for d in devices:
            plug_id = d.get("device_id") or d.get("id", "plug")
            name = d.get("name") or d.get("alias") or plug_id
            power = d.get("current_power")
            if power is not None:
                key = f"plug_{plug_id}"
                modules[key] = {
                    "name": f"Plug: {name}",
                    "power": float(power),
                }
    except Exception:
        logger.debug("Energy plug data unavailable", exc_info=True)


async def _primary_netatmo_station_id() -> str | None:
    try:
        from devices_mcp.integrations.netatmo_client import NetatmoService

        svc = await NetatmoService.get_instance()
        stations = await svc.list_stations()
        if stations:
            sid = stations[0].get("station_id")
            return str(sid) if sid else None
    except Exception:
        pass
    return None
