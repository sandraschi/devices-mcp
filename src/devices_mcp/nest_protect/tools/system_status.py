"""System status tools for Nest Protect MCP."""

import os
import platform
import time
from typing import Any, Dict, Optional

import psutil
from pydantic import BaseModel, Field


class ProcessStatusParams(BaseModel):
    """Parameters for process status."""

    pid: Optional[int] = Field(None, description="Process ID to check (default: current process)")


async def get_system_status() -> Dict[str, Any]:
    """Get system status and metrics."""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        # Memory
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        # Disk
        disk = psutil.disk_usage("/")
        disk_io = psutil.disk_io_counters()

        # Network
        net_io = psutil.net_io_counters()
        net_if = psutil.net_if_addrs()

        # System info
        boot_time = psutil.boot_time()
        uptime = time.time() - boot_time

        return {
            "status": "success",
            "system": {
                "os": f"{platform.system()} {platform.release()}",
                "hostname": platform.node(),
                "python_version": platform.python_version(),
                "uptime_seconds": int(uptime),
                "boot_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_time)),
            },
            "cpu": {
                "usage_percent": cpu_percent,
                "cores": cpu_count,
                "load_avg": [x / cpu_count * 100 for x in os.getloadavg()]
                if hasattr(os, "getloadavg")
                else None,
            },
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "used_percent": mem.percent,
                "swap_total_gb": round(swap.total / (1024**3), 2),
                "swap_used_gb": round(swap.used / (1024**3), 2),
                "swap_free_gb": round(swap.free / (1024**3), 2),
                "swap_percent": swap.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "used_percent": disk.percent,
                "read_mb": round(disk_io.read_bytes / (1024**2), 2) if disk_io else None,
                "write_mb": round(disk_io.write_bytes / (1024**2), 2) if disk_io else None,
            },
            "network": {
                "bytes_sent_mb": round(net_io.bytes_sent / (1024**2), 2) if net_io else None,
                "bytes_recv_mb": round(net_io.bytes_recv / (1024**2), 2) if net_io else None,
                "interfaces": list(net_if.keys()) if net_if else [],
            },
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to get system status: {e!s}"}


async def get_process_status(pid: int = None) -> Dict[str, Any]:
    """Get status of the Nest Protect MCP process."""
    try:
        if pid is None:
            process = psutil.Process()
        else:
            process = psutil.Process(pid)

        with process.oneshot():
            return {
                "status": "success",
                "process": {
                    "pid": process.pid,
                    "name": process.name(),
                    "status": process.status(),
                    "create_time": process.create_time(),
                    "cpu_percent": process.cpu_percent(interval=0.1),
                    "memory_percent": process.memory_percent(),
                    "memory_info": {
                        "rss_mb": round(process.memory_info().rss / (1024**2), 2),
                        "vms_mb": round(process.memory_info().vms / (1024**2), 2),
                    },
                    "num_threads": process.num_threads(),
                    "connections": [
                        {
                            "fd": conn.fd,
                            "family": conn.family,
                            "type": conn.type,
                            "laddr": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                            "raddr": f"{conn.raddr.ip}:{conn.raddr.port}"
                            if hasattr(conn, "raddr") and conn.raddr
                            else None,
                            "status": conn.status,
                        }
                        for conn in process.connections()
                    ],
                },
            }
    except psutil.NoSuchProcess:
        return {"status": "error", "message": f"Process {pid} not found"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to get process status: {e!s}"}


async def get_api_status() -> Dict[str, Any]:
    """Get status of the Nest API connection."""
    import aiohttp

    from ..state_manager import get_app_state

    state = get_app_state()

    if not state.access_token:
        return {
            "status": "success",
            "api_connected": False,
            "message": "Not authenticated with Nest API",
        }

    try:
        url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{state.config.project_id}/devices"
        headers = {"Authorization": f"Bearer {state.access_token}"}

        async with aiohttp.ClientSession() as session, session.get(
            url, headers=headers, params={"pageSize": 1}
        ) as response:
            if response.status == 200:
                return {
                    "status": "success",
                    "api_connected": True,
                    "message": "Successfully connected to Nest API",
                    "token_expires_in": getattr(state, "token_expires_in", None),
                }
            error = await response.json()
            return {
                "status": "error",
                "api_connected": False,
                "message": "Failed to connect to Nest API",
                "error": error.get("error", {}).get("message"),
                "token_expires_in": getattr(state, "token_expires_in", None),
            }
    except Exception as e:
        return {
            "status": "error",
            "api_connected": False,
            "message": f"Failed to check API status: {e!s}",
            "token_expires_in": getattr(state, "token_expires_in", None),
        }
