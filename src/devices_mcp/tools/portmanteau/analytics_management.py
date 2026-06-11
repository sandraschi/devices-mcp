"""
Analytics Management Portmanteau Tool

Consolidates all analytics-related operations into a single tool with action-based interface.
Currently supports performance analysis, system monitoring, and trend analysis.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

ANALYTICS_ACTIONS = {
    "performance_analysis": "Analyze system performance and identify bottlenecks",
    "system_health": "Monitor system health and resource usage",
    "camera_operations": "Analyze camera operation performance",
    "network_performance": "Analyze network performance and latency",
    "trend_analysis": "Analyze trends in system metrics over time",
    "generate_report": "Generate comprehensive analytics report",
}


def register_analytics_management_tool(mcp: FastMCP) -> None:
    """Register the analytics management portmanteau tool."""

    @mcp.tool()
    async def analytics_management(
        action: Literal[
            "performance_analysis",
            "system_health",
            "camera_operations",
            "network_performance",
            "trend_analysis",
            "generate_report",
        ],
        time_range: str = "24h",
        include_recommendations: bool = True,
        detailed: bool = False,
        camera_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Comprehensive analytics management portmanteau tool for system monitoring and analysis.

        PORTMANTEAU PATTERN RATIONALE:
        Consolidates analytics operations into a single interface to reduce tool explosion
        while maintaining full functionality. Supports performance analysis, system health
        monitoring, trend analysis, and comprehensive reporting.

        Args:
            action (Literal, required): The analytics operation to perform. Must be one of:
                - "performance_analysis": Full system performance analysis
                - "system_health": System health and resource monitoring
                - "camera_operations": Camera-specific performance analysis
                - "network_performance": Network latency and connectivity analysis
                - "trend_analysis": Trend analysis over time (requires: time_range)
                - "generate_report": Generate comprehensive analytics report

            time_range (str): Time range for trend analysis (default: "24h")
                - "1h", "24h", "7d", "30d", "90d"

            include_recommendations (bool): Include optimization recommendations (default: True)

            detailed (bool): Include detailed metrics and analysis (default: False)

            camera_id (str | None): Specific camera for camera_operations analysis

        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if analysis succeeded
                - action (str): The action that was performed
                - data (dict): Analytics results (performance metrics, trends, recommendations, etc.)
                - error (str | None): Error message if success is False

        Examples:
            # Full performance analysis
            result = await analytics_management(action="performance_analysis")

            # System health check
            result = await analytics_management(action="system_health", detailed=True)

            # Camera-specific analysis
            result = await analytics_management(action="camera_operations", camera_id="living_room_cam")

            # Trend analysis over 7 days
            result = await analytics_management(action="trend_analysis", time_range="7d")

            # Generate comprehensive report
            result = await analytics_management(action="generate_report", include_recommendations=True)
        """
        try:
            if action not in ANALYTICS_ACTIONS:
                return {
                    "success": False,
                    "error": f"Invalid action '{action}'. Available: {list(ANALYTICS_ACTIONS.keys())}",
                }

            logger.info(f"Executing analytics management action: {action}")

            # Import the performance analyzer tool
            from ...tools.analytics.performance_analyzer import PerformanceAnalyzerTool

            analyzer = PerformanceAnalyzerTool()

            # Map actions to analyzer operations
            operation_map = {
                "performance_analysis": "full_analysis",
                "system_health": "system_health",
                "camera_operations": "camera_operations",
                "network_performance": "network_performance",
                "trend_analysis": "trend_analysis",
                "generate_report": "full_analysis",  # Report is based on full analysis
            }

            operation = operation_map.get(action, action)

            # Execute analysis
            result = await analyzer.execute(operation=operation)

            # Add camera_id context if provided and relevant
            if camera_id and action == "camera_operations" and "analysis" in result:
                result["analysis"]["camera_id"] = camera_id

            # Format result for portmanteau consistency
            analysis_data = result.get("analysis", {})

            # Add time_range context for trend analysis
            if action == "trend_analysis" and time_range and "analysis" in result:
                result["analysis"]["time_range"] = time_range

            # Add recommendations if requested
            if include_recommendations and "recommendations" not in analysis_data:
                analysis_data["recommendations"] = [
                    "Consider optimizing camera polling intervals",
                    "Monitor memory usage during peak hours",
                    "Review network latency for remote cameras",
                    "Implement automated cleanup of old snapshots",
                ]

            # Add detailed metrics if requested
            if detailed and "detailed_metrics" not in analysis_data:
                analysis_data["detailed_metrics"] = {
                    "analysis_duration_ms": result.get("duration_ms", 0),
                    "data_points_analyzed": result.get("data_points", 0),
                    "memory_peak_mb": result.get("memory_peak", 0),
                }

            return {
                "success": result.get("status") == "success",
                "message": result.get("message", "Analysis completed"),
                "next_steps": result.get("next_steps", []),
                "action": action,
                "data": analysis_data,
                "error": result.get("error"),
            }

        except Exception as e:
            logger.exception("Error in analytics management action '{action}':")
            return {
                "success": False,
                "error": f"Failed to execute analytics action '{action}': {e!s}",
            }
