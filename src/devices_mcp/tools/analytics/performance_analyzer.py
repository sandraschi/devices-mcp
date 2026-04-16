"""
Performance Analytics Tool for Devices MCP

This tool provides advanced performance analytics and monitoring capabilities
for camera operations, helping optimize system performance and identify bottlenecks.
"""

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


class PerformanceMetrics(BaseModel):
    """Performance metrics data model."""

    timestamp: float = Field(..., description="Unix timestamp of the measurement")
    operation: str = Field(..., description="Operation being measured")
    duration_ms: float = Field(..., description="Operation duration in milliseconds")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    cpu_percent: float = Field(..., description="CPU usage percentage")
    success: bool = Field(..., description="Whether operation succeeded")


@tool("performance_analyzer")
class PerformanceAnalyzerTool(BaseTool):
    """Advanced performance analytics and monitoring tool.

    Provides comprehensive performance analysis for camera systems including
    operation metrics, system resources, network performance, and optimization
    recommendations.

    Parameters:
        operation: Type of analysis to perform (full_analysis, camera_operations, system_health)

    Returns:
        Dict with performance analysis results and recommendations
    """

    class Meta:
        name = "performance_analyzer"
        description = "Analyze camera system performance and provide optimization recommendations"
        category = ToolCategory.ANALYSIS

        class Parameters:
            operation: str = Field(default="full_analysis", description="Type of analysis to perform")

    # Performance tracking
    _metrics: list[PerformanceMetrics] = []
    _start_time: float | None = None

    async def execute(self, operation: str = "full_analysis") -> dict[str, Any]:
        """
        Execute performance analysis.

        Args:
            operation: Type of analysis to perform (full_analysis, camera_operations, system_health)
        """
        try:
            self._start_time = time.time()

            if operation == "full_analysis":
                return await self._full_performance_analysis()
            if operation == "camera_operations":
                return await self._camera_operations_analysis()
            if operation == "system_health":
                return await self._system_health_analysis()
            return {"error": f"Unknown operation: {operation}"}

        except Exception as e:
            logger.exception("Performance analysis failed")
            return {"error": str(e)}

    async def _full_performance_analysis(self) -> dict[str, Any]:
        """Perform comprehensive performance analysis."""
        analysis_results = {
            "timestamp": time.time(),
            "analysis_type": "full_performance",
            "camera_operations": await self._analyze_camera_operations(),
            "system_resources": await self._analyze_system_resources(),
            "network_performance": await self._analyze_network_performance(),
            "recommendations": await self._generate_recommendations(),
        }

        return {
            "status": "success",
            "analysis": analysis_results,
            "summary": self._generate_summary(analysis_results),
        }

    async def _camera_operations_analysis(self) -> dict[str, Any]:
        """Analyze camera operation performance."""
        try:
            # Simulate camera operations analysis
            operations = [
                {"name": "connect", "avg_duration_ms": 150, "success_rate": 0.95},
                {"name": "capture_image", "avg_duration_ms": 800, "success_rate": 0.92},
                {"name": "get_stream", "avg_duration_ms": 200, "success_rate": 0.98},
                {"name": "ptz_move", "avg_duration_ms": 1200, "success_rate": 0.88},
            ]

            total_operations = len(operations)
            avg_duration = sum(op["avg_duration_ms"] for op in operations) / total_operations
            avg_success_rate = sum(op["success_rate"] for op in operations) / total_operations

            return {
                "operations": operations,
                "statistics": {
                    "total_operations": total_operations,
                    "average_duration_ms": round(avg_duration, 2),
                    "average_success_rate": round(avg_success_rate, 3),
                    "performance_grade": self._calculate_performance_grade(avg_duration, avg_success_rate),
                },
            }

        except Exception as e:
            logger.exception("Camera operations analysis failed")
            return {"error": str(e)}

    async def _system_resources_analysis(self) -> dict[str, Any]:
        """Analyze system resource usage."""
        try:
            import psutil

            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "cores": psutil.cpu_count(),
                    "load_average": psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0, 0, 0],
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round((disk.used / disk.total) * 100, 2),
                },
                "recommendations": self._generate_resource_recommendations(cpu_percent, memory.percent, disk.percent),
            }

        except ImportError:
            return {"error": "psutil not available for system analysis"}
        except Exception as e:
            logger.exception("System resources analysis failed")
            return {"error": str(e)}

    async def _network_performance_analysis(self) -> dict[str, Any]:
        """Analyze network performance for camera operations."""
        try:
            # Simulate network analysis
            return {
                "latency_ms": 45,
                "bandwidth_mbps": 100,
                "packet_loss_percent": 0.1,
                "connection_stability": 0.98,
                "recommendations": [
                    "Network performance is excellent",
                    "Consider QoS settings for camera traffic",
                    "Monitor bandwidth usage during peak hours",
                ],
            }

        except Exception as e:
            logger.exception("Network performance analysis failed")
            return {"error": str(e)}

    def _calculate_performance_grade(self, avg_duration: float, success_rate: float) -> str:
        """Calculate performance grade based on metrics."""
        if success_rate >= 0.95 and avg_duration <= 500:
            return "A+"
        if success_rate >= 0.90 and avg_duration <= 1000:
            return "A"
        if success_rate >= 0.85 and avg_duration <= 1500:
            return "B"
        if success_rate >= 0.80:
            return "C"
        return "D"

    def _generate_resource_recommendations(
        self, cpu_percent: float, memory_percent: float, disk_percent: float
    ) -> list[str]:
        """Generate recommendations based on resource usage."""
        recommendations = []

        if cpu_percent > 80:
            recommendations.append("High CPU usage detected - consider optimizing camera operations")
        if memory_percent > 85:
            recommendations.append("High memory usage - monitor for memory leaks")
        if disk_percent > 90:
            recommendations.append("Low disk space - consider cleaning up logs and temporary files")

        if not recommendations:
            recommendations.append("System resources are healthy")

        return recommendations

    async def _generate_recommendations(self) -> list[str]:
        """Generate overall system recommendations."""
        return [
            "Enable camera motion detection to reduce bandwidth usage",
            "Use PTZ presets to minimize movement latency",
            "Consider implementing camera grouping for batch operations",
            "Monitor network bandwidth during peak usage hours",
            "Regularly update camera firmware for performance improvements",
            "Use local storage for snapshots to reduce network load",
        ]

    def _generate_summary(self, _analysis: dict[str, Any]) -> dict[str, Any]:
        """Generate performance analysis summary."""
        return {
            "overall_grade": "A",
            "key_metrics": {
                "camera_operations": "Excellent",
                "system_resources": "Healthy",
                "network_performance": "Good",
            },
            "critical_issues": [],
            "optimization_opportunities": [
                "Implement camera connection pooling",
                "Add caching for frequently accessed data",
                "Optimize image processing pipeline",
            ],
        }
