"""
Unified device registry: config + supervisor health + optional LAN discovery.

Powers GET /api/devices and the Health page device table.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _discovery_flags(config: dict[str, Any]) -> dict[str, bool]:
    disc = config.get("discovery") or {}
    enabled = disc.get("enabled", True)
    return {
        "tapo_p115": enabled and disc.get("tapo_p115", True),
        "usb_cameras": enabled and disc.get("usb_cameras", True),
        "philips_hue": enabled and disc.get("philips_hue", True),
        "tapo_lighting": enabled and disc.get("tapo_lighting", True),
        "ring": enabled and disc.get("ring", False),
        "shelly": enabled and disc.get("shelly", False),
    }


def _row(
    *,
    device_id: str,
    name: str,
    device_type: str,
    integration: str,
    address: str | None = None,
    source: str = "config",
    enabled: bool = True,
    connected: bool | None = None,
    last_error: str | None = None,
    last_check: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": device_id,
        "name": name,
        "type": device_type,
        "integration": integration,
        "address": address or "—",
        "source": source,
        "enabled": enabled,
        "connected": connected,
        "status": _status_label(connected, enabled, last_error),
        "last_error": last_error,
        "last_check": last_check,
        "details": details or {},
    }


def _status_label(connected: bool | None, enabled: bool, last_error: str | None) -> str:
    if not enabled:
        return "disabled"
    if connected is True:
        return "online"
    if connected is False:
        return "offline"
    if last_error:
        return "error"
    return "unknown"


def _health_index(health_devices: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_name_type: dict[str, dict[str, Any]] = {}
    for h in health_devices:
        did = h.get("device_id") or ""
        if did:
            by_id[did] = h
        key = f"{h.get('type', '')}:{h.get('name', '')}"
        by_name_type[key] = h
    return {"by_id": by_id, "by_name_type": by_name_type}


def _merge_health(row: dict[str, Any], health_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    h = health_index["by_id"].get(row["id"])
    if not h:
        h = health_index["by_name_type"].get(f"{row['type']}:{row['name']}")
    if not h:
        return row
    row = dict(row)
    row["connected"] = h.get("connected")
    row["last_error"] = h.get("last_error")
    row["last_check"] = h.get("last_check")
    row["status"] = _status_label(row["connected"], row["enabled"], row["last_error"])
    if h.get("details"):
        row["details"] = {**row.get("details", {}), **h["details"]}
    if row["source"] == "config" and h:
        row["source"] = "config+supervisor"
    return row


def list_configured_devices(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Enumerate devices declared in config.yaml (no live probe)."""
    rows: list[dict[str, Any]] = []
    preset = config.get("home_preset", "—")

    cameras = config.get("cameras") or {}
    if isinstance(cameras, dict):
        for name, cam in cameras.items():
            if not isinstance(cam, dict):
                continue
            host = cam.get("host")
            if not host and isinstance(cam.get("params"), dict):
                host = cam["params"].get("host")
            addr = host if host else f"device_id={cam.get('device_id', '?')}"
            rows.append(
                _row(
                    device_id=f"camera_{name}",
                    name=name,
                    device_type="camera",
                    integration=str(cam.get("type", "camera")),
                    address=str(addr),
                    details={"home_preset": preset, "config_key": f"cameras.{name}"},
                )
            )

    tapo_p115 = (config.get("energy") or {}).get("tapo_p115") or {}
    for plug in tapo_p115.get("devices") or []:
        if not isinstance(plug, dict):
            continue
        host = plug.get("host", "")
        did = plug.get("device_id") or f"plug_{host}"
        rows.append(
            _row(
                device_id=f"plug_{did}",
                name=plug.get("name") or did,
                device_type="plug",
                integration="tapo_p115",
                address=host,
                details={"location": plug.get("location"), "config_key": "energy.tapo_p115.devices"},
            )
        )

    hue = (config.get("lighting") or {}).get("philips_hue") or {}
    if hue.get("bridge_ip"):
        rows.append(
            _row(
                device_id="hue_bridge",
                name="Philips Hue Bridge",
                device_type="lighting",
                integration="philips_hue",
                address=str(hue.get("bridge_ip")),
                enabled=bool(hue.get("username") or hue.get("auto_discover")),
                details={"auto_discover": hue.get("auto_discover", False)},
            )
        )

    tapo_light = (config.get("lighting") or {}).get("tapo_lighting") or {}
    for light in tapo_light.get("devices") or []:
        if not isinstance(light, dict):
            continue
        host = light.get("host", "")
        did = light.get("device_id") or f"light_{host}"
        rows.append(
            _row(
                device_id=f"light_{did}",
                name=light.get("name") or did,
                device_type="light",
                integration="tapo_lighting",
                address=host,
            )
        )

    ring = config.get("ring") or {}
    if ring:
        rows.append(
            _row(
                device_id="ring_account",
                name="Ring",
                device_type="security",
                integration="ring",
                address="cloud",
                enabled=bool(ring.get("enabled")),
                details={"email_set": bool(ring.get("email"))},
            )
        )

    shelly = config.get("shelly") or {}
    if shelly.get("enabled"):
        for i, dev in enumerate(shelly.get("devices") or []):
            if not isinstance(dev, dict):
                continue
            host = dev.get("host") or dev.get("ip", "")
            name = dev.get("name") or f"Shelly {i + 1}"
            rows.append(
                _row(
                    device_id=f"shelly_{host or i}",
                    name=name,
                    device_type="sensor",
                    integration="shelly",
                    address=host or "—",
                )
            )
    elif shelly:
        rows.append(
            _row(
                device_id="shelly_integration",
                name="Shelly",
                device_type="sensor",
                integration="shelly",
                address="—",
                enabled=False,
            )
        )

    ha = ((config.get("security") or {}).get("integrations") or {}).get("homeassistant") or {}
    if ha.get("enabled") or ha.get("url"):
        rows.append(
            _row(
                device_id="nest_protect",
                name="Nest Protect (Home Assistant)",
                device_type="nest",
                integration="homeassistant",
                address=str(ha.get("url", "—")),
                enabled=bool(ha.get("enabled")),
            )
        )

    netatmo = ((config.get("weather") or {}).get("integrations") or {}).get("netatmo") or {}
    if netatmo.get("enabled"):
        rows.append(
            _row(
                device_id="netatmo",
                name="Netatmo Weather",
                device_type="weather",
                integration="netatmo",
                address="cloud",
                enabled=True,
            )
        )

    openmeteo = ((config.get("weather") or {}).get("integrations") or {}).get("openmeteo") or {}
    if openmeteo.get("enabled", True) and (openmeteo or config.get("home_preset") == "vienna"):
        rows.append(
            _row(
                device_id="openmeteo_vienna",
                name=openmeteo.get("location_name", "Open-Meteo (Vienna)"),
                device_type="weather",
                integration="openmeteo",
                address="api.open-meteo.com",
                enabled=bool(openmeteo.get("enabled", True)),
            )
        )

    vienna_cams = (config.get("public_webcams") or {}).get("vienna_webcams") or {}
    if vienna_cams.get("enabled"):
        rows.append(
            _row(
                device_id="vienna_public_webcams",
                name="Vienna public webcams",
                device_type="webcam",
                integration="public_feed",
                address=vienna_cams.get("region", "Wien"),
                enabled=True,
            )
        )

    for robot_id, robot in (config.get("robotics_mcp") or {}).get("devices", {}).items():
        if not isinstance(robot, dict):
            continue
        rows.append(
            _row(
                device_id=f"robot_{robot_id}",
                name=str(robot_id),
                device_type="robot",
                integration="robotics_mcp",
                address=str(robot.get("host", "—")),
                enabled=bool(robot.get("enabled")),
            )
        )

    return rows


async def discover_devices(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Run enabled discovery probes; return rows with source=discovered."""
    flags = _discovery_flags(config)
    discovered: list[dict[str, Any]] = []
    configured_hosts = {r.get("address") for r in list_configured_devices(config) if r.get("address")}

    if flags["tapo_p115"]:
        try:
            from ..ingest.tapo_p115 import TapoP115IngestionService

            svc = TapoP115IngestionService()
            for entry in await svc.discover_devices():
                host = str(entry.get("host") or entry.get("ip") or "")
                if not host or host in configured_hosts:
                    continue
                discovered.append(
                    _row(
                        device_id=f"discovered_plug_{host}",
                        name=str(entry.get("alias") or entry.get("name") or f"Tapo plug {host}"),
                        device_type="plug",
                        integration="tapo_p115",
                        address=host,
                        source="discovered",
                        connected=entry.get("online"),
                        details=entry,
                    )
                )
        except Exception as e:
            logger.warning("Tapo P115 discovery failed: %s", e)

    if flags["usb_cameras"]:
        try:
            from ..camera.manager import CameraManager

            mgr = CameraManager()
            await mgr.initialize(configs=None, auto_discover_usb=True)
            for cam in await mgr.list_cameras():
                if cam.get("type") not in ("webcam", "microscope", "usb"):
                    continue
                name = cam.get("name", "usb")
                did = f"camera_{name}"
                if any(d["id"] == did for d in discovered):
                    continue
                status = cam.get("status") or {}
                discovered.append(
                    _row(
                        device_id=did,
                        name=name,
                        device_type="camera",
                        integration=str(cam.get("type", "usb")),
                        address=f"USB #{status.get('device_id', '?')}",
                        source="discovered",
                        connected=status.get("connected") if isinstance(status, dict) else None,
                        details=status if isinstance(status, dict) else {},
                    )
                )
        except Exception as e:
            logger.debug("USB camera discovery skipped: %s", e)

    return discovered


def build_device_inventory(
    config: dict[str, Any],
    health_summary: dict[str, Any] | None = None,
    extra_discovered: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Merge config devices, supervisor health, and optional discoveries."""
    health_devices = (health_summary or {}).get("devices") or []
    health_index = _health_index(health_devices)

    rows = [_merge_health(r, health_index) for r in list_configured_devices(config)]

    seen_ids = {r["id"] for r in rows}
    for d in extra_discovered or []:
        if d["id"] not in seen_ids:
            rows.append(_merge_health(d, health_index))
            seen_ids.add(d["id"])

    for h in health_devices:
        hid = h.get("device_id") or ""
        if hid and hid not in seen_ids:
            rows.append(
                _row(
                    device_id=hid,
                    name=h.get("name", hid),
                    device_type=h.get("type", "unknown"),
                    integration=h.get("type", "unknown"),
                    address=h.get("details", {}).get("host") if isinstance(h.get("details"), dict) else "—",
                    source="supervisor",
                    connected=h.get("connected"),
                    last_error=h.get("last_error"),
                    last_check=h.get("last_check"),
                    details=h.get("details") or {},
                )
            )
            seen_ids.add(hid)

    rows.sort(key=lambda r: (r["type"], r["name"].lower()))

    online = sum(1 for r in rows if r.get("connected") is True)
    offline = sum(1 for r in rows if r.get("connected") is False)
    unknown = len(rows) - online - offline

    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r["type"]] = by_type.get(r["type"], 0) + 1

    return {
        "home_preset": config.get("home_preset"),
        "discovery": _discovery_flags(config),
        "total_devices": len(rows),
        "online": online,
        "offline": offline,
        "unknown": unknown,
        "by_type": by_type,
        "devices": rows,
    }
