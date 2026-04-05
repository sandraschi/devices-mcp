from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter

from devices_mcp.config import get_model
from devices_mcp.config.models import SecuritySettings
from devices_mcp.core.server import DevicesMCPServer
from devices_mcp.security.integrations import SecurityIntegrationManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/security", tags=["security"])

# Global security manager instance
_security_manager: SecurityIntegrationManager | None = None


async def _get_security_manager() -> SecurityIntegrationManager:
    """Get or create security integration manager."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityIntegrationManager()
        cfg = get_model(SecuritySettings)
        await _security_manager.initialize(cfg.integrations.model_dump())
    return _security_manager


async def _compute_ring_status() -> Dict[str, Any]:
    """Get real Ring device status with battery monitoring."""
    cfg = get_model(SecuritySettings)
    enabled = bool(cfg.integrations.ring_mcp.get("enabled", False))

    devices: list[Dict[str, Any]] = []
    battery_warnings = 0
    battery_critical = 0

    if enabled:
        try:
            # Try to get Ring devices from camera manager
            server = await DevicesMCPServer.get_instance()
            if hasattr(server, "camera_manager") and server.camera_manager:
                cameras = await server.camera_manager.list_cameras()
                ring_cameras = [c for c in cameras if c.get("type") == "ring"]
                for cam in ring_cameras:
                    status_dict = cam.get("status", {})
                    if isinstance(status_dict, dict):
                        # Get detailed camera info including battery
                        camera_info = cam.get("info", {})
                        battery_life = camera_info.get("battery_life")
                        battery_level = None
                        battery_status = "unknown"
                        is_charging = False

                        if battery_life is not None:
                            # battery_life can be a percentage (0-100) or "ok"/"low" string
                            if isinstance(battery_life, (int, float)):
                                battery_level = int(battery_life)
                                if battery_level <= 20:
                                    battery_status = "critical"
                                    battery_critical += 1
                                elif battery_level <= 40:
                                    battery_status = "low"
                                    battery_warnings += 1
                                else:
                                    battery_status = "good"
                            elif isinstance(battery_life, str):
                                battery_status = battery_life.lower()
                                if battery_status == "low":
                                    battery_warnings += 1
                                elif battery_status in ("critical", "dead"):
                                    battery_critical += 1

                        # Check if device is charging (if available in health data)
                        health_data = camera_info.get("health", {})
                        if isinstance(health_data, dict):
                            is_charging = health_data.get("charging", False) or health_data.get(
                                "powered", False
                            )

                        devices.append(
                            {
                                "device_id": cam.get("name", ""),
                                "name": cam.get("name", ""),
                                "type": "doorbell",
                                "status": "online" if status_dict.get("connected") else "offline",
                                "location": "Unknown",
                                "battery_level": battery_level,
                                "battery_life": battery_life,
                                "battery_status": battery_status,
                                "is_charging": is_charging,
                                "model": camera_info.get("model", "Unknown"),
                            }
                        )
        except Exception:
            logger.exception("Failed to get Ring devices")

    devices_total = len(devices)
    health = {
        "ok": True,
        "msg": f"Ring integration: {devices_total} devices",
        "battery_warnings": battery_warnings,
        "battery_critical": battery_critical,
    }
    summary = {
        "enabled": enabled,
        "devices_total": devices_total,
        "battery_warnings": battery_warnings,
        "battery_critical": battery_critical,
    }
    return {
        "enabled": enabled,
        "devices_total": devices_total,
        "devices": devices,
        "health": health,
        "summary": summary,
    }


async def _compute_nest_status() -> Dict[str, Any]:
    """Get real Nest Protect device status with battery monitoring."""
    cfg = get_model(SecuritySettings)
    enabled = bool(cfg.integrations.nest_protect.get("enabled", False))

    devices: list[Dict[str, Any]] = []
    battery_warnings = 0
    battery_critical = 0

    if enabled:
        try:
            manager = await _get_security_manager()
            nest_devices = await manager.get_all_devices()
            for device in nest_devices:
                battery_level = device.battery_level
                battery_status = "unknown"

                # Determine battery status from level
                if battery_level is not None:
                    if battery_level <= 20:
                        battery_status = "critical"
                        battery_critical += 1
                    elif battery_level <= 40:
                        battery_status = "low"
                        battery_warnings += 1
                    else:
                        battery_status = "good"

                devices.append(
                    {
                        "device_id": device.id,
                        "name": device.name,
                        "type": device.type,
                        "status": device.status,
                        "location": device.location,
                        "battery_level": battery_level,
                        "battery_status": battery_status,
                        "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                    }
                )
        except Exception:
            logger.exception("Failed to get Nest Protect devices")

    devices_total = len(devices)
    health = {
        "ok": True,
        "msg": f"Nest Protect: {devices_total} devices" if enabled else "Nest Protect disabled",
        "battery_warnings": battery_warnings,
        "battery_critical": battery_critical,
    }
    summary = {
        "enabled": enabled,
        "devices_total": devices_total,
        "battery_warnings": battery_warnings,
        "battery_critical": battery_critical,
    }
    return {
        "enabled": enabled,
        "devices_total": devices_total,
        "devices": devices,
        "health": health,
        "summary": summary,
    }


@router.get("/ring/status", summary="Get Ring integration status")
async def get_ring_status() -> Dict[str, Any]:
    return await _compute_ring_status()


@router.get("/nest/status", summary="Get Nest Protect integration status")
async def get_nest_status() -> Dict[str, Any]:
    return await _compute_nest_status()


@router.get("/nest/devices", summary="Get all Nest Protect devices")
async def get_nest_devices() -> Dict[str, Any]:
    """Get all Nest Protect devices with detailed status."""
    try:
        from devices_mcp.integrations.nest_client import get_nest_client

        client = get_nest_client()
        if not client or not client.is_initialized:
            # Fallback to security manager
            try:
                manager = await _get_security_manager()
                devices = await manager.get_all_devices()
                return {
                    "devices": [
                        device.to_dict()
                        if hasattr(device, "to_dict")
                        else {
                            "device_id": getattr(device, "id", ""),
                            "name": getattr(device, "name", ""),
                            "type": getattr(device, "type", "protect"),
                            "status": getattr(device, "status", "unknown"),
                            "location": getattr(device, "location", "Unknown"),
                            "battery_level": getattr(device, "battery_level", None),
                            "battery_status": getattr(device, "battery_status", "unknown"),
                            "last_seen": getattr(device, "last_seen", None),
                        }
                        for device in devices
                    ],
                    "count": len(devices),
                }
            except Exception:
                return {"devices": [], "count": 0, "message": "Nest client not initialized"}

        devices = await client.get_devices()
        return {
            "devices": [device.to_dict() for device in devices],
            "count": len(devices),
        }
    except Exception as e:
        logger.exception("Failed to get Nest Protect devices")
        return {"devices": [], "count": 0, "error": str(e)}


@router.get("/nest/alerts", summary="Get Nest Protect alerts")
async def get_nest_alerts() -> Dict[str, Any]:
    """Get active alerts from Nest Protect devices (smoke, CO, offline)."""
    try:
        from devices_mcp.integrations.nest_client import get_nest_client

        client = get_nest_client()
        if not client or not client.is_initialized:
            return {
                "alerts": [],
                "total_alerts": 0,
                "active_alerts": 0,
                "message": "Nest client not initialized",
            }

        devices = await client.get_devices()
        alerts = []

        for device in devices:
            # Check smoke status
            if device.smoke_status.value != "ok":
                alerts.append(
                    {
                        "device_id": device.device_id,
                        "device_name": device.name,
                        "location": device.location,
                        "type": "smoke",
                        "status": device.smoke_status.value,
                        "severity": "emergency"
                        if device.smoke_status.value == "emergency"
                        else "warning",
                    }
                )

            # Check CO status
            if device.co_status.value != "ok":
                alerts.append(
                    {
                        "device_id": device.device_id,
                        "device_name": device.name,
                        "location": device.location,
                        "type": "co",
                        "status": device.co_status.value,
                        "severity": "emergency"
                        if device.co_status.value == "emergency"
                        else "warning",
                    }
                )

            # Check if offline
            if not device.is_online:
                alerts.append(
                    {
                        "device_id": device.device_id,
                        "device_name": device.name,
                        "location": device.location,
                        "type": "offline",
                        "status": "offline",
                        "severity": "warning",
                    }
                )

            # Check battery health
            if device.battery_health != "ok":
                alerts.append(
                    {
                        "device_id": device.device_id,
                        "device_name": device.name,
                        "location": device.location,
                        "type": "battery",
                        "status": device.battery_health,
                        "severity": "warning",
                    }
                )

        return {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "active_alerts": len([a for a in alerts if a["severity"] == "emergency"]),
            "warnings": len([a for a in alerts if a["severity"] == "warning"]),
        }
    except Exception as e:
        logger.exception("Failed to get Nest Protect alerts")
        return {"alerts": [], "total_alerts": 0, "error": str(e)}


@router.get("/nest/summary", summary="Get Nest Protect summary")
async def get_nest_summary() -> Dict[str, Any]:
    """Get comprehensive Nest Protect summary."""
    try:
        from devices_mcp.integrations.nest_client import get_nest_client

        client = get_nest_client()
        if not client or not client.is_initialized:
            # Fallback to security manager status
            status = await _compute_nest_status()
            return {
                "initialized": status.get("enabled", False),
                "total_devices": status.get("devices_total", 0),
                "devices": status.get("devices", []),
                "message": "Using security manager"
                if status.get("enabled")
                else "Nest client not initialized",
            }

        summary = await client.get_summary()
        return {
            "initialized": True,
            **summary,
        }
    except Exception as e:
        logger.exception("Failed to get Nest Protect summary")
        return {
            "initialized": False,
            "error": str(e),
        }
