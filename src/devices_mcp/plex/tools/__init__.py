"""
PlexMCP Tools Package

This package contains all MCP tools for Plex Media Server management.
Tools are organized into portmanteau tools (consolidated operations) and
individual tools (legacy, being deprecated).
"""

# Import portmanteau tools module to trigger registration
# This ensures all @mcp.tool() decorators execute when tools package is imported
from . import portmanteau

__all__ = ["portmanteau"]
