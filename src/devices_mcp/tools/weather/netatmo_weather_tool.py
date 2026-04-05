"""
Netatmo Weather Portmanteau Tool

Combines Netatmo weather operations:
- Get Netatmo stations
- Get Netatmo weather data
"""

import logging
import time
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


@tool("netatmo_weather")
class NetatmoWeatherTool(BaseTool):
    """Netatmo weather data tool.

    Provides unified Netatmo weather operations including station information
    and current weather data retrieval.

    Parameters:
        operation: Type of weather operation (stations, data).
        station_id: Station ID for data operation (optional).

    Returns:
        A dictionary containing the Netatmo weather result.
    """

    class Meta:
        name = "netatmo_weather"
        description = (
            "Unified Netatmo weather operations including station info and current weather data"
        )
        category = ToolCategory.WEATHER

        class Parameters(BaseModel):
            operation: str = Field(..., description="Weather operation: 'stations', 'data'")
            station_id: Optional[str] = Field(None, description="Station ID for data operation")

    async def execute(
        self,
        operation: str,
        station_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute Netatmo weather operation."""
        try:
            logger.info(f"Netatmo weather {operation} operation")

            if operation == "stations":
                return await self._get_stations()
            if operation == "data":
                return await self._get_weather_data(station_id)
            return {
                "success": False,
                "error": f"Invalid operation: {operation}. Must be 'stations' or 'data'",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception(f"Netatmo weather {operation} operation failed")
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "timestamp": time.time(),
            }

    async def _get_stations(self) -> Dict[str, Any]:
        """Get Netatmo weather stations from real API if available."""
        # Try to get real Netatmo stations using singleton
        try:
            from ...integrations.netatmo_client import NetatmoService

            service = await NetatmoService.get_instance()

            if service._use_real_api:
                # Get real stations from Netatmo API
                real_stations = await service.list_stations()

                if real_stations:
                    # Convert to expected format
                    stations = []
                    for station in real_stations:
                        station_data = {
                            "station_id": station.get("station_id"),
                            "name": station.get("station_name", "Weather Station"),
                            "location": station.get("location", "Unknown"),
                            "type": "indoor",  # Main station is always indoor
                            "modules": [],
                            "last_update": station.get("last_update", time.time()),
                        }

                        # Add modules (only real ones - no fake outdoor module)
                        for module in station.get("modules", []):
                            station_data["modules"].append(
                                {
                                    "module_id": module.get("module_id"),
                                    "name": module.get("module_name"),
                                    "type": module.get("module_type", "indoor"),
                                    "battery_level": module.get("battery_percent"),
                                    "signal_strength": None,  # Not available in API response
                                }
                            )

                        stations.append(station_data)

                    total_modules = sum(len(station["modules"]) for station in stations)

                    return {
                        "success": True,
                        "operation": "stations",
                        "stations": stations,
                        "total_stations": len(stations),
                        "total_modules": total_modules,
                        "message": f"Found {len(stations)} Netatmo stations with {total_modules} modules",
                        "timestamp": time.time(),
                    }
        except Exception as e:
            logger.warning(f"Failed to get real Netatmo stations: {e}")

        # If Netatmo is not available, return empty list (no fake stations)
        return {
            "success": True,
            "operation": "stations",
            "stations": [],
            "total_stations": 0,
            "total_modules": 0,
            "message": "No Netatmo stations available (Netatmo API not configured or unavailable)",
            "timestamp": time.time(),
        }

    async def _get_weather_data(self, station_id: Optional[str]) -> Dict[str, Any]:
        """Get Netatmo weather data from real API if available, otherwise return minimal data."""
        station_id = station_id or "netatmo_001"

        # Try to get real Netatmo data using singleton
        try:
            from ...integrations.netatmo_client import NetatmoService

            service = await NetatmoService.get_instance()

            if service._use_real_api:
                # Get real data from Netatmo API
                data, timestamp = await service.current_data(station_id, "all")

                if data:
                    weather_data = {
                        "station_id": station_id,
                        "timestamp": timestamp,
                    }

                    # Add indoor data if available
                    if "indoor" in data:
                        weather_data["indoor"] = {
                            "temperature": data["indoor"].get("temperature"),
                            "humidity": data["indoor"].get("humidity"),
                            "co2": data["indoor"].get("co2"),
                            "noise": data["indoor"].get("noise"),
                            "pressure": data["indoor"].get("pressure"),
                            "health_index": "Good"
                            if data["indoor"].get("co2", 1000) < 1000
                            else "Fair",
                        }

                    # Only add outdoor data if it actually exists (real outdoor module)
                    if data.get("outdoor"):
                        weather_data["outdoor"] = {
                            "temperature": data["outdoor"].get("temperature"),
                            "humidity": data["outdoor"].get("humidity"),
                            # Note: Netatmo outdoor modules don't have wind/rain/UV - those require separate modules
                            # Only include if we actually have those modules
                        }
                    # If no outdoor module exists, don't include outdoor data at all

                    # Add extra indoor modules if available (e.g., bathroom)
                    if data.get("extra_indoor"):
                        weather_data["extra_indoor"] = data["extra_indoor"]

                    return {
                        "success": True,
                        "operation": "data",
                        "weather_data": weather_data,
                        "message": f"Weather data retrieved for station {station_id}",
                        "timestamp": timestamp,
                    }
                logger.warning(f"No data returned from Netatmo API for station {station_id}")
        except Exception as e:
            logger.warning(f"Failed to get real Netatmo data: {e}")

        # If Netatmo is not available or failed, return minimal indoor-only data
        # DO NOT generate fake outdoor data
        weather_data = {
            "station_id": station_id,
            "timestamp": time.time(),
            "indoor": {
                "temperature": None,
                "humidity": None,
                "co2": None,
                "noise": None,
                "pressure": None,
                "health_index": "No Data",
            },
            # Explicitly omit outdoor data - don't generate fake values
        }

        return {
            "success": True,
            "operation": "data",
            "weather_data": weather_data,
            "message": f"Weather data retrieved for station {station_id} (Netatmo API unavailable - no outdoor data)",
            "timestamp": time.time(),
        }
