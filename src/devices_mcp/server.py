"""
Devices MCP Server - Legacy import for backward compatibility.

This module provides backward compatibility by importing from core.server.
Also exposes the REST ASGI app for uvicorn (web dashboard): uvicorn devices_mcp.server:app
"""

from .core.server import DevicesMCPServer
from .dual_server import dual_server

# For backward compatibility
TapoCameraMCP = DevicesMCPServer
TapoCameraServer = DevicesMCPServer

# ASGI app for uvicorn (web dashboard on 10717)
app = dual_server.rest_app
