"""
Dedicated health check tool for comprehensive system monitoring.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict

from pydantic import BaseModel, Field

from devices_mcp.tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


class HealthCheckResult(BaseModel):
    """Result of a comprehensive health check."""

    status: str = Field(..., description="Overall health status: healthy/warning/critical")
    checks: Dict[str, Any] = Field(..., description="Individual health check results")
    response_time_ms: float = Field(..., description="Time taken for health check")
    timestamp: str = Field(..., description="Timestamp of health check")


@tool(name="health_check")
class HealthCheckTool(BaseTool):
    """Tool for comprehensive health monitoring and diagnostics."""

    class Meta:
        name = "health_check"
        description = "Perform comprehensive health check of the MCP server and cameras"
        category = ToolCategory.SYSTEM

        class Parameters:
            include_cameras: bool = Field(
                True, description="Whether to include camera health checks"
            )
            include_performance: bool = Field(
                True, description="Whether to include performance metrics"
            )

    include_cameras: bool = True
    include_performance: bool = True

    def __init__(self, **data):
        super().__init__(**data)
        self._performance_metrics = {
            "response_times": [],
            "last_reset": datetime.utcnow(),
        }

    async def execute(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        start_time = time.time()

        try:
            # Core server health
            server_health = await self._check_server_health()

            # System resource health
            system_health = await self._check_system_health()

            # Camera health (if requested)
            camera_health = {}
            if self.include_cameras:
                camera_health = await self._check_camera_health()

            # Performance metrics (if requested) - pass response time for accurate calculation
            performance_metrics = {}
            if self.include_performance:
                # Update last check time for performance metrics
                if not hasattr(self, "_last_check_time"):
                    self._last_check_time = start_time
                performance_metrics = await self._get_performance_metrics()

            # Overall status determination
            all_checks = {
                "server": server_health,
                "system": system_health,
                **camera_health,
                **performance_metrics,
            }

            # Determine overall status
            critical_issues = [
                name
                for name, check in all_checks.items()
                if isinstance(check, dict) and check.get("status") == "critical"
            ]
            warning_issues = [
                name
                for name, check in all_checks.items()
                if isinstance(check, dict) and check.get("status") == "warning"
            ]

            if critical_issues:
                overall_status = "critical"
            elif warning_issues:
                overall_status = "warning"
            else:
                overall_status = "healthy"

            response_time_ms = (time.time() - start_time) * 1000

            result = HealthCheckResult(
                status=overall_status,
                checks=all_checks,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow().isoformat(),
            )

            logger.info(f"Health check completed: {overall_status} ({response_time_ms:.1f}ms)")
            return result.dict()

        except Exception as e:
            logger.exception("Health check failed")
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheckResult(
                status="critical",
                checks={"error": {"status": "critical", "message": str(e)}},
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow().isoformat(),
            ).dict()

    async def _check_server_health(self) -> Dict[str, Any]:
        """Check MCP server health."""
        try:
            # Check if server is responsive by testing basic operations
            from devices_mcp.core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()

            # Basic responsiveness check
            server_responsive = hasattr(server, "mcp") and server.mcp is not None

            # Check for registered tools - use _tools_registered flag instead of list_tools()
            tools_registered = (
                getattr(server, "_tools_registered", False) if server_responsive else False
            )

            issues = []
            if not server_responsive:
                issues.append("Server not properly initialized")
            elif not tools_registered:
                issues.append("Tools not yet registered")

            status = "critical" if issues else "healthy"

            return {
                "status": status,
                "responsive": server_responsive,
                "tools_registered": tools_registered,
                "issues": issues,
            }

        except Exception as e:
            logger.exception("Server health check failed")
            return {"status": "critical", "error": str(e), "issues": [str(e)]}

    async def _check_system_health(self) -> Dict[str, Any]:
        """Check system resource health."""
        try:
            try:
                import psutil

                has_psutil = True
            except ImportError:
                has_psutil = False

            if has_psutil:
                # Get resource usage
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
            else:
                # Fallback when psutil is not available
                return {
                    "status": "warning",
                    "issues": ["psutil not available - system monitoring limited"],
                    "cpu_percent": 0.0,
                    "memory_percent": 0.0,
                    "disk_percent": 0.0,
                }

            issues = []

            # Check thresholds
            if cpu_percent > 90:
                issues.append(f"Critical CPU usage: {cpu_percent}%")
            elif cpu_percent > 80:
                issues.append(f"High CPU usage: {cpu_percent}%")

            if memory.percent > 95:
                issues.append(f"Critical memory usage: {memory.percent}%")
            elif memory.percent > 85:
                issues.append(f"High memory usage: {memory.percent}%")

            if disk.percent > 95:
                issues.append(f"Critical disk usage: {disk.percent}%")
            elif disk.percent > 90:
                issues.append(f"High disk usage: {disk.percent}%")

            # Determine status
            if any("Critical" in issue for issue in issues):
                status = "critical"
            elif issues:
                status = "warning"
            else:
                status = "healthy"

            return {
                "status": status,
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "issues": issues,
            }

        except Exception as e:
            logger.exception("System health check failed")
            return {"status": "critical", "error": str(e), "issues": [str(e)]}

    async def _check_camera_health(self) -> Dict[str, Any]:
        """Check camera connectivity and health."""
        try:
            from devices_mcp.core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()
            camera_manager = server.camera_manager

            if not camera_manager:
                return {
                    "status": "no_manager",
                    "issues": ["No camera manager available"],
                }

            # Use list_cameras() method or cameras dict
            if hasattr(camera_manager, "list_cameras"):
                cameras_list = await camera_manager.list_cameras()
                total_cameras = len(cameras_list)
                online_cameras = sum(
                    1 for cam in cameras_list if cam.get("status", {}).get("connected", False)
                )
            elif hasattr(camera_manager, "cameras"):
                cameras_dict = camera_manager.cameras
                total_cameras = len(cameras_dict)
                online_cameras = 0
                for camera_name, camera in cameras_dict.items():
                    try:
                        status = await camera.get_status()
                        if status.get("connected", False):
                            online_cameras += 1
                    except Exception:
                        pass
            else:
                return {
                    "status": "no_cameras",
                    "total_cameras": 0,
                    "online_cameras": 0,
                    "issues": ["Cannot access camera list"],
                }

            issues = []
            if total_cameras == 0:
                camera_status = "no_cameras"
            elif online_cameras == 0:
                camera_status = "critical"
                issues.append("No cameras are online")
            elif online_cameras < total_cameras:
                camera_status = "warning"
                issues.append(f"{total_cameras - online_cameras} camera(s) offline")
            else:
                camera_status = "healthy"

            return {
                "status": camera_status,
                "total_cameras": total_cameras,
                "online_cameras": online_cameras,
                "issues": issues,
            }

        except Exception as e:
            logger.exception("Camera health check failed")
            return {"status": "critical", "error": str(e), "issues": [str(e)]}

    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance monitoring metrics."""
        try:
            # Calculate this health check response time (will be updated by caller)
            current_time = time.time()

            # Initialize if first call
            if not hasattr(self, "_last_check_time"):
                self._last_check_time = current_time
                response_time_delta = 0
            else:
                response_time_delta = current_time - self._last_check_time
                self._last_check_time = current_time

            # Record response time delta (in ms)
            if response_time_delta > 0:
                self._performance_metrics["response_times"].append(response_time_delta * 1000)

            # Clean old metrics (keep last 100)
            if len(self._performance_metrics["response_times"]) > 100:
                self._performance_metrics["response_times"] = self._performance_metrics[
                    "response_times"
                ][-100:]

            # Calculate average response time
            response_times = self._performance_metrics["response_times"]
            avg_response_time_ms = (
                sum(response_times) / len(response_times) if response_times else 0
            )

            try:
                import psutil

                process = psutil.Process()
                memory_mb = process.memory_info().rss / (1024 * 1024)
            except ImportError:
                memory_mb = 0.0

            return {
                "status": "healthy",
                "avg_response_time_ms": round(avg_response_time_ms, 2),
                "memory_usage_mb": round(memory_mb, 2),
                "cpu_usage_percent": process.cpu_percent(),
                "health_checks_count": len(response_times),
            }

        except Exception as e:
            logger.exception("Performance metrics failed")
            return {"status": "warning", "error": str(e)}
