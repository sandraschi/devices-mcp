"""
System Management Portmanteau Tool

Consolidates all system-related operations into a single tool with action-based interface.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

from devices_mcp.tools.system.health_tool import HealthCheckTool
from devices_mcp.tools.system.system_control_tool import SystemControlTool
from devices_mcp.tools.system.system_info_tool import SystemInfoTool

logger = logging.getLogger(__name__)

SYSTEM_ACTIONS = {
    "info": "Get system information",
    "status": "Get system status",
    "health": "Perform health check",
    "initialize": "Initialize all cameras and hardware",
    "reboot": "Reboot camera",
    "logs": "Get system logs",
}


def register_system_management_tool(mcp: FastMCP) -> None:
    """Register the system management portmanteau tool."""

    @mcp.tool()
    async def system_management(
        action: Literal["info", "status", "health", "initialize", "reboot", "logs"],
        camera_name: str | None = None,
        reboot_type: str = "soft",
        log_level: str = "INFO",
        lines: int = 100,
    ) -> dict[str, Any]:
        """
        Comprehensive system management portmanteau tool.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 5+ separate tools (one per operation), this tool consolidates related
        system operations into a single interface. Prevents tool explosion (5+ tools → 1 tool) while maintaining
        full functionality and improving discoverability. Follows FastMCP 3.1+ best practices.

        Args:
            action (Literal, required): The operation to perform. Must be one of: "info", "status", "health",
                "initialize", "reboot", "logs".
                - "info": Get system information (no other parameters required)
                - "status": Get system status (no other parameters required)
                - "health": Perform health check (no other parameters required)
                - "initialize": Initialize all cameras and hardware (no other parameters required)
                - "reboot": Reboot camera (requires: camera_name, reboot_type)
                - "logs": Get system logs (optional: log_level, lines)

            camera_name (str | None): Camera name for reboot operation. Required for: reboot operation.

            reboot_type (str): Type of reboot. Required for: reboot operation. Default: "soft".
                Valid: "soft", "hard", "factory_reset"

            log_level (str): Log level filter. Used by: logs operation. Default: "INFO".
                Valid: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"

            lines (int): Number of log lines to retrieve. Used by: logs operation. Default: 100

        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data (info, status, health, logs, etc.)
                - error (str | None): Error message if success is False

        Examples:
            # Get system info
            result = await system_management(action="info")

            # Get system status
            result = await system_management(action="status")

            # Health check
            result = await system_management(action="health")

            # Initialize all cameras
            result = await system_management(action="initialize")

            # Reboot camera
            result = await system_management(action="reboot", camera_name="Front Door", reboot_type="soft")

            # Get logs
            result = await system_management(action="logs", log_level="ERROR", lines=50)
        """
        try:
            if action not in SYSTEM_ACTIONS:
                return {
                    "success": False,
                    "error": f"Invalid action '{action}'. Available: {list(SYSTEM_ACTIONS.keys())}",
                }

            logger.info(f"Executing system management action: {action}")

            if action == "info":
                tool = SystemInfoTool()
                result = await tool.execute(operation="info")
                return {"success": True, "action": action, "data": result}

            if action == "logs":
                tool = SystemInfoTool()
                result = await tool.execute(
                    operation="logs",
                    log_level=log_level.lower(),
                    log_lines=lines,
                )
                return {"success": True, "action": action, "data": result}

            if action in ["status", "reboot"]:
                tool = SystemControlTool()
                operation_map = {
                    "status": "status",
                    "reboot": "reboot_camera",
                }
                result = await tool.execute(
                    operation=operation_map[action],
                    camera_id=camera_name,
                    reboot_type=reboot_type,
                )
                return {"success": True, "action": action, "data": result}

            if action == "health":
                tool = HealthCheckTool()
                result = await tool.execute()
                return {"success": True, "action": action, "data": result}

            if action == "initialize":
                from devices_mcp.core.hardware_init import initialize_all_hardware
                from devices_mcp.core.server import TapoCameraServer

                server = await TapoCameraServer.get_instance()
                result = await initialize_all_hardware(server.camera_manager)
                return {"success": True, "action": action, "data": result}

            return {"success": False, "error": f"Action '{action}' not implemented"}

        except Exception as e:
            logger.exception("Error in system management action '{action}':")
            return {"success": False, "error": f"Failed to execute action '{action}': {e!s}"}
