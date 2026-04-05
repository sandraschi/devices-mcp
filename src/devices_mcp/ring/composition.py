"""
Server Composition and Proxy for Ring MCP - FastMCP 3.1

This module provides functionality to compose multiple MCP servers together
and proxy requests between them, enabling a unified API for multiple services.

This module uses FastMCP 3.1 patterns with multiline decorators and proper
tool registration for Claude Desktop stdio communication.
"""

import logging
from typing import Any, Dict, List, Optional

from fastmcp import Client, FastMCP

logger = logging.getLogger(__name__)


class MCPServerComposition:
    """Compose multiple MCP servers together with proxy capabilities."""

    def __init__(self, base_server: FastMCP):
        """Initialize the server composition.

        Args:
            base_server: The base FastMCP server to extend with composition features.
        """
        self.base_server = base_server
        self.connected_servers: Dict[str, Client] = {}
        self.namespace_mapping: Dict[str, str] = {}

        # Register composition tools with the base server
        self._register_tools(base_server)

    def _register_tools(self, app: FastMCP) -> None:
        """Register composition and proxy tools with the base server.

        Uses FastMCP 3.1 patterns with multiline decorators and proper
        stdio communication support for Claude Desktop integration.

        Args:
            app: FastMCP application instance
        """

        @app.tool()
        async def list_connected_servers() -> List[Dict[str, Any]]:
            """List all connected MCP servers and their namespaces."""
            return [
                {
                    "namespace": namespace,
                    "server_url": client.base_url,
                    "connected": client.connected,
                }
                for namespace, client in self.connected_servers.items()
            ]

        @app.tool()
        async def connect_server(
            namespace: str, server_url: str, api_key: Optional[str] = None
        ) -> Dict[str, Any]:
            """Connect to another MCP server.

            Args:
                namespace: Namespace to use for this server's tools
                server_url: Base URL of the MCP server to connect to
                api_key: Optional API key for authentication

            Returns:
                Connection status and server information
            """
            if namespace in self.connected_servers:
                raise ValueError(f"Namespace '{namespace}' is already in use")

            try:
                client = Client(base_url=server_url, api_key=api_key)
                await client.connect()

                # Get server info to verify connection
                server_info = await client.server_info()

                # Store the client and namespace mapping
                self.connected_servers[namespace] = client

                # Register all tools from the connected server with the namespace
                for tool_name in await client.list_tools():
                    tool_info = await client.get_tool(tool_name)
                    prefixed_name = f"{namespace}.{tool_name}"
                    self.namespace_mapping[prefixed_name] = (namespace, tool_name)

                return {
                    "status": "connected",
                    "namespace": namespace,
                    "server_info": server_info,
                    "tools_registered": list(self.namespace_mapping.keys()),
                }

            except Exception as e:
                logger.exception("Failed to connect to server %s: %s", server_url, str(e))
                raise RuntimeError(f"Failed to connect to server: {e!s}")

        @self.base_server.tool()
        async def disconnect_server(namespace: str) -> Dict[str, Any]:
            """Disconnect from a connected MCP server.

            Args:
                namespace: Namespace of the server to disconnect

            Returns:
                Disconnection status
            """
            if namespace not in self.connected_servers:
                raise ValueError(f"No server connected with namespace '{namespace}'")

            try:
                client = self.connected_servers[namespace]
                await client.close()

                # Remove all tools from this namespace
                tools_to_remove = [
                    name for name in self.namespace_mapping if name.startswith(f"{namespace}.")
                ]
                for tool_name in tools_to_remove:
                    self.namespace_mapping.pop(tool_name, None)

                # Note: The call_namespaced_tool remains available for other namespaces

                # Remove the client
                self.connected_servers.pop(namespace, None)

                return {
                    "status": "disconnected",
                    "namespace": namespace,
                    "tools_removed": tools_to_remove,
                }

            except Exception as e:
                logger.exception("Failed to disconnect server %s: %s", namespace, str(e))
                raise RuntimeError(f"Failed to disconnect server: {e!s}")

        @app.tool()
        async def call_namespaced_tool(tool_name: str, **kwargs) -> Any:
            """Call a tool from a connected MCP server using namespace prefix.

            This tool allows calling tools from connected MCP servers using their
            namespaced names (e.g., 'namespace.tool_name'). The tool will automatically
            route the call to the appropriate connected server.

            Args:
                tool_name: Full name of the tool including namespace (e.g., 'ring.get_devices')
                **kwargs: Arguments to pass to the tool

            Returns:
                The result from the proxied tool call

            Raises:
                ValueError: If the tool is not found or the call fails
            """
            if tool_name not in self.namespace_mapping:
                raise ValueError(f"No such tool: {tool_name}")

            namespace, actual_tool_name = self.namespace_mapping[tool_name]
            client = self.connected_servers.get(namespace)

            if not client or not client.connected:
                raise RuntimeError(f"Server '{namespace}' is not connected")

            try:
                return await client.call(actual_tool_name, **kwargs)
            except Exception as e:
                logger.exception(
                    "Error calling tool %s on server %s: %s", actual_tool_name, namespace, str(e)
                )
                raise RuntimeError(f"Failed to call tool {tool_name}: {e!s}")

    async def close(self) -> None:
        """Close all connections to remote servers."""
        for namespace, client in list(self.connected_servers.items()):
            try:
                await client.close()
                logger.info("Disconnected from server: %s", namespace)
            except Exception as e:
                logger.exception("Error disconnecting from server %s: %s", namespace, str(e))

        self.connected_servers.clear()
        self.namespace_mapping.clear()


def create_composed_app(ring_client=None) -> FastMCP:
    """Create a composed FastMCP application with Ring MCP and composition support.

    Uses FastMCP 3.1 patterns with multiline decorators and proper
    stdio communication support for Claude Desktop integration.

    Args:
        ring_client: Optional initialized Ring client instance

    Returns:
        Configured FastMCP application with composition support
    """
    # Create the base FastMCP application (3.1 compatible)
    app = FastMCP(name="Ring MCP with Composition", version="3.1.0")

    # Add the Ring MCP tools
    from .server import register_ring_tools

    if ring_client:
        register_ring_tools(app, ring_client)
    else:
        # Initialize a default Ring client if none provided
        from ring_mcp.core.ring_client_modern import RingClient

        default_client = RingClient()
        register_ring_tools(app, default_client)

    # Add composition capabilities
    composition = MCPServerComposition(app)

    # Register a cleanup handler to close all connections on shutdown
    @app.on_event("shutdown")
    async def shutdown_event():
        await composition.close()

    return app
