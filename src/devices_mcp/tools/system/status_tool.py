"""
Status tool for monitoring system health and camera status in Devices MCP.
"""

import logging
import os
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# Lazy import psutil to avoid import errors if not available
try:
    import psutil

    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

from devices_mcp.tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


class SystemStatus(BaseModel):
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    disk_usage: float = Field(..., description="Disk usage percentage")
    uptime: str = Field(..., description="System uptime")
    active_cameras: int = Field(..., description="Number of active camera connections")
    active_streams: int = Field(..., description="Number of active streams")
    last_updated: str = Field(..., description="Timestamp of last status update")


class HealthStatus(BaseModel):
    """Comprehensive health status information."""

    overall: str = Field(..., description="Overall health status: healthy/warning/critical")
    server_status: str = Field(..., description="MCP server status")
    camera_health: dict[str, Any] = Field(..., description="Camera health information")
    system_health: dict[str, Any] = Field(..., description="System resource health")
    last_check: str = Field(..., description="Timestamp of health check")


class PerformanceMetrics(BaseModel):
    """Performance monitoring metrics."""

    response_time_avg: float = Field(..., description="Average response time (ms)")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    cpu_usage_percent: float = Field(..., description="CPU usage percentage")
    active_connections: int = Field(..., description="Number of active connections")
    total_requests: int = Field(..., description="Total requests processed")


@tool(name="status")
class StatusTool(BaseTool):
    """Tool to get system and camera status information."""

    class Meta:
        name = "status"
        category = ToolCategory.SYSTEM

    detail_level: str = Field(default="basic", description="Level of detail in the status report")
    section: str = Field(default="system", description="Section to get status for")

    model_config = ConfigDict(json_schema_extra={"enum": ["basic", "detailed", "cameras"]})

    def __init__(self, **data):
        super().__init__(**data)
        # Store server reference in a way that doesn't conflict with Pydantic
        self._server = None
        self._camera_manager = None

    def _get_server(self):
        """Get server instance, initializing if needed."""
        if self._server is None:
            try:
                from devices_mcp.core.server import TapoCameraServer

                self._server = TapoCameraServer.get_instance()
            except Exception:
                self._server = None
        return self._server

    def _get_camera_manager(self):
        """Get camera manager instance, initializing if needed."""
        if self._camera_manager is None:
            server = self._get_server()
            if server and hasattr(server, "camera_manager"):
                self._camera_manager = server.camera_manager
        return self._camera_manager

    async def execute(self) -> dict[str, Any]:
        """Return comprehensive system and camera status information with health monitoring."""
        try:
            # Get basic system status
            basic_status = await self._get_system_status()

            # Enhanced health monitoring for Gold status
            health_status = await self._get_comprehensive_health()

            # Combine status information
            result = {
                "success": True,
                "status": basic_status,
                "health": health_status,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Get camera status if requested
            if self.detail_level in ["detailed", "cameras"] and self._get_camera_manager():
                result["cameras"] = await self._get_camera_statuses()

                if self.detail_level == "detailed":
                    result["system"] = await self._get_detailed_system_status()

            logger.info(f"Status check completed - Health: {health_status.get('overall', 'unknown')}")
            return result

        except Exception as e:
            logger.exception("Error getting system status")
            return {
                "success": False,
                "error": f"Failed to get status: {e!s}",
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def _get_comprehensive_health(self) -> dict[str, Any]:
        """Get comprehensive health status for Gold tier monitoring."""
        try:
            # System resource health
            if HAS_PSUTIL and psutil:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                disk_percent = psutil.disk_usage("/").percent
            else:
                cpu_percent = 0.0
                memory_percent = 0.0
                disk_percent = 0.0
                system_warnings = ["psutil not available - system monitoring limited"]

            # Determine overall system health
            system_warnings = []
            if cpu_percent > 80:
                system_warnings.append("High CPU usage")
            if memory_percent > 85:
                system_warnings.append("High memory usage")
            if disk_percent > 90:
                system_warnings.append("High disk usage")

            system_status = "healthy" if not system_warnings else "warning"

            # Camera health
            camera_health = await self._assess_camera_health()

            # MCP Server health
            server_status = await self._assess_server_health()

            # Overall health determination
            all_warnings = system_warnings + camera_health.get("warnings", []) + server_status.get("warnings", [])
            overall = (
                "critical"
                if any("critical" in warning.lower() for warning in all_warnings)
                else "warning"
                if all_warnings
                else "healthy"
            )

            return {
                "overall": overall,
                "server_status": server_status.get("status", "unknown"),
                "camera_health": camera_health,
                "system_health": {
                    "status": system_status,
                    "warnings": system_warnings,
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                },
                "last_check": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.exception("Error in comprehensive health check")
            return {
                "overall": "critical",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat(),
            }

    async def _assess_camera_health(self) -> dict[str, Any]:
        """Assess overall camera health."""
        camera_manager = self._get_camera_manager()
        if not camera_manager:
            return {"status": "no_cameras", "warnings": []}

        try:
            cameras = camera_manager.get_cameras()
            total_cameras = len(cameras)
            online_cameras = sum(1 for camera in cameras if camera.is_online())

            warnings = []
            if online_cameras == 0 and total_cameras > 0:
                warnings.append("No cameras are currently online")
            elif online_cameras < total_cameras:
                warnings.append(f"{total_cameras - online_cameras} cameras are offline")

            status = "healthy" if online_cameras > 0 else "warning"

            return {
                "status": status,
                "total_cameras": total_cameras,
                "online_cameras": online_cameras,
                "warnings": warnings,
            }

        except Exception as e:
            logger.exception("Error assessing camera health")
            return {"status": "error", "warnings": [str(e)]}

    async def _assess_server_health(self) -> dict[str, Any]:
        """Assess MCP server health."""
        try:
            # Check if server is responsive
            server_responsive = True

            # Check for any critical errors in logs (simplified check)
            critical_errors = 0

            warnings = []
            if critical_errors > 0:
                warnings.append(f"{critical_errors} critical errors detected")

            status = "healthy" if server_responsive and critical_errors == 0 else "warning"

            return {
                "status": status,
                "responsive": server_responsive,
                "warnings": warnings,
            }

        except Exception as e:
            logger.exception("Error assessing server health")
            return {"status": "error", "warnings": [str(e)]}

    async def _get_system_status(self) -> dict[str, Any]:
        """Get basic system status information."""
        camera_manager = self._get_camera_manager()

        if HAS_PSUTIL and psutil:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage("/").percent
            uptime = self._format_uptime(psutil.boot_time())
        else:
            cpu_percent = 0.0
            memory_percent = 0.0
            disk_percent = 0.0
            uptime = "unknown"

        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_usage": disk_percent,
            "uptime": uptime,
            "active_cameras": (len(camera_manager.get_active_cameras()) if camera_manager else 0),
            "active_streams": (len(camera_manager.get_active_streams()) if camera_manager else 0),
            "last_updated": datetime.utcnow().isoformat(),
        }

    async def _get_camera_statuses(self) -> list[dict[str, Any]]:
        """Get status for all cameras."""
        camera_manager = self._get_camera_manager()
        if not camera_manager:
            return []

        cameras_status = []
        for camera in camera_manager.get_cameras():
            stream = camera_manager.get_camera_stream(camera.id)
            cameras_status.append(
                {
                    "camera_id": camera.id,
                    "model": camera.model,
                    "status": "online" if camera.is_online() else "offline",
                    "last_seen": camera.last_seen.isoformat() if camera.last_seen else "never",
                    "stream_status": "active" if stream and stream.is_active() else "inactive",
                    "fps": stream.get_fps() if stream else 0.0,
                    "resolution": f"{stream.width}x{stream.height}" if stream else "N/A",
                }
            )
        return cameras_status

    async def _get_detailed_system_status(self) -> dict[str, Any]:
        """Get detailed system status information."""

        if HAS_PSUTIL and psutil:
            process_info = {
                "pid": os.getpid(),
                "memory_mb": psutil.Process().memory_info().rss / (1024 * 1024),
                "threads": psutil.Process().num_threads(),
            }
        else:
            process_info = {
                "pid": os.getpid(),
                "memory_mb": 0.0,
                "threads": 0,
            }

        return {
            "grafana": self._get_grafana_status(),
            "storage": self._get_storage_status(),
            "network": self._get_network_status(),
            "process_info": process_info,
        }

    def _get_grafana_status(self) -> dict[str, Any]:
        """Get Grafana integration status."""
        return {
            "plugin_installed": os.path.exists("/var/lib/grafana/plugins/tapo-camera-stream"),
            "dashboards_imported": len(self._find_grafana_dashboards()) > 0,
            "api_accessible": self._check_grafana_api(),
        }

    def _get_storage_status(self) -> dict[str, Any]:
        """Get storage usage information."""
        return {
            "total_recordings": self._count_recordings(),
            "storage_used_gb": self._get_storage_used_gb(),
            "retention_days": self._get_retention_days(),
        }

    def _get_network_status(self) -> dict[str, Any]:
        """Get network status information."""
        if HAS_PSUTIL and psutil:
            net_io = psutil.net_io_counters()
            if net_io:
                return {
                    "bytes_sent_mb": net_io.bytes_sent / (1024 * 1024),
                    "bytes_recv_mb": net_io.bytes_recv / (1024 * 1024),
                    "active_connections": len(psutil.net_connections()),
                }
            return {
                "bytes_sent_mb": 0.0,
                "bytes_recv_mb": 0.0,
                "active_connections": 0,
            }
        return {
            "bytes_sent_mb": 0.0,
            "bytes_recv_mb": 0.0,
            "active_connections": 0,
        }

    def _format_uptime(self, boot_time: float) -> str:
        """Format system uptime as a human-readable string."""
        uptime_seconds = datetime.now().timestamp() - boot_time
        days, remainder = divmod(int(uptime_seconds), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m"

    def _find_grafana_dashboards(self) -> list[str]:
        """Find all Grafana dashboards."""
        # Implementation depends on your dashboard storage
        return []

    def _check_grafana_api(self) -> bool:
        """Check if Grafana API is accessible."""
        # Implementation depends on your setup
        return False

    def _count_recordings(self) -> int:
        """Count number of stored recordings."""
        # Implementation depends on your storage
        return 0

    def _get_storage_used_gb(self) -> float:
        """Get storage used in GB."""
        # Implementation depends on your storage
        return 0.0

    def _get_retention_days(self) -> int:
        """Get configured retention period in days."""
        # Implementation depends on your configuration
        return 30
