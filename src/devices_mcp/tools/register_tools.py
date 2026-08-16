"""
FastMCP Tool Registration for devices-mcp

This module registers all devices-mcp tools with FastMCP.
"""

import logging
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_all_tools(
    mcp: FastMCP,
    tool_mode: str = "production",
    ring_client: Any = None,
    nest_protect_client: Any = None,
) -> None:
    """Register devices-mcp tools with the FastMCP server.

    Args:
        mcp: The FastMCP instance to register tools with
        tool_mode: Registration mode:
            - "production": Only portmanteau tools (cleaner UI)
            - "testing" or "all": Individual + portmanteau tools (for testing)
    """
    # Check if tools are already registered to this FastMCP instance
    if hasattr(mcp, "_devices_tools_registered") and mcp._devices_tools_registered:
        logger.debug("Tools already registered to this FastMCP instance, skipping")
        return

    # Always register portmanteau tools (consolidated tools)
    from devices_mcp.tools.portmanteau import register_all_portmanteau_tools

    register_all_portmanteau_tools(mcp)
    mcp._devices_tools_registered = True  # Mark as registered
    logger.info("Portmanteau tools registered successfully")

    # Register log query tools
    try:
        from devices_mcp.tools.log_tools import register_log_tools

        register_log_tools(mcp)
        logger.info("Log query tools registered")
    except Exception as e:
        logger.warning(f"Failed to register log query tools: {e}")


def _register_individual_tools(mcp: FastMCP) -> None:
    """Register individual tools for backward compatibility and testing.

    Args:
        mcp: The FastMCP instance to register tools with
    """
    # This would register individual tools if needed for testing
    # For now, we rely on portmanteau tools only
    logger.info("Individual tools registration skipped (using portmanteau tools only)")
