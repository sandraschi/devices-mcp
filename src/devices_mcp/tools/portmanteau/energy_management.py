"""
Energy Management Portmanteau Tool

Consolidates all energy-related operations into a single tool with action-based interface.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

from devices_mcp.tools.energy.energy_management_tool import EnergyManagementTool
from devices_mcp.utils.response_builders import (
    build_hardware_error_response,
    build_success_response,
)

logger = logging.getLogger(__name__)

ENERGY_ACTIONS = {
    "status": "Get smart plug status",
    "control": "Control smart plug (on/off)",
    "consumption": "Get energy consumption data",
    "cost": "Get energy cost analysis",
}


def register_energy_management_tool(mcp: FastMCP) -> None:
    """Register the energy management portmanteau tool."""

    @mcp.tool()
    async def energy_management(
        action: Literal["status", "control", "consumption", "cost"],
        device_id: str | None = None,
        power_state: str | None = None,
        time_range: str = "24h",
    ) -> dict[str, Any]:
        """
        Comprehensive energy management portmanteau tool.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 4+ separate tools (one per operation), this tool consolidates related
        energy operations into a single interface. Prevents tool explosion (4+ tools → 1 tool) while maintaining
        full functionality and improving discoverability. Follows FastMCP 3.1+ best practices.

        Args:
            action (Literal, required): The operation to perform. Must be one of: "status", "control",
                "consumption", "cost".
                - "status": Get smart plug status (optional: device_id for specific device)
                - "control": Control smart plug power (requires: device_id, power_state)
                - "consumption": Get energy consumption data (optional: device_id, time_range)
                - "cost": Get energy cost analysis (optional: device_id, time_range)

            device_id (str | None): Smart plug device ID. Required for: control operation.
                Optional for: status, consumption, cost operations (filters to specific device).

            power_state (str | None): Power state for control. Required for: control operation.
                Valid: "on", "off", "toggle"

            time_range (str): Time range for consumption/cost analysis. Used by: consumption, cost operations.
                Default: "24h". Valid: "1h", "24h", "7d", "30d"

        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data (status, consumption, cost, etc.)
                - error (str | None): Error message if success is False

        Examples:
            # Get status of all devices
            result = await energy_management(action="status")

            # Control specific device
            result = await energy_management(action="control", device_id="tapo_001", power_state="on")

            # Get consumption data
            result = await energy_management(action="consumption", time_range="7d")

            # Get cost analysis
            result = await energy_management(action="cost", device_id="tapo_001", time_range="30d")
        """
        try:
            if action not in ENERGY_ACTIONS:
                return {
                    "success": False,
                    "error": f"Invalid action '{action}'. Available: {list(ENERGY_ACTIONS.keys())}",
                }

            logger.info(f"Executing energy management action: {action}")

            tool = EnergyManagementTool()
            result = await tool.execute(
                operation=action,
                device_id=device_id,
                action=power_state,
                time_range=time_range,
            )

            # Build conversational success response based on action type
            if action == "status":
                device_count = len(result.get("devices", [])) if isinstance(result, dict) else 0
                return build_success_response(
                    operation="energy_status",
                    summary=f"Retrieved status for {device_count} smart plug{'s' if device_count != 1 else ''}",
                    result=result,
                    recommendations=[
                        "Monitor energy usage with 'consumption' action",
                        "Set up automated controls based on device status",
                        "Check cost analysis with 'cost' action for savings",
                    ],
                    next_steps=[
                        "Try 'consumption' to see energy usage patterns",
                        "Use 'control' to manage device power states",
                        "Set up automation based on energy data",
                    ],
                )

            if action == "control":
                state = power_state or result.get("power_state", "unknown")
                return build_success_response(
                    operation="energy_control",
                    summary=f"Smart plug {device_id or 'device'} turned {state}",
                    result=result,
                    recommendations=[
                        "Monitor power consumption after state change",
                        "Set up schedules for automated on/off times",
                        "Check energy cost impact of the change",
                    ],
                    next_steps=[
                        "Check status with 'status' action to confirm change",
                        "Monitor consumption with 'consumption' action",
                        "Set up automation rules for this device",
                    ],
                )

            if action == "consumption":
                return build_success_response(
                    operation="energy_consumption",
                    summary=f"Retrieved energy consumption data for time range: {time_range}",
                    result=result,
                    recommendations=[
                        "Analyze usage patterns for optimization opportunities",
                        "Compare consumption across different time periods",
                        "Check cost analysis with 'cost' action",
                    ],
                    next_steps=[
                        "Run 'cost' analysis to see financial impact",
                        "Set up monitoring alerts for high usage",
                        "Optimize device usage based on consumption data",
                    ],
                )

            if action == "cost":
                return build_success_response(
                    operation="energy_cost_analysis",
                    summary=f"Generated energy cost analysis for time range: {time_range}",
                    result=result,
                    recommendations=[
                        "Identify high-cost devices for optimization",
                        "Set up usage alerts for cost control",
                        "Compare costs across different time periods",
                    ],
                    next_steps=[
                        "Implement energy-saving measures for high-cost devices",
                        "Set up automated controls to reduce costs",
                        "Monitor cost trends over time",
                    ],
                )

            return build_success_response(
                operation=f"energy_{action}",
                summary=f"Energy {action} operation completed successfully",
                result=result,
            )

        except Exception as e:
            logger.exception("Error in energy management action '{action}':")

            # Intelligent error analysis for smart plug issues
            error_str = str(e).lower()
            recovery_options = []

            if "connection" in error_str or "network" in error_str or "unreachable" in error_str:
                recovery_options = [
                    "Check smart plug is powered on and connected to WiFi",
                    "Verify smart plug is on the same network as MCP server",
                    "Check firewall allows communication with smart plug",
                    "Try power cycling the smart plug (unplug for 30 seconds)",
                ]
            elif "authentication" in error_str or "login" in error_str or "credentials" in error_str:
                recovery_options = [
                    "Verify smart plug username/password in configuration",
                    "Check if smart plug was factory reset and needs re-setup",
                    "Ensure you're using the correct device model/API",
                    "Try re-linking the smart plug to your account",
                ]
            elif "device" in error_str or "not found" in error_str:
                recovery_options = [
                    f"Verify device_id '{device_id}' exists and is configured"
                    if device_id
                    else "Provide a valid device_id parameter",
                    "Check device is registered in Tapo app",
                    "Try rescanning for devices in Tapo app",
                    "Ensure device firmware is up to date",
                ]
            else:
                recovery_options = [
                    "Check smart plug status and network connectivity",
                    "Verify device credentials and configuration",
                    "Try restarting the MCP server",
                    "Check smart plug firmware is current",
                ]

            device_info = f" for device '{device_id}'" if device_id else ""
            return build_hardware_error_response(
                error=f"Smart plug operation failed during {action}{device_info}",
                device_type="Smart Plug",
                device_id=device_id or "unknown",
                recovery_options=recovery_options,
                suggestions=[
                    f"Try running energy action '{action}' again after applying recovery steps",
                    "Check device connectivity with 'status' action first",
                    "Verify device configuration in config.yaml",
                ],
            )
