import asyncio
import inspect
import logging
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psutil
from fastapi import APIRouter, Request
from fastapi.responses import Response

from devices_mcp.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter()


async def _maybe_await(value):
    """Return awaited value when needed."""
    if inspect.isawaitable(value):
        return await value
    return value


def _is_portmanteau_tool_name(name: str) -> bool:
    """Heuristic classifier for portmanteau-style tool names."""
    return name.endswith("_management") or name in {
        "system_management",
        "camera_management",
        "lighting_management",
        "energy_management",
        "weather_management",
        "security_management",
        "ring_management",
        "media_management",
        "messages_management",
        "automation_management",
        "alerts_management",
        "analytics_management",
        "configuration_management",
        "robotics_management",
        "medical_management",
        "kitchen_management",
        "thermal_management",
        "motion_management",
        "audio_management",
        "dymo_management",
    }


@router.get("/api/status")
async def get_status(request: Request):
    """Get server status."""
    config = get_config()
    return {
        "status": "ok",
        "version": "1.0.0",
        "debug": config.get("debug", False),
    }


@router.get("/api/init-status")
async def get_init_status():
    """Expose DevicesMCPServer initialization state for webapp warmup UX.

    This endpoint must be safe to call during startup and MUST NOT trigger heavyweight init.
    """
    try:
        from devices_mcp.core.server import DevicesMCPServer

        return {
            "status": "ok",
            "server": "devices-mcp",
            "initialized": bool(getattr(DevicesMCPServer, "_initialized", False)),
            "initializing": bool(getattr(DevicesMCPServer, "_initializing", False)),
            "hardware_initialized": bool(getattr(DevicesMCPServer, "_hardware_initialized", False)),
        }
    except Exception as e:
        logger.exception("Failed to read init status")
        return {"status": "error", "error": str(e), "initialized": False, "initializing": False}


@router.get("/api/tools")
async def get_tools():
    """Expose the MCP tools registry for dynamic analysis."""
    try:
        from devices_mcp.core.server import DevicesMCPServer  # Use updated name

        server = await DevicesMCPServer.get_instance()

        mcp_tools = []
        if hasattr(server.mcp, "list_tools") and callable(server.mcp.list_tools):
            import inspect

            if inspect.iscoroutinefunction(server.mcp.list_tools):
                mcp_tools = await server.mcp.list_tools()
            else:
                mcp_tools = server.mcp.list_tools()
        if not mcp_tools and hasattr(server.mcp, "_tools"):
            mcp_tools = list(server.mcp._tools.values())

        return {
            "success": True,
            "tools": [
                {
                    "name": getattr(t, "name", str(t)),
                    "description": getattr(t, "description", ""),
                    "parameters": (
                        t.parameters.model_json_schema()
                        if hasattr(t, "parameters") and hasattr(t.parameters, "model_json_schema")
                        else getattr(t, "parameters", {}),
                    ),
                }
                for t in sorted(mcp_tools, key=lambda x: getattr(x, "name", str(x)))
            ],
        }
    except Exception as e:
        logger.exception("Failed to list tools")
        return {"success": False, "error": str(e), "tools": []}


@router.get("/api/capabilities")
async def get_capabilities():
    """Runtime capability introspection for MCP-aware webapp pages."""
    try:
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()
        mcp = server.mcp

        # Tools
        raw_tools = []
        if hasattr(mcp, "list_tools") and callable(mcp.list_tools):
            raw_tools = await _maybe_await(mcp.list_tools())
        elif hasattr(mcp, "_tools"):
            raw_tools = list(mcp._tools.values())
        tool_names = sorted([getattr(t, "name", str(t)) for t in raw_tools])

        # Prompts/resources are optional across FastMCP versions and tool modes.
        prompt_names = []
        resource_uris = []

        if hasattr(mcp, "list_prompts") and callable(mcp.list_prompts):
            prompts = await _maybe_await(mcp.list_prompts())
            prompt_names = sorted([getattr(p, "name", str(p)) for p in prompts if getattr(p, "name", None)])

        if hasattr(mcp, "list_resources") and callable(mcp.list_resources):
            resources = await _maybe_await(mcp.list_resources())
            resource_uris = sorted([str(getattr(r, "uri", "")) for r in resources if getattr(r, "uri", None)])

        portmanteau_tools = [name for name in tool_names if _is_portmanteau_tool_name(name)]
        atomic_tools = [name for name in tool_names if name not in portmanteau_tools]

        workflow_tools = sorted([name for name in tool_names if "workflow" in name or "assistant" in name])
        sampling_indicators = sorted([name for name in tool_names if "agentic" in name or "assistant" in name])
        skill_uris = sorted([uri for uri in resource_uris if uri.startswith("skill://")])

        tool_mode = "portmanteau"
        if len(portmanteau_tools) > 0 and len(atomic_tools) > 0:
            tool_mode = "both"
        elif len(portmanteau_tools) == 0:
            tool_mode = "atomic"

        return {
            "status": "ok",
            "server": {
                "name": "devices-mcp",
                "version": "1.0.0",
                "fastmcp": "3.2+",
            },
            "tool_surface": {
                "total": len(tool_names),
                "portmanteau_count": len(portmanteau_tools),
                "atomic_count": len(atomic_tools),
                "portmanteau_tools": portmanteau_tools,
                "atomic_tools": atomic_tools,
            },
            "features": {
                "sampling": len(sampling_indicators) > 0,
                "agentic_workflows": len(workflow_tools) > 0,
                "prompts": len(prompt_names) > 0,
                "resources": len(resource_uris) > 0,
                "skills": len(skill_uris) > 0,
            },
            "inventory": {
                "workflow_tools": workflow_tools,
                "sampling_indicator_tools": sampling_indicators,
                "prompt_names": prompt_names,
                "resource_uris": resource_uris,
                "skill_uris": skill_uris,
            },
            "runtime": {
                "transport": "http",
                "surface_mode": tool_mode,
                "tool_mode_env": os.getenv("TAPO_MCP_TOOL_MODE", "production"),
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as e:
        logger.exception("Failed to build capabilities response")
        return {
            "status": "error",
            "error": str(e),
            "features": {
                "sampling": False,
                "agentic_workflows": False,
                "prompts": False,
                "resources": False,
                "skills": False,
            },
            "tool_surface": {
                "total": 0,
                "portmanteau_count": 0,
                "atomic_count": 0,
                "portmanteau_tools": [],
                "atomic_tools": [],
            },
            "inventory": {
                "workflow_tools": [],
                "sampling_indicator_tools": [],
                "prompt_names": [],
                "resource_uris": [],
                "skill_uris": [],
            },
            "runtime": {"transport": "http", "surface_mode": "unknown"},
            "timestamp": datetime.now(UTC).isoformat(),
        }


@router.get("/metrics", summary="Prometheus metrics (fleet mcp_tool_* and process defaults)")
async def prometheus_metrics():
    from devices_mcp.fleet_tool_metrics import prometheus_metrics_body_and_type

    body, media_type = prometheus_metrics_body_and_type()
    return Response(content=body, media_type=media_type)


@router.get("/api/health", summary="Get comprehensive system health metrics")
async def get_health():
    """Get comprehensive system health metrics including disk, CPU, memory, uptime, and services."""
    try:
        # System resources
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
        except Exception:
            cpu_percent = 0
        try:
            memory = psutil.virtual_memory()
        except Exception:
            memory = None
        try:
            disk = psutil.disk_usage("/")
        except Exception:
            disk = None

        # System uptime
        boot_time = psutil.boot_time()
        uptime_seconds = time.time() - boot_time

        # Process info
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent(interval=0.1)

        # Network stats
        try:
            net_io = psutil.net_io_counters()
            network = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
            }
        except Exception:
            network = None

        # Database status
        db_status = {}
        try:
            ts_db_path = Path("data/timeseries.db")
            if ts_db_path.exists():
                db_size = ts_db_path.stat().st_size
                db_status["timeseries"] = {
                    "status": "ok",
                    "path": str(ts_db_path),
                    "size_bytes": db_size,
                    "size_mb": round(db_size / (1024 * 1024), 2),
                }
            else:
                db_status["timeseries"] = {"status": "not_found"}
        except Exception as e:
            db_status["timeseries"] = {"status": "error", "error": str(e)}

        # Check PostgreSQL
        postgres_status = {"status": "unknown"}
        try:
            import os

            postgres_host = os.getenv("POSTGRES_HOST")
            if postgres_host:
                import socket

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((postgres_host, int(os.getenv("POSTGRES_PORT", "5432"))))
                sock.close()
                if result == 0:
                    postgres_status = {"status": "reachable", "host": postgres_host}
                else:
                    postgres_status = {"status": "unreachable", "host": postgres_host}
            else:
                postgres_status = {"status": "not_configured"}
        except Exception as e:
            postgres_status = {"status": "error", "error": str(e)}

        db_status["postgres"] = postgres_status

        # Camera status
        camera_status = {"total": 0, "online": 0, "offline": 0}
        try:
            from devices_mcp.core.server import DevicesMCPServer

            server = await asyncio.wait_for(asyncio.shield(DevicesMCPServer.get_instance()), timeout=3.0)
            cameras = await asyncio.wait_for(server.camera_manager.list_cameras(), timeout=3.0)
            camera_status["total"] = len(cameras)
            online_count = 0
            for cam in cameras:
                status_val = cam.get("status", {})
                if isinstance(status_val, dict):
                    if status_val.get("connected", False):
                        online_count += 1
                elif isinstance(status_val, str) and status_val == "online":
                    online_count += 1
            camera_status["online"] = online_count
            camera_status["offline"] = camera_status["total"] - camera_status["online"]
        except Exception as e:
            logger.warning(f"Health check camera status error: {e}")
            camera_status = {"total": 0, "online": 0, "offline": 0, "error": str(e)}

        return {
            "success": True,
            "timestamp": time.time(),
            "uptime_seconds": uptime_seconds,
            "uptime_human": str(timedelta(seconds=int(uptime_seconds))),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total if memory else 0,
                    "available": memory.available if memory else 0,
                    "percent": memory.percent if memory else 0,
                }
                if memory
                else None,
                "disk": {
                    "total": disk.total if disk else 0,
                    "used": disk.used if disk else 0,
                    "free": disk.free if disk else 0,
                    "percent": disk.percent if disk else 0,
                }
                if disk
                else None,
            },
            "process": {
                "memory_rss": process_memory.rss,
                "cpu_percent": process_cpu,
            },
            "network": network,
            "databases": db_status,
            "cameras": camera_status,
        }
    except Exception as e:
        logger.exception("Health check failed")
        return {"success": False, "error": str(e)}


@router.get("/api/system/status")
async def get_system_status():
    """Get system status."""
    try:
        from devices_mcp.core.server import DevicesMCPServer

        server = await asyncio.wait_for(asyncio.shield(DevicesMCPServer.get_instance()), timeout=3.0)
        cameras = await asyncio.wait_for(server.camera_manager.list_cameras(), timeout=3.0)
        total_cameras = len(cameras)
        online_cameras = sum(
            1
            for cam in cameras
            if cam.get("status") == "online"
            or (isinstance(cam.get("status"), dict) and cam.get("status", {}).get("connected", False))
        )

        try:
            disk = psutil.disk_usage("/")
            storage_used_percent = round(disk.percent, 1)
        except Exception:
            storage_used_percent = 0

        return {
            "status": "ok",
            "version": "1.0.0",
            "cameras": {
                "total": total_cameras,
                "online": online_cameras,
                "offline": total_cameras - online_cameras,
            },
            "storage": {"used_percent": storage_used_percent},
            "uptime": "N/A",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/api/system/reconnect")
async def reconnect_services() -> dict[str, Any]:
    """Reconnect dashboard services (hue rescan, netatmo re-init) and report state.

    Returns per-service status after the reconnect attempt so the dashboard
    can refresh its cards in one round trip.
    """
    results: dict[str, Any] = {}
    try:
        from devices_mcp.tools.lighting.hue_tools import get_hue_manager

        mgr = get_hue_manager()
        if mgr._initialized and mgr._bridge is not None:
            try:
                await asyncio.wait_for(mgr.rescan(), timeout=20.0)
                results["hue"] = {
                    "ok": True,
                    "connected": True,
                    "lights_count": len(mgr.lights),
                    "message": "Hue bridge rescan complete.",
                }
            except Exception as e:
                results["hue"] = {
                    "ok": False,
                    "connected": False,
                    "message": f"Hue rescan failed: {e!s}",
                }
        else:
            results["hue"] = {"ok": False, "connected": False, "message": "Hue bridge not initialized."}
    except Exception as e:
        results["hue"] = {"ok": False, "message": f"Hue reconnect error: {e!s}"}

    try:
        from devices_mcp.integrations.netatmo_client import NetatmoService

        await NetatmoService.reset_for_reconnect()
        try:
            inst = await asyncio.wait_for(NetatmoService.get_instance(), timeout=25.0)
        except Exception:
            inst = None
        if inst is None:
            results["netatmo"] = {"ok": False, "connected": False, "message": "Netatmo client not loaded."}
        else:
            ok = inst.is_api_ready()
            results["netatmo"] = {
                "ok": ok,
                "connected": ok,
                "message": "Netatmo weather station is connected."
                if ok
                else (inst.last_error or "Netatmo needs re-auth."),
                "reconnect_url": "/api/netatmo/oauth/start",
            }
    except Exception as e:
        results["netatmo"] = {"ok": False, "message": f"Netatmo reconnect error: {e!s}"}

    results["status"] = "ok" if any(r.get("ok") for r in results.values()) else "degraded"
    return results
