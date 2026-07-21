"""
Kitchen Management Portmanteau Tool
Consolidates all kitchen appliance operations into a single tool with action-based interface.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

_READ_ONLY: dict[str, bool] = {"readonly": True}
_MUTATING: dict[str, bool] = {}
_DESTRUCTIVE: dict[str, bool] = {"destructive": True}

from devices_mcp.tools.energy.tapo_plug_tools import tapo_plug_manager

logger = logging.getLogger(__name__)
KITCHEN_ACTIONS = {
    "list_appliances": "List all kitchen appliances",
    "control_appliance": "Control kitchen appliance via smart plug (on/off)",
    "get_appliance_status": "Get appliance status and power consumption",
    "get_energy_usage": "Get energy usage for kitchen appliances",
}


def register_kitchen_management_tool(mcp: FastMCP) -> None:
    """Register the kitchen management portmanteau tool."""

    @mcp.tool(annotations=_READ_ONLY)
    async def kitchen_management(
        action: Literal["list_appliances", "control_appliance", "get_appliance_status", "get_energy_usage"],
        device_id: str | None = None,
        power_state: str | None = None,
        time_range: str = "24h",
    ) -> dict[str, Any]:
        """
        Comprehensive kitchen appliance management portmanteau tool.
        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 4+ separate tools (one per operation), this tool consolidates related
        kitchen operations into a single interface. Prevents tool explosion (4+ tools → 1 tool) while maintaining
        full functionality and improving discoverability. Follows FastMCP 3.1+ best practices.
        Currently supports appliances connected via Tapo P115 smart plugs:
        - Zojirushi Water Boiler & Warmer (on/off control, energy monitoring)
        - Tefal Optigrill (on/off control via smart plug, no temperature control)
        - Any other appliance connected to a Tapo P115 smart plug
        Args:
            action (Literal, required): The operation to perform. Must be one of:
                - "list_appliances": List all kitchen appliances (connected via smart plugs)
                - "control_appliance": Control appliance power (requires: device_id, power_state)
                - "get_appliance_status": Get appliance status and power consumption (requires: device_id)
                - "get_energy_usage": Get energy usage data (optional: device_id, time_range)
            device_id (str | None): Smart plug device ID. Required for: control_appliance, get_appliance_status operations.
                Optional for: get_energy_usage operation (filters to specific device).
            power_state (str | None): Power state for control. Required for: control_appliance operation.
                Valid: "on", "off", "toggle"
            time_range (str): Time range for energy usage. Used by: get_energy_usage operation.
                Default: "24h". Valid: "1h", "24h", "7d", "30d"
        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data
                - error (str | None): Error message if success is False
        Examples:
            # List all kitchen appliances
            result = await kitchen_management(action="list_appliances")
            # Turn on Zojirushi kettle
            result = await kitchen_management(action="control_appliance", device_id="kitchen_zojirushi", power_state="on")
            # Get appliance status
            result = await kitchen_management(action="get_appliance_status", device_id="kitchen_zojirushi")
            # Get energy usage for all kitchen appliances
            result = await kitchen_management(action="get_energy_usage", time_range="7d")
        """
        try:
            if action not in KITCHEN_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(KITCHEN_ACTIONS.keys())}",
                }
            logger.info(f"Executing kitchen management action: {action}")
            # Get all devices and filter to kitchen appliances
            # Kitchen appliances are identified by device name or location
            all_devices = await tapo_plug_manager.get_all_devices()
            kitchen_keywords = ["kitchen", "zojirushi", "kettle", "optigrill", "grill"]
            kitchen_devices = [
                device
                for device in all_devices
                if any(keyword.lower() in device.name.lower() for keyword in kitchen_keywords)
            ]
            if action == "list_appliances":
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "appliances": [
                            {
                                "device_id": device.device_id,
                                "name": device.name,
                                "power_state": device.power_state,
                                "power_watt": device.current_power,
                                "voltage": device.voltage,
                                "current": device.current,
                                "readonly": tapo_plug_manager.is_device_readonly(device.device_id),
                            }
                            for device in kitchen_devices
                        ],
                        "count": len(kitchen_devices),
                    },
                }
            if action == "control_appliance":
                if not device_id:
                    return {
                        "success": False,
                        "message": "device_id is required for control_appliance action",
                        "error": "device_id is required for control_appliance action",
                    }
                if not power_state:
                    return {
                        "success": False,
                        "message": "power_state is required for control_appliance action",
                        "error": "power_state is required for control_appliance action",
                    }
                if power_state not in ["on", "off", "toggle"]:
                    return {
                        "success": False,
                        "message": f"Invalid power_state '{power_state}'. Valid: 'on', 'off', 'toggle'",
                    }
                # Check if device is in kitchen
                device = await tapo_plug_manager.get_device_status(device_id)
                if not device:
                    return {
                        "success": False,
                        "message": f"Device {device_id} not found",
                        "error": f"Device {device_id} not found",
                    }
                is_kitchen = any(keyword.lower() in device.name.lower() for keyword in kitchen_keywords)
                if not is_kitchen:
                    return {
                        "success": False,
                        "message": f"Device {device_id} is not identified as a kitchen appliance",
                    }
                # Control device
                turn_on = None
                if power_state == "on":
                    turn_on = True
                elif power_state == "off":
                    turn_on = False
                elif power_state == "toggle":
                    turn_on = not device.power_state
                success = await tapo_plug_manager.toggle_device(device_id, turn_on)
                if success:
                    # Get updated status
                    updated_device = await tapo_plug_manager.get_device_status(device_id)
                    return {
                        "success": True,
                        "action": action,
                        "data": {
                            "device_id": device_id,
                            "power_state": updated_device.power_state if updated_device else turn_on,
                            "message": f"Appliance turned {'ON' if turn_on else 'OFF'}",
                        },
                    }
                return {
                    "success": False,
                    "message": "Failed to control appliance",
                    "error": "Failed to control appliance",
                }
            if action == "get_appliance_status":
                if not device_id:
                    return {
                        "success": False,
                        "message": "device_id is required for get_appliance_status action",
                        "error": "device_id is required for get_appliance_status action",
                    }
                device = await tapo_plug_manager.get_device_status(device_id)
                if not device:
                    return {
                        "success": False,
                        "message": f"Device {device_id} not found",
                        "error": f"Device {device_id} not found",
                    }
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "device_id": device.device_id,
                        "name": device.name,
                        "power_state": device.power_state,
                        "power_watt": device.current_power,
                        "voltage": device.voltage,
                        "current": device.current,
                        "daily_energy": device.daily_energy,
                        "monthly_energy": device.monthly_energy,
                        "readonly": tapo_plug_manager.is_device_readonly(device.device_id),
                    },
                }
            if action == "get_energy_usage":
                # Use energy_management tool for this
                from devices_mcp.tools.energy.energy_management_tool import EnergyManagementTool

                tool = EnergyManagementTool()
                result = await tool.execute(
                    operation="consumption",
                    device_id=device_id,
                    time_range=time_range,
                )
                return {
                    "success": True,
                    "action": action,
                    "data": result,
                }
            return {
                "success": False,
                "message": f"Action '{action}' not implemented",
                "error": f"Action '{action}' not implemented",
            }
        except Exception as e:
            logger.exception("Error in kitchen management action '{action}':")
            return {
                "success": False,
                "message": f"Failed to execute action '{action}': {e!s}",
                "error": f"Failed to execute action '{action}': {e!s}",
            }
