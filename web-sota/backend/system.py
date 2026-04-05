import asyncio
import logging
import os
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import psutil
from fastapi import APIRouter

from devices_mcp.mcp_client import call_mcp_tool

if TYPE_CHECKING:
    from devices_mcp.core.server import TapoCameraServer
else:
    # Import at runtime to avoid circular dependencies
    from devices_mcp.core.server import TapoCameraServer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/status")
async def get_status():
    """Get server status."""
    # Try to get debug flag from server instance
    debug = False
    try:
        server = await TapoCameraServer.get_instance()
        if server and hasattr(server, "config"):
            # Access config from the server instance if available
            # Note: This depends on how config is exposed in TapoCameraServer
            # Assuming it might be accessible via properties or methods
            pass
    except Exception:
        pass

    return {
        "status": "ok",
        "version": "1.0.0",
        "debug": debug,
    }


@router.get("/health", summary="Get comprehensive system health metrics")
async def get_health():
    """Get comprehensive system health metrics including disk, CPU, memory, uptime, and services."""
    try:
        # System resources (with error handling)
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
            # Check SQLite (time series DB)
            # Assuming standard path relative to this file
            ts_db_path = Path(__file__).parent.parent.parent.parent / "data" / "timeseries.db"
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
            postgres_host = os.getenv("POSTGRES_HOST")
            if postgres_host:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((postgres_host, int(os.getenv("POSTGRES_PORT", "5432"))))
                sock.close()
                if result == 0:
                    postgres_status = {
                        "status": "reachable",
                        "host": postgres_host,
                    }
                else:
                    postgres_status = {
                        "status": "unreachable",
                        "host": postgres_host,
                    }
            else:
                postgres_status = {"status": "not_configured"}
        except Exception as e:
            postgres_status = {"status": "error", "error": str(e)}

        db_status["postgres"] = postgres_status

        # Camera status (with timeout to prevent hanging)
        camera_status = {"total": 0, "online": 0, "offline": 0}
        try:
            # Get camera status from MCP
            result = await call_mcp_tool("camera_management", {"action": "list"})
            if result.get("success"):
                cameras = result.get("data", [])
                camera_status["total"] = len(cameras)
                # Check status - can be dict or string
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
                camera_status["initialization"] = "ready"
            else:
                camera_status["initialization"] = "error"
                camera_status["error"] = "MCP call failed"
        except asyncio.TimeoutError:
            logger.warning("Camera status check timed out in health endpoint")
            camera_status = {
                "total": 0,
                "online": 0,
                "offline": 0,
                "error": "timeout",
            }
        except Exception as e:
            logger.warning(f"Camera status check failed: {e}")
            camera_status["error"] = str(e)

        # Determine overall health status
        issues = []
        if cpu_percent > 90:
            issues.append("critical_cpu")
        elif cpu_percent > 80:
            issues.append("high_cpu")

        if memory and memory.percent > 95:
            issues.append("critical_memory")
        elif memory and memory.percent > 85:
            issues.append("high_memory")

        if disk and disk.percent > 95:
            issues.append("critical_disk")
        elif disk and disk.percent > 90:
            issues.append("high_disk")

        if camera_status["total"] > 0 and camera_status["online"] == 0:
            issues.append("no_cameras_online")

        if postgres_status.get("status") == "unreachable":
            issues.append("postgres_unreachable")

        overall_status = (
            "critical"
            if any("critical" in issue for issue in issues)
            else "warning"
            if issues
            else "healthy"
        )

        # Build response with safe defaults if metrics failed
        memory_data = (
            {
                "total_gb": round(memory.total / (1024**3), 2) if memory else 0,
                "available_gb": round(memory.available / (1024**3), 2) if memory else 0,
                "used_gb": round(memory.used / (1024**3), 2) if memory else 0,
                "percent": round(memory.percent, 1) if memory else 0,
                "process_mb": round(process_memory.rss / (1024**2), 2) if memory else 0,
            }
            if memory
            else {"error": "Unable to read memory stats"}
        )

        disk_data = (
            {
                "total_gb": round(disk.total / (1024**3), 2) if disk else 0,
                "used_gb": round(disk.used / (1024**3), 2) if disk else 0,
                "free_gb": round(disk.free / (1024**3), 2) if disk else 0,
                "percent": round(disk.percent, 1) if disk else 0,
            }
            if disk
            else {"error": "Unable to read disk stats"}
        )

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": {
                "cpu": {
                    "percent": round(cpu_percent, 1),
                    "count": psutil.cpu_count(),
                    "process_percent": round(process_cpu, 1),
                },
                "memory": memory_data,
                "disk": disk_data,
                "uptime": {
                    "seconds": int(uptime_seconds),
                    "days": int(uptime_seconds / 86400),
                    "hours": int((uptime_seconds % 86400) / 3600),
                    "minutes": int((uptime_seconds % 3600) / 60),
                },
            },
            "network": network,
            "databases": db_status,
            "cameras": camera_status,
            "issues": issues,
        }
    except Exception as e:
        logger.exception("Error getting health metrics")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
