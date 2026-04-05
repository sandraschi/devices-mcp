"""
Registration for Nest Protect tools.
"""

import logging

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_nest_protect_tools(mcp: FastMCP) -> None:
    """Register Nest Protect tools with the provided FastMCP instance."""
    try:
        from devices_mcp.nest_protect.tools import get_all_tools

        tools = get_all_tools()
        for name, func in tools.items():
            # Add prefix to avoid name collisions
            prefixed_name = f"nest_{name}"
            mcp.tool(name=prefixed_name)(func)

        logger.info(f"Successfully registered {len(tools)} Nest Protect tools")
    except ImportError as e:
        logger.warning(f"Nest Protect tools not available: {e}")
    except Exception:
        logger.exception("Failed to register Nest Protect tools:")
