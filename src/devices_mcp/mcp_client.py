"""
MCP Client for Webapp Integration

This module provides a client that can communicate with MCP servers via stdio,
allowing the webapp to use MCP tools instead of duplicating functionality.

The webapp becomes a full MCP client that can:
1. Connect to local MCP servers
2. Connect to remote MCP servers over HTTP (future)
3. Connect to multiple MCP servers simultaneously
4. Use MCP tools through a unified interface
"""

import asyncio
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MCPClient:
    """Client for communicating with MCP servers via stdio."""

    def __init__(self, server_command: list[str], cwd: str | None = None):
        """
        Initialize MCP client.

        Args:
            server_command: Command to start the MCP server (e.g., ["python", "-m", "devices_mcp.cli_v2", "serve"])
            cwd: Working directory for the server process
        """
        self.server_command = server_command
        self.cwd = cwd or str(Path.cwd())
        self.process: subprocess.Popen | None = None
        self._initialized = False
        self._request_id = 0

    async def start_server(self) -> None:
        """Start the MCP server process."""
        if self.process:
            logger.warning("Server already running")
            return

        logger.info(f"Starting MCP server: {' '.join(self.server_command)}")
        try:
            self.process = subprocess.Popen(
                self.server_command,
                cwd=self.cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            self._initialized = True
            logger.info("MCP server started successfully")
        except Exception:
            logger.exception("Failed to start MCP server:")
            raise

    async def stop_server(self) -> None:
        """Stop the MCP server process."""
        if self.process:
            logger.info("Stopping MCP server")
            try:
                self.process.terminate()
                await asyncio.sleep(0.1)  # Give it a moment to terminate gracefully
                if self.process.poll() is None:
                    self.process.kill()
                self.process = None
                self._initialized = False
                logger.info("MCP server stopped")
            except Exception:
                logger.exception("Error stopping MCP server:")

    def _get_next_request_id(self) -> int:
        """Get the next request ID."""
        self._request_id += 1
        return self._request_id

    async def _send_request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        if not self.process or not self._initialized:
            raise RuntimeError("MCP server not started")

        request_id = self._get_next_request_id()
        request = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}

        request_json = json.dumps(request) + "\n"
        logger.debug(f"Sending request: {request_json.strip()}")

        if self.process.stdin:
            self.process.stdin.write(request_json)
            self.process.stdin.flush()

        # Read response
        if self.process.stdout:
            response_line = self.process.stdout.readline().strip()
            if response_line:
                try:
                    response = json.loads(response_line)
                    logger.debug(f"Received response: {response}")
                    return response
                except json.JSONDecodeError as e:
                    logger.exception("Failed to parse response:")
                    raise e from e

        raise RuntimeError("No response received from MCP server")

    async def initialize(self) -> dict[str, Any]:
        """Initialize the MCP connection."""
        return await self._send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "tapo-camera-webapp", "version": "1.0.0"},
            },
        )

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools from the MCP server."""
        response = await self._send_request("tools/list", {})
        return response.get("result", {}).get("tools", [])

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server."""
        response = await self._send_request("tools/call", {"name": tool_name, "arguments": arguments})
        return response.get("result", {})

    async def list_resources(self) -> list[dict[str, Any]]:
        """List available resources from the MCP server."""
        response = await self._send_request("resources/list", {})
        return response.get("result", {}).get("resources", [])

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource from the MCP server."""
        response = await self._send_request("resources/read", {"uri": uri})
        return response.get("result", {})


class MCPClientManager:
    """Manager for multiple MCP client connections."""

    def __init__(self):
        self.clients: dict[str, MCPClient] = {}
        self._default_client: str | None = None

    def add_client(self, name: str, client: MCPClient, set_default: bool = False) -> None:
        """Add an MCP client."""
        self.clients[name] = client
        if set_default or not self._default_client:
            self._default_client = name
        logger.info(f"Added MCP client '{name}'")

    def get_client(self, name: str | None = None) -> MCPClient:
        """Get an MCP client by name."""
        client_name = name or self._default_client
        if not client_name or client_name not in self.clients:
            raise ValueError(f"MCP client '{client_name}' not found")
        return self.clients[client_name]

    async def start_all_clients(self) -> None:
        """Start all MCP clients."""
        for name, client in self.clients.items():
            try:
                await client.start_server()
                await client.initialize()
                logger.info(f"Started MCP client '{name}'")
            except Exception:
                logger.exception("Failed to start MCP client '{name}':")

    async def stop_all_clients(self) -> None:
        """Stop all MCP clients."""
        for name, client in self.clients.items():
            try:
                await client.stop_server()
                logger.info(f"Stopped MCP client '{name}'")
            except Exception:
                logger.exception("Error stopping MCP client '{name}':")

    async def call_tool(
        self, tool_name: str, arguments: dict[str, Any], client_name: str | None = None
    ) -> dict[str, Any]:
        """Call a tool on the specified MCP client."""
        client = self.get_client(client_name)
        return await client.call_tool(tool_name, arguments)


# Global client manager instance
mcp_clients = MCPClientManager()


async def get_mcp_client(name: str | None = None) -> MCPClient:
    """Get an MCP client instance."""
    return mcp_clients.get_client(name)


async def call_mcp_tool(tool_name: str, arguments: dict[str, Any], client_name: str | None = None) -> dict[str, Any]:
    """Call an MCP tool through the client manager."""
    return await mcp_clients.call_tool(tool_name, arguments, client_name)


def create_local_tapo_client() -> MCPClient:
    """Create an MCP client for the local Devices MCP server."""
    # Use the CLI command to start the server
    server_command = [sys.executable, "-m", "devices_mcp.cli_v2", "serve"]
    return MCPClient(server_command)


def create_local_plex_client() -> MCPClient:
    """Create an MCP client for the local Plex MCP server."""
    # Use the Plex MCP main module to start the server
    server_command = [sys.executable, "-m", "devices_mcp.plex.main"]
    return MCPClient(server_command)


def setup_default_clients() -> None:
    """Set up default MCP clients."""
    # Add the local Tapo client as default
    tapo_client = create_local_tapo_client()
    mcp_clients.add_client("tapo", tapo_client, set_default=True)

    # Add the local Plex client
    try:
        plex_client = create_local_plex_client()
        mcp_clients.add_client("plex", plex_client)
        logger.info("Plex MCP client added to default clients")
    except Exception as e:
        logger.warning(f"Failed to add Plex MCP client: {e}")
        logger.info("Continuing without Plex MCP client")


# Convenience functions for common operations
async def list_tapo_lights() -> dict[str, Any]:
    """List all lights via MCP."""
    return await call_mcp_tool("tapo", {"action": "list_lights"})


async def list_tapo_plugs() -> dict[str, Any]:
    """List all smart plugs via MCP."""
    return await call_mcp_tool("tapo", {"action": "list_plugs"})


async def get_tapo_status() -> dict[str, Any]:
    """Get system status via MCP."""
    return await call_mcp_tool("tapo", {"action": "status"})


# Plex convenience functions
async def plex_library_browse(operation: str = "list", **kwargs) -> dict[str, Any]:
    """Browse Plex media libraries via MCP."""
    return await call_mcp_tool("plex_library_browse", {"operation": operation, **kwargs})


async def plex_media_search(query: str, **kwargs) -> dict[str, Any]:
    """Search Plex media via MCP."""
    return await call_mcp_tool("plex_media_search", {"query": query, **kwargs})


async def get_plex_status() -> dict[str, Any]:
    """Get Plex system status via MCP."""
    try:
        return await call_mcp_tool("plex_server", {"operation": "status"})
    except Exception:
        # Fallback to API call if MCP fails
        return {"status": "unknown", "error": "MCP server not available"}
