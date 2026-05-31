"""Build live device inventory text for LLM chat system prompts."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

SYSTEM_PREAMBLE = """You are the assistant for the user's Devices MCP smart home dashboard.
Answer questions about their devices using the LIVE HOME INVENTORY below.
If asked what cameras, lights, plugs, or sensors they have, list them from the inventory.
Be concise. If something is marked offline or not connected, say so.
Do not invent devices not listed below."""


async def build_device_context_snapshot() -> str:
    """Return system-message body: preamble + live inventory sections."""
    sections: list[str] = [SYSTEM_PREAMBLE, "", "## LIVE HOME INVENTORY", ""]

    sections.extend(await _section_cameras())
    sections.extend(_section_from_config())
    sections.extend(await _section_live_status())

    return "\n".join(sections).strip()


async def _section_cameras() -> list[str]:
    lines = ["### Cameras"]
    try:
        from devices_mcp.core.server import DevicesMCPServer

        server = await asyncio.wait_for(DevicesMCPServer.get_instance(), timeout=5.0)
        cameras = await asyncio.wait_for(server.camera_manager.list_cameras(), timeout=5.0)
        if not cameras:
            lines.append("- (none discovered yet — check config.yaml cameras section)")
        for cam in cameras:
            name = cam.get("name") or cam.get("id") or "unknown"
            ctype = cam.get("type", "unknown")
            status = cam.get("status")
            if isinstance(status, dict):
                online = status.get("connected", status.get("online"))
            else:
                online = status == "online"
            state = "online" if online else "offline"
            host = cam.get("host") or (cam.get("params") or {}).get("host")
            extra = f", host {host}" if host else ""
            lines.append(f"- **{name}** ({ctype}, {state}{extra})")
    except Exception as e:
        logger.debug("Camera inventory for chat skipped: %s", e)
        lines.append(f"- (camera list unavailable: {e})")
    lines.append("")
    return lines


def _section_from_config() -> list[str]:
    from devices_mcp.config import get_config

    raw = get_config() or {}
    lines: list[str] = []

    # Config-only camera entries (when manager not ready)
    cameras_cfg = raw.get("cameras") or {}
    if cameras_cfg:
        lines.append("### Cameras (configured)")
        for cam_id, cam in cameras_cfg.items():
            if not isinstance(cam, dict):
                continue
            ctype = cam.get("type", "unknown")
            host = (cam.get("params") or {}).get("host") or cam.get("host")
            lines.append(f"- **{cam_id}** ({ctype}{f', {host}' if host else ''})")
        lines.append("")

    energy = (raw.get("energy") or {}).get("tapo_p115") or {}
    devices = energy.get("devices") or []
    if devices:
        lines.append("### Tapo P115 smart plugs")
        for d in devices:
            if not isinstance(d, dict):
                continue
            name = d.get("name") or d.get("device_id")
            loc = d.get("location")
            host = d.get("host")
            lines.append(f"- **{name}** ({d.get('device_id')}{f', {loc}' if loc else ''}{f', {host}' if host else ''})")
        lines.append("")

    hue = (raw.get("lighting") or {}).get("philips_hue") or {}
    if hue.get("enabled") is not False and hue.get("bridge_ip"):
        lines.append("### Philips Hue")
        lines.append(f"- Bridge at **{hue.get('bridge_ip')}** (Bridge Pro uses HTTPS)")
        lines.append("")

    netatmo = ((raw.get("weather") or {}).get("integrations") or {}).get("netatmo") or {}
    if netatmo.get("enabled"):
        lines.append("### Netatmo weather")
        lines.append("- Enabled in config (OAuth / refresh token)")
        lines.append("")

    ring = raw.get("ring") or {}
    if ring.get("enabled"):
        lines.append("### Ring")
        lines.append("- Doorbell + alarm integration enabled")
        lines.append("")

    ha = ((raw.get("security") or {}).get("integrations") or {}).get("homeassistant") or {}
    if ha.get("enabled"):
        lines.append("### Nest Protect (via Home Assistant)")
        lines.append(f"- Home Assistant at **{ha.get('url', 'http://localhost:8123')}**")
        lines.append("")

    shelly = raw.get("shelly") or {}
    if shelly.get("enabled"):
        lines.append("### Shelly temperature sensors")
        for d in shelly.get("devices") or []:
            if isinstance(d, dict):
                lines.append(f"- **{d.get('name', d.get('ip'))}** ({d.get('ip')})")
        if not shelly.get("devices"):
            lines.append("- Enabled but no devices configured")
        lines.append("")

    robotics = raw.get("robotics_mcp") or {}
    if robotics.get("enabled"):
        lines.append("### Robots")
        for rid, robot in (robotics.get("devices") or {}).items():
            if isinstance(robot, dict):
                lines.append(f"- **{robot.get('name', rid)}** ({robot.get('type', 'robot')})")
        if robotics.get("yahboom_mcp_url"):
            lines.append(f"- Yahboom MCP: {robotics['yahboom_mcp_url']}")
        lines.append("")

    return lines


async def _section_live_status() -> list[str]:
    lines = ["### Integration status (live)"]

    async def _ring() -> str | None:
        try:
            from devices_mcp.integrations.ring_client import get_ring_client

            c = get_ring_client()
            if not c:
                return "Ring: not initialized"
            if c.is_initialized:
                return "Ring: connected"
            if c.is_2fa_pending:
                return "Ring: 2FA pending"
            return f"Ring: not connected ({c.last_error or 'unknown'})"
        except Exception:
            return None

    async def _netatmo() -> str | None:
        try:
            from devices_mcp.integrations.netatmo_client import NetatmoService

            svc = NetatmoService.get_existing_instance()
            if svc and svc.is_api_ready():
                return "Netatmo: connected"
            return "Netatmo: not connected"
        except Exception:
            return None

    async def _hue() -> str | None:
        try:
            from devices_mcp.tools.lighting.hue_tools import get_hue_manager

            mgr = get_hue_manager()
            if mgr.is_connected:
                return f"Hue: connected ({len(mgr.lights)} lights)"
            return "Hue: not connected"
        except Exception:
            return None

    results = await asyncio.gather(_ring(), _netatmo(), _hue(), return_exceptions=True)
    for r in results:
        if isinstance(r, str):
            lines.append(f"- {r}")
    lines.append("")
    return lines


def merge_device_context_into_messages(messages: list[dict[str, Any]], context: str) -> list[dict[str, Any]]:
    """Prepend or augment system message with device inventory."""
    out = [dict(m) for m in messages]
    if out and out[0].get("role") == "system":
        out[0]["content"] = context + "\n\n---\n\n" + str(out[0].get("content", ""))
    else:
        out.insert(0, {"role": "system", "content": context})
    return out
