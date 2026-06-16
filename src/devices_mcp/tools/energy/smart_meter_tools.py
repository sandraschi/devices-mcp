"""
Wien Energie Smart Meter Tools for Devices MCP

This module provides MCP tools for monitoring Wien Energie smart meters
via Wiener Netze infrastructure with real-time energy consumption tracking.
"""

import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, Field

from ...ingest import IngestionUnavailableError, WienEnergieIngestionService
from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)

# Global smart meter service instance
_smart_meter_service: WienEnergieIngestionService | None = None


def get_smart_meter_service() -> WienEnergieIngestionService | None:
    """Get or create smart meter service instance."""
    global _smart_meter_service
    if _smart_meter_service is None:
        try:
            _smart_meter_service = WienEnergieIngestionService()
        except IngestionUnavailableError as e:
            logger.warning(f"Smart meter service unavailable: {e}")
            return None
        except Exception:
            logger.exception("Failed to initialize smart meter service:")
            return None
    return _smart_meter_service


@tool("smart_meter_status")
class SmartMeterStatusTool(BaseTool):
    """Get current status and readings from Wien Energie smart meter.

    Retrieves real-time energy consumption data including power, voltage,
    current, and total energy consumption from the smart meter.

    Parameters:
        include_tariff: Whether to include tariff information in response.

    Returns:
        Dictionary with current smart meter status and readings.
    """

    class Meta:
        name = "smart_meter_status"
        description = "Get current status and real-time readings from Wien Energie smart meter"
        category = ToolCategory.ENERGY

        class Parameters(BaseModel):
            include_tariff: bool = Field(False, description="Include tariff information in response")

    async def execute(self, include_tariff: bool = False) -> dict[str, Any]:
        """Execute smart meter status query."""
        try:
            service = get_smart_meter_service()
            if not service:
                return {
                    "success": False,
                    "message": "Smart meter service not available. Check configuration and adapter connection.",
                    "error": "Smart meter service not available. Check configuration and adapter connection.",
                    "timestamp": time.time(),
                }

            # Discover meter if needed
            meter_info = await service.discover_meter()
            if not meter_info:
                return {
                    "success": False,
                    "message": "Unable to discover smart meter. Check adapter connection and security key.",
                    "error": "Unable to discover smart meter. Check adapter connection and security key.",
                    "timestamp": time.time(),
                }

            # Fetch current reading
            reading = await service.fetch_current_reading()
            if not reading:
                return {
                    "success": False,
                    "message": "Unable to fetch current reading from smart meter.",
                    "error": "Unable to fetch current reading from smart meter.",
                    "meter_info": meter_info,
                    "timestamp": time.time(),
                }

            result = {
                "success": True,
                "operation": "status",
                "meter": meter_info,
                "reading": reading,
                "timestamp": time.time(),
            }

            if include_tariff:
                tariff_info = await service.get_tariff_info()
                result["tariff"] = tariff_info

            return result

        except Exception as e:
            logger.exception("Smart meter status query failed")
            return {
                "success": False,
                "message": str(e),
                "error": str(e),
                "timestamp": time.time(),
            }


@tool("smart_meter_consumption")
class SmartMeterConsumptionTool(BaseTool):
    """Get energy consumption data from Wien Energie smart meter.

    Retrieves historical energy consumption data for specified time range.

    Parameters:
        time_range: Time range for consumption data (1h, 24h, 7d, 30d).
        start_date: Optional start date (ISO format).
        end_date: Optional end date (ISO format).

    Returns:
        Dictionary with energy consumption data and statistics.
    """

    class Meta:
        name = "smart_meter_consumption"
        description = "Get energy consumption data from Wien Energie smart meter"
        category = ToolCategory.ENERGY

        class Parameters(BaseModel):
            time_range: str | None = Field("24h", description="Time range: '1h', '24h', '7d', '30d'")
            start_date: str | None = Field(None, description="Start date (ISO format)")
            end_date: str | None = Field(None, description="End date (ISO format)")

    async def execute(
        self,
        time_range: str = "24h",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Execute consumption query."""
        try:
            service = get_smart_meter_service()
            if not service:
                return {
                    "success": False,
                    "message": "Smart meter service not available.",
                    "error": "Smart meter service not available.",
                    "timestamp": time.time(),
                }

            # Parse time range or dates
            if start_date and end_date:
                start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            else:
                end = datetime.now(UTC)
                if time_range == "1h":
                    start = end - timedelta(hours=1)
                elif time_range == "24h":
                    start = end - timedelta(hours=24)
                elif time_range == "7d":
                    start = end - timedelta(days=7)
                elif time_range == "30d":
                    start = end - timedelta(days=30)
                else:
                    start = end - timedelta(hours=24)

            # Fetch historical data
            history = await service.fetch_historical_data(start, end)

            # Calculate statistics
            total_energy = sum(point.get("daily_energy_kwh", 0) or point.get("energy_kwh", 0) for point in history)
            avg_power = sum(point.get("power_w", 0) or 0 for point in history) / len(history) if history else 0

            return {
                "success": True,
                "operation": "consumption",
                "time_range": time_range,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "data_points": len(history),
                "total_energy_kwh": total_energy,
                "average_power_w": avg_power,
                "history": history,
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception("Smart meter consumption query failed")
            return {
                "success": False,
                "message": str(e),
                "error": str(e),
                "timestamp": time.time(),
            }


@tool("smart_meter_cost")
class SmartMeterCostTool(BaseTool):
    """Calculate energy cost based on Wien Energie tariffs.

    Calculates energy costs for specified consumption using current tariff rates.

    Parameters:
        energy_kwh: Energy consumption in kWh.
        time_range: Time range for cost calculation (1h, 24h, 7d, 30d).
        timestamp: Optional timestamp for time-based tariff calculation.

    Returns:
        Dictionary with cost calculation and tariff information.
    """

    class Meta:
        name = "smart_meter_cost"
        description = "Calculate energy cost based on Wien Energie tariffs"
        category = ToolCategory.ENERGY

        class Parameters(BaseModel):
            energy_kwh: float | None = Field(None, description="Energy consumption in kWh")
            time_range: str | None = Field("24h", description="Time range: '1h', '24h', '7d', '30d'")
            timestamp: str | None = Field(None, description="Timestamp for tariff calculation")

    async def execute(
        self,
        energy_kwh: float | None = None,
        time_range: str = "24h",
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Execute cost calculation."""
        try:
            service = get_smart_meter_service()
            if not service:
                return {
                    "success": False,
                    "message": "Smart meter service not available.",
                    "error": "Smart meter service not available.",
                    "timestamp": time.time(),
                }

            # Get tariff info
            tariff_info = await service.get_tariff_info()

            # If energy_kwh not provided, get from current reading
            if energy_kwh is None:
                reading = await service.fetch_current_reading()
                if reading:
                    # Calculate energy for time range
                    if time_range == "1h":
                        energy_kwh = reading.get("active_power_w", 0) / 1000.0
                    elif time_range == "24h":
                        energy_kwh = reading.get("daily_energy_kwh", 0)
                    elif time_range == "7d":
                        energy_kwh = reading.get("daily_energy_kwh", 0) * 7
                    elif time_range == "30d":
                        energy_kwh = reading.get("daily_energy_kwh", 0) * 30
                    else:
                        energy_kwh = reading.get("daily_energy_kwh", 0)
                else:
                    return {
                        "success": False,
                        "message": "Unable to fetch current reading. Please provide energy_kwh parameter.",
                        "error": "Unable to fetch current reading. Please provide energy_kwh parameter.",
                        "timestamp": time.time(),
                    }

            # Calculate cost
            ts = None
            if timestamp:
                ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            cost = service.calculate_energy_cost(energy_kwh, ts)

            return {
                "success": True,
                "operation": "cost",
                "energy_kwh": energy_kwh,
                "time_range": time_range,
                "cost_eur": cost,
                "tariff": tariff_info,
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception("Smart meter cost calculation failed")
            return {
                "success": False,
                "message": str(e),
                "error": str(e),
                "timestamp": time.time(),
            }
