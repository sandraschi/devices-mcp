"""
Weather Management Portmanteau Tool
Consolidates all weather-related operations into a single tool with action-based interface.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

_READ_ONLY: dict[str, bool] = {"readonly": True}
_MUTATING: dict[str, bool] = {}
_DESTRUCTIVE: dict[str, bool] = {"destructive": True}

from devices_mcp.tools.weather.netatmo_analysis_tool import NetatmoAnalysisTool
from devices_mcp.tools.weather.netatmo_weather_tool import NetatmoWeatherTool

logger = logging.getLogger(__name__)
WEATHER_ACTIONS = {
    "current": "Get current weather data",
    "historical": "Get historical weather data",
    "stations": "List weather stations",
    "alerts": "Configure weather alerts",
    "health": "Get weather station health",
    "analyze": "Analyze weather patterns",
}


def register_weather_management_tool(mcp: FastMCP) -> None:
    """Register the weather management portmanteau tool."""

    @mcp.tool(annotations=_READ_ONLY)
    async def weather_management(
        action: Literal["current", "historical", "stations", "alerts", "health", "analyze"],
        station_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        alert_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Comprehensive weather management portmanteau tool.
        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 6+ separate tools (one per operation), this tool consolidates related
        weather operations into a single interface. Prevents tool explosion (6+ tools → 1 tool) while maintaining
        full functionality and improving discoverability. Follows FastMCP 3.1+ best practices.
        Args:
            action (Literal, required): The operation to perform. Must be one of: "current", "historical",
                "stations", "alerts", "health", "analyze".
                - "current": Get current weather data (optional: station_id)
                - "historical": Get historical weather data (requires: start_date, end_date, optional: station_id)
                - "stations": List weather stations (no other parameters required)
                - "alerts": Configure weather alerts (optional: alert_config)
                - "health": Get weather station health (optional: station_id)
                - "analyze": Analyze weather patterns (requires: start_date, end_date, optional: station_id)
            station_id (str | None): Weather station ID. Used by: current, historical, health, analyze operations
                to filter to specific station.
            start_date (str | None): Start date for historical data. Required for: historical, analyze operations.
                Format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
            end_date (str | None): End date for historical data. Required for: historical, analyze operations.
                Format: "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
            alert_config (dict[str, Any] | None): Alert configuration. Used by: alerts operation.
                Required keys: "thresholds" (dict), "conditions" (list).
                Optional keys: "enabled" (bool), "notifications" (list)
        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data (weather data, stations, alerts, etc.)
                - error (str | None): Error message if success is False
        Examples:
            # Get current weather
            result = await weather_management(action="current", station_id="station_001")
            # Get historical data
            result = await weather_management(action="historical", start_date="2024-01-01", end_date="2024-01-31")
            # List stations
            result = await weather_management(action="stations")
            # Analyze patterns
            result = await weather_management(action="analyze", start_date="2024-01-01", end_date="2024-01-31")
        """
        try:
            if action not in WEATHER_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(WEATHER_ACTIONS.keys())}",
                }
            logger.info(f"Executing weather management action: {action}")
            if action == "stations":
                tool = NetatmoWeatherTool()
                result = await tool.execute(
                    operation="stations",
                    station_id=station_id,
                )
                return {"success": True, "action": action, "data": result}
            if action == "current":
                tool = NetatmoWeatherTool()
                result = await tool.execute(
                    operation="data",
                    station_id=station_id,
                )
                return {"success": True, "action": action, "data": result}
            if action in ["historical", "alerts", "health"]:
                # These operations are not yet implemented in NetatmoWeatherTool
                return {
                    "success": False,
                    "message": f"Action '{action}' is not yet implemented. Available actions: current, stations, analyze",
                }
            if action == "analyze":
                tool = NetatmoAnalysisTool()
                result = await tool.execute(
                    station_id=station_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                return {"success": True, "action": action, "data": result}
            return {
                "success": False,
                "message": f"Action '{action}' not implemented",
                "error": f"Action '{action}' not implemented",
            }
        except Exception as e:
            logger.exception("Error in weather management action '{action}':")
            return {
                "success": False,
                "message": f"Failed to execute action '{action}': {e!s}",
                "error": f"Failed to execute action '{action}': {e!s}",
            }
