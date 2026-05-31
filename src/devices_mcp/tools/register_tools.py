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

    # Register Plex MCP tools
    try:
        # Use the local function defined in this file
        _register_plex_tools_with_mcp(mcp, tool_mode=tool_mode)
    except Exception as e:
        logger.warning(f"Failed to register Plex MCP tools: {e}")

    # Register Ring tools
    try:
        from devices_mcp.ring.server import register_ring_tools

        register_ring_tools(mcp, ring_client)
        logger.info("Ring tools registered")
    except Exception as e:
        logger.warning(f"Failed to register Ring tools: {e}")

    # Register Nest Protect tools
    try:
        from devices_mcp.nest_protect.tools.register import register_nest_protect_tools

        register_nest_protect_tools(mcp, nest_protect_client)
        logger.info("Nest Protect tools registered")
    except Exception as e:
        logger.warning(f"Failed to register Nest Protect tools: {e}")


def _register_plex_tools_with_mcp(mcp: FastMCP, tool_mode: str = "production") -> None:
    """Register Plex MCP tools with the provided FastMCP instance."""

    @mcp.tool()
    async def plex_library_browse(
        operation: str = "list", library_key: str | None = None, include_details: bool = False
    ) -> dict:
        """Browse Plex media libraries."""
        try:
            # Import the actual Plex library function
            from devices_mcp.plex.tools.portmanteau.library import _plex_library_operation

            # Call the underlying function
            result = await _plex_library_operation(
                operation=operation, library_key=library_key, include_details=include_details
            )
            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"Plex library operation failed: {e}",
                "message": "Unable to access Plex library. Please check your Plex server configuration.",
            }

    @mcp.tool()
    async def plex_media_search(query: str, media_type: str = "all", limit: int = 20) -> dict:
        """Search for media in Plex library."""
        try:
            # Import the actual Plex search function
            from devices_mcp.plex.tools.portmanteau.search import _plex_search_operation

            result = await _plex_search_operation(operation="search", query=query, media_type=media_type, limit=limit)
            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"Plex search failed: {e}",
                "message": "Unable to search Plex library. Please check your Plex server configuration.",
            }

    logger.info("Plex MCP tools registered with Devices MCP FastMCP instance")

    # Register individual tools only in testing/all mode
    if tool_mode.lower() in ["testing", "all"]:
        logger.info(f"Tool mode: {tool_mode} - Registering individual tools for testing")
        _register_individual_tools(mcp)
    else:
        logger.info(f"Tool mode: {tool_mode} - Using portmanteau tools only (production mode)")


def _register_individual_tools(mcp: FastMCP) -> None:
    """Register individual tools for backward compatibility and testing.

    Args:
        mcp: The FastMCP instance to register tools with
    """
    # This would register individual tools if needed for testing
    # For now, we rely on portmanteau tools only
    logger.info("Individual tools registration skipped (using portmanteau tools only)")
