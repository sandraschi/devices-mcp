"""
iKettle Management Portmanteau Tool
Consolidates all Smarter iKettle operations into a single tool with action-based interface.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

_READ_ONLY: dict[str, bool] = {"readonly": True}
_MUTATING: dict[str, bool] = {}
_DESTRUCTIVE: dict[str, bool] = {"destructive": True}

from devices_mcp.config import get_config
from devices_mcp.integrations.ikettle_client import IKettleClient

logger = logging.getLogger(__name__)
IKETTLE_ACTIONS = {
    "status": "Get kettle status",
    "boil": "Start boiling water",
    "keep_warm": "Start keep warm mode",
    "stop": "Stop current operation",
    "set_mode": "Set kettle mode (wake_up, home, formula)",
}


def register_ikettle_management_tool(mcp: FastMCP) -> None:
    """Register the iKettle management portmanteau tool."""

    @mcp.tool(annotations=_MUTATING)
    async def ikettle_management(
        action: Literal["status", "boil", "keep_warm", "stop", "set_mode"],
        temperature: int = 100,
        duration: int = 30,
        mode: Literal["wake_up", "home", "formula"] = "home",
    ) -> dict[str, Any]:
        """
        Comprehensive iKettle management portmanteau tool.
        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 5+ separate tools (one per operation), this tool consolidates related
        iKettle operations into a single interface. Prevents tool explosion (5+ tools -> 1 tool) while maintaining
        full functionality and improving discoverability. Follows FastMCP 3.1+ best practices.
        Args:
            action (Literal, required): The operation to perform. Must be one of: "status", "boil",
                "keep_warm", "stop", "set_mode".
                - "status": Get current kettle status, water level, and temperature.
                - "boil": Start boiling water to specified temperature (Celsius).
                - "keep_warm": Set keep warm mode to specified temperature and duration.
                - "stop": Stop any current operation (boil or keep warm).
                - "set_mode": Set the kettle mode.
            temperature (int): Target temperature in Celsius. Used by: boil, keep_warm.
                Default: 100 (for boil), 95 (for keep_warm). Range: 20-100.
            duration (int): Duration in minutes for keep warm mode. Used by: keep_warm.
                Default: 30.
            mode (Literal): Kettle mode to set. Used by: set_mode.
                Valid: "wake_up", "home", "formula". Default: "home".
        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data
                - error (str | None): Error message if success is False
        Examples:
            # Check kettle status
            result = await ikettle_management(action="status")
            # Boil water to 95 degrees for coffee
            result = await ikettle_management(action="boil", temperature=95)
            # Set keep warm for tea at 80 degrees for 20 minutes
            result = await ikettle_management(action="keep_warm", temperature=80, duration=20)
            # Stop the kettle
            result = await ikettle_management(action="stop")
        """
        try:
            config = get_config()
            ikettle_cfg = config.get("ikettle", {})
            if not ikettle_cfg.get("enabled", False):
                return {
                    "success": False,
                    "message": "iKettle integration is disabled in configuration",
                    "error": "iKettle integration is disabled in configuration",
                }
            host = ikettle_cfg.get("host")
            if not host:
                return {
                    "success": False,
                    "message": "iKettle host address not configured",
                    "error": "iKettle host address not configured",
                }
            client = IKettleClient(host)
            if action == "status":
                data = await client.get_formatted_status()
                return {"success": True, "action": action, "data": data}
            if action == "boil":
                success = await client.boil(temperature)
                return {
                    "success": success,
                    "action": action,
                    "data": {"temperature_c": temperature} if success else {},
                }
            if action == "keep_warm":
                success = await client.keep_warm(temperature, duration)
                return {
                    "success": success,
                    "action": action,
                    "data": {"temperature_c": temperature, "duration_m": duration} if success else {},
                }
            if action == "stop":
                success = await client.stop()
                return {"success": success, "action": action, "data": {}}
            if action == "set_mode":
                success = await client.set_mode(mode)
                return {
                    "success": success,
                    "action": action,
                    "data": {"mode": mode} if success else {},
                }
            return {
                "success": False,
                "message": f"Action '{action}' not implemented",
                "error": f"Action '{action}' not implemented",
            }
        except Exception as e:
            logger.exception("Error in ikettle management action '{action}':")
            return {
                "success": False,
                "message": f"Failed to execute action '{action}': {e!s}",
            }
