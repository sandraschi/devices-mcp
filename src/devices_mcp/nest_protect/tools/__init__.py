"""Nest Protect MCP Tools.

This module contains all the tools available in the Nest Protect MCP server.
"""

from typing import Any, Callable, Dict, List, Type

from fastmcp.tools import Tool

# Import all tool modules (they will be registered when imported)
from . import (
    auth_tools,
    config_tools,
    device_control,
    device_status,
    help_tool,
    system_status,
)


# Collect all tool functions from modules
def get_all_tools() -> Dict[str, Callable]:
    """Get all tools from all modules."""
    tools = {}

    # Device status tools
    tools.update(
        {
            "list_devices": device_status.list_devices,
            "get_device_status": device_status.get_device_status,
            "get_device_events": device_status.get_device_events,
        }
    )

    # Device control tools
    tools.update(
        {
            "hush_alarm": device_control.hush_alarm,
            "run_safety_check": device_control.run_safety_check,
            "set_led_brightness": device_control.set_led_brightness,
        }
    )

    # System status tools
    tools.update(
        {
            "get_system_status": system_status.get_system_status,
            "get_process_status": system_status.get_process_status,
            "get_api_status": system_status.get_api_status,
        }
    )

    # Help tools
    tools.update(
        {
            "list_available_tools": help_tool.list_available_tools,
            "get_tool_help": help_tool.get_tool_help,
            "search_tools": help_tool.search_tools,
        }
    )

    # Auth tools
    tools.update(
        {
            "initiate_oauth_flow": auth_tools.initiate_oauth_flow,
            "handle_oauth_callback": auth_tools.handle_oauth_callback,
            "refresh_access_token": auth_tools.refresh_access_token,
        }
    )

    # Config tools
    tools.update(
        {
            "get_config": config_tools.get_config,
            "update_config": config_tools.update_config,
            "reset_config": config_tools.reset_config,
            "export_config": config_tools.export_config,
            "import_config": config_tools.import_config,
        }
    )

    return tools


# Re-export commonly used types
__all__ = [
    "Tool",
    "get_all_tools",
]
