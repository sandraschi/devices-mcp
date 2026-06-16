"""
Energy Management Portmanteau Tool

Combines energy monitoring and control operations:
- Get smart plug status
- Control smart plugs (on/off)
- Get energy consumption data
- Get energy cost analysis
"""

import logging
import time
from typing import Any

from pydantic import BaseModel, Field

from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


@tool("energy_management")
class EnergyManagementTool(BaseTool):
    """Comprehensive energy management tool.

    Provides unified control for energy monitoring including smart plug status,
    control operations, consumption tracking, and cost analysis.

    Parameters:
        operation: Type of energy operation (status, control, consumption, cost).
        device_id: ID of the smart plug device (optional for status).
        action: Control action (on, off, toggle) for control operation.
        time_range: Time range for consumption/cost analysis (1h, 24h, 7d, 30d).

    Returns:
        A dictionary containing the energy operation result.
    """

    class Meta:
        name = "energy_management"
        description = (
            "Unified energy management for smart plugs including status, control, consumption, and cost analysis"
        )
        category = ToolCategory.ENERGY

        class Parameters(BaseModel):
            operation: str = Field(..., description="Energy operation: 'status', 'control', 'consumption', 'cost'")
            device_id: str | None = Field(None, description="Smart plug device ID")
            action: str | None = Field(None, description="Control action: 'on', 'off', 'toggle'")
            time_range: str | None = Field("24h", description="Time range for analysis: '1h', '24h', '7d', '30d'")

    async def execute(
        self,
        operation: str,
        device_id: str | None = None,
        action: str | None = None,
        time_range: str = "24h",
    ) -> dict[str, Any]:
        """Execute energy management operation."""
        try:
            logger.info(f"Energy {operation} operation")

            if operation == "status":
                return await self._get_status(device_id)
            if operation == "control":
                return await self._control_device(device_id, action)
            if operation == "consumption":
                return await self._get_consumption(time_range)
            if operation == "cost":
                return await self._get_cost_analysis(time_range)
            return {
                "success": False,
                "message": f"Invalid operation: {operation}. Must be 'status', 'control', 'consumption', or 'cost'",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception(f"Energy {operation} operation failed")
            return {
                "success": False,
                "message": str(e),
                "error": str(e),
                "operation": operation,
                "timestamp": time.time(),
            }

    async def _get_status(self, device_id: str | None) -> dict[str, Any]:
        """Get smart plug status from real devices."""
        try:
            # Import the Tapo plug manager
            from devices_mcp.config import get_config
            from devices_mcp.tools.energy.tapo_plug_tools import tapo_plug_manager

            # Get all devices from the manager
            devices_data = []
            devices = tapo_plug_manager.devices

            if not devices:
                # If no devices loaded, try to initialize with account credentials
                config = get_config()
                energy_cfg = config.get("energy", {}).get("tapo_p115", {})
                account = energy_cfg.get("account", {})
                if account.get("email") and account.get("password"):
                    await tapo_plug_manager.initialize(account)

            devices = tapo_plug_manager.devices

            for _device_id_key, device in devices.items():
                devices_data.append(
                    {
                        "device_id": device.device_id,
                        "name": device.name,
                        "location": device.location,
                        "is_on": device.power_state,
                        "power": device.current_power,
                        "voltage": device.voltage,
                        "current": device.current,
                        "daily_energy": device.daily_energy,
                        "monthly_energy": device.monthly_energy,
                        "daily_cost": device.daily_cost,
                        "monthly_cost": device.monthly_cost,
                        "last_seen": device.last_seen,
                        "automation_enabled": device.automation_enabled,
                        "energy_monitoring": device.energy_monitoring,
                        "power_schedule": device.power_schedule,
                        "energy_saving_mode": device.energy_saving_mode,
                        "timestamp": time.time(),
                    }
                )

            if device_id:
                device = next((d for d in devices_data if d["device_id"] == device_id), None)
                if not device:
                    return {
                        "success": False,
                        "message": f"Device {device_id} not found",
                        "available_devices": [d["device_id"] for d in devices_data],
                        "timestamp": time.time(),
                    }
                return {
                    "success": True,
                    "device": device,
                    "timestamp": time.time(),
                }

            return {
                "success": True,
                "devices": devices_data,
                "total_devices": len(devices_data),
                "online_devices": len([d for d in devices_data if d.get("is_on", False)]),
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception("Failed to get real device status")
            return {
                "success": False,
                "error": f"Tapo smart plug service unavailable: {e!s}",
                "service_status": "offline",
                "message": "Cannot retrieve real-time energy monitoring data. Tapo smart plug integration is currently unavailable.",
                "timestamp": time.time(),
            }

    async def _control_device(self, device_id: str | None, action: str | None) -> dict[str, Any]:
        """Control smart plug device."""
        if not device_id:
            return {
                "success": False,
                "message": "Device ID is required for control operation",
                "error": "Device ID is required for control operation",
                "timestamp": time.time(),
            }

        if not action:
            return {
                "success": False,
                "message": "Action is required for control operation",
                "error": "Action is required for control operation",
                "timestamp": time.time(),
            }

        valid_actions = ["on", "off", "toggle"]
        if action not in valid_actions:
            return {
                "success": False,
                "message": f"Invalid action: {action}. Must be one of: {valid_actions}",
                "timestamp": time.time(),
            }

        # Control real Tapo plug devices
        try:
            from devices_mcp.tools.energy.tapo_plug_tools import tapo_plug_manager

            # Get device
            devices = tapo_plug_manager.devices
            if device_id not in devices:
                return {
                    "success": False,
                    "message": f"Device {device_id} not found",
                    "available_devices": list(devices.keys()),
                    "timestamp": time.time(),
                }

            device = devices[device_id]

            # Perform control action
            if action == "on":
                new_state = True
            elif action == "off":
                new_state = False
            elif action == "toggle":
                new_state = not device.power_state
            else:
                return {
                    "success": False,
                    "message": f"Invalid action: {action}",
                    "timestamp": time.time(),
                }

            # Use the tapo_plug_manager to control the device
            success = await tapo_plug_manager.control_device(device_id, new_state)

            if success:
                return {
                    "success": True,
                    "operation": "control",
                    "device_id": device_id,
                    "device_name": device.name,
                    "location": device.location,
                    "action": action,
                    "new_state": new_state,
                    "message": f"Device {device.name} ({device_id}) turned {'on' if new_state else 'off'}",
                    "timestamp": time.time(),
                }
            return {
                "success": False,
                "message": f"Failed to control device {device_id}",
                "device_id": device_id,
                "action": action,
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception("Failed to control device")
            return {
                "success": False,
                "error": f"Device control unavailable: {e!s}",
                "service_status": "offline",
                "device_id": device_id,
                "action": action,
                "message": f"Cannot control device {device_id}. Tapo smart plug integration is currently unavailable.",
                "timestamp": time.time(),
            }

    async def _get_consumption(self, time_range: str) -> dict[str, Any]:
        """Get energy consumption data from real devices."""
        try:
            # Import the Tapo plug manager
            from devices_mcp.config import get_config
            from devices_mcp.tools.energy.tapo_plug_tools import tapo_plug_manager

            # Get electricity rate from config
            config = get_config()
            electricity_rate = config.get("energy", {}).get("electricity_rate_eur_per_kwh", 0.30)

            # Get devices
            devices = tapo_plug_manager.devices
            if not devices:
                energy_cfg = config.get("energy", {}).get("tapo_p115", {})
                account = energy_cfg.get("account", {})
                if account.get("email") and account.get("password"):
                    await tapo_plug_manager.initialize(account)
                devices = tapo_plug_manager.devices

            # Calculate time range
            now = time.time()
            if time_range == "1h":
                start_time = now - 3600
                interval_hours = 1 / 12  # 5 min intervals
                points = 12
            elif time_range == "24h":
                start_time = now - 86400
                interval_hours = 1
                points = 24
            elif time_range == "7d":
                start_time = now - 604800
                interval_hours = 24
                points = 7
            elif time_range == "30d":
                start_time = now - 2592000
                interval_hours = 24
                points = 30
            else:
                return {
                    "success": False,
                    "message": f"Invalid time range: {time_range}. Must be one of: 1h, 24h, 7d, 30d",
                    "timestamp": time.time(),
                }

            # Aggregate consumption data from all devices
            total_consumption = 0.0
            device_consumption_data = []

            for _device_id, device in devices.items():
                # Use device's daily/monthly data based on time range
                if time_range == "24h":
                    device_consumption = device.daily_energy
                elif time_range in ["7d", "30d"]:
                    device_consumption = device.monthly_energy * (7 if time_range == "7d" else 30) / 30
                else:  # 1h
                    device_consumption = device.daily_energy / 24

                total_consumption += device_consumption

                device_consumption_data.append(
                    {
                        "device_id": device.device_id,
                        "device_name": device.name,
                        "location": device.location,
                        "consumption_kwh": device_consumption,
                        "cost_eur": device_consumption * electricity_rate,
                    }
                )

            # Generate time series data points (simplified)
            consumption_data = []
            interval_seconds = interval_hours * 3600

            for i in range(points):
                timestamp = start_time + (i * interval_seconds)
                point_consumption = total_consumption / points
                consumption_data.append(
                    {
                        "timestamp": timestamp,
                        "consumption_kwh": round(point_consumption, 3),
                        "cost_eur": round(point_consumption * electricity_rate, 2),
                        "formatted_time": f"Point {i + 1}",
                    }
                )

            return {
                "success": True,
                "operation": "consumption",
                "time_range": time_range,
                "total_consumption_kwh": total_consumption,
                "total_cost_eur": round(total_consumption * electricity_rate, 2),
                "device_breakdown": device_consumption_data,
                "data_points": len(consumption_data),
                "consumption_data": consumption_data,
                "devices_count": len(devices),
                "electricity_rate_eur_per_kwh": electricity_rate,
                "message": f"Energy consumption for {time_range}: {round(total_consumption, 2)} kWh ({round(total_consumption * electricity_rate, 2)} EUR) from {len(devices)} devices",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception("Failed to get real consumption data")
            return {
                "success": False,
                "error": f"Energy consumption data unavailable: {e!s}",
                "service_status": "offline",
                "time_range": time_range,
                "message": f"Cannot retrieve energy consumption data for {time_range}. Tapo smart plug integration is currently unavailable.",
                "timestamp": time.time(),
            }

    async def _get_cost_analysis(self, time_range: str) -> dict[str, Any]:
        """Get energy cost analysis from real devices."""
        try:
            # Import the Tapo plug manager
            from devices_mcp.config import get_config
            from devices_mcp.tools.energy.tapo_plug_tools import tapo_plug_manager

            # Get devices
            devices = tapo_plug_manager.devices
            if not devices:
                config = get_config()
                energy_cfg = config.get("energy", {}).get("tapo_p115", {})
                account = energy_cfg.get("account", {})
                if account.get("email") and account.get("password"):
                    await tapo_plug_manager.initialize(account)
                devices = tapo_plug_manager.devices

            # Get electricity rate from config (in euros per kWh)
            electricity_rate = config.get("energy", {}).get("electricity_rate_eur_per_kwh", 0.30)

            # Calculate costs based on device consumption data
            total_cost = 0.0
            cost_by_device = []

            for _device_id, device in devices.items():
                # Use appropriate consumption data based on time range
                if time_range == "24h":
                    consumption = device.daily_energy
                elif time_range in ["7d", "30d"]:
                    consumption = device.monthly_energy * (7 if time_range == "7d" else 30) / 30
                else:  # 1h
                    consumption = device.daily_energy / 24

                # Calculate cost using configured electricity rate in euros
                cost = consumption * electricity_rate
                total_cost += cost

                cost_by_device.append(
                    {
                        "device": device.name,
                        "device_id": device.device_id,
                        "location": device.location,
                        "consumption_kwh": consumption,
                        "cost_eur": cost,
                    }
                )

            # Calculate savings potential (15% reduction)
            savings_potential = total_cost * 0.15

            return {
                "success": True,
                "operation": "cost",
                "time_range": time_range,
                "total_cost_eur": round(total_cost, 2),
                "electricity_rate_eur_per_kwh": electricity_rate,
                "cost_by_device": cost_by_device,
                "devices_count": len(devices),
                "savings_potential_eur": round(savings_potential, 2),
                "message": f"Energy cost for {time_range}: {round(total_cost, 2)} EUR from {len(devices)} devices",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception("Failed to get real cost analysis")
            return {
                "success": False,
                "error": f"Energy cost analysis unavailable: {e!s}",
                "service_status": "offline",
                "time_range": time_range,
                "message": f"Cannot calculate energy costs for {time_range}. Tapo smart plug integration is currently unavailable.",
                "timestamp": time.time(),
            }
