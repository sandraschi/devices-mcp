"""
Mock MCP Server for Testing

This module provides a mock MCP server that can be used for testing MCP client
functionality. It simulates the stdio-based MCP protocol used by the Devices MCP.

Features:
- Simulates MCP protocol over stdio
- Configurable tool responses
- Error simulation capabilities
- Performance testing support
- Comprehensive logging and debugging
"""

import asyncio
import json
import logging
import sys
import time
from typing import Any

logger = logging.getLogger(__name__)


class MockMCPServer:
    """
    Mock MCP server for testing purposes.

    Simulates the stdio-based MCP protocol with configurable responses.
    """

    def __init__(self, response_config: dict[str, Any] | None = None):
        """
        Initialize the mock MCP server.

        Args:
            response_config: Configuration for tool responses
        """
        self.response_config = response_config or self._get_default_config()
        self.requests_received = []
        self.responses_sent = []
        self.running = False
        self.request_count = 0

    def _get_default_config(self) -> dict[str, Any]:
        """Get default response configuration."""
        return {
            "tools": {
                "energy_management": {
                    "status": {"success": True, "action": "status", "data": {"devices": []}},
                    "consumption": {
                        "success": True,
                        "action": "consumption",
                        "data": {"devices": []},
                    },
                    "cost": {
                        "success": True,
                        "action": "cost",
                        "data": {"total_devices": 0, "current_power": 0, "daily_cost": 0},
                    },
                    "control": {
                        "success": True,
                        "action": "control",
                        "data": {"device_id": "test", "power_state": "on"},
                    },
                },
                "motion_management": {
                    "status": {
                        "success": True,
                        "action": "status",
                        "data": {
                            "subscriptions": [],
                            "total_subscriptions": 0,
                            "active_subscriptions": 0,
                        },
                    },
                    "events": {
                        "success": True,
                        "action": "events",
                        "data": {"events": [], "count": 0},
                    },
                    "capabilities": {
                        "success": True,
                        "action": "capabilities",
                        "data": {"onvif_cameras": {"motion_detection": "Limited"}},
                    },
                    "subscribe": {
                        "success": True,
                        "action": "subscribe",
                        "data": {"camera_id": "test", "subscribed": True},
                    },
                    "unsubscribe": {
                        "success": True,
                        "action": "unsubscribe",
                        "data": {"camera_id": "test", "unsubscribed": True},
                    },
                    "test": {
                        "success": True,
                        "action": "test",
                        "data": {"camera_id": "test", "onvif_events_support": True},
                    },
                },
                "camera_management": {
                    "list": {"success": True, "action": "list", "data": {"cameras": []}},
                    "info": {
                        "success": True,
                        "action": "info",
                        "data": {"camera_id": "test", "name": "Test Camera"},
                    },
                    "get_stream_url": {
                        "success": True,
                        "action": "get_stream_url",
                        "data": {"stream_url": "rtsp://test:554/stream"},
                    },
                    "capture": {
                        "success": True,
                        "action": "capture",
                        "data": {"image_path": "/tmp/test.jpg"},
                    },
                },
                "media_management": {
                    "get_stream_url": {
                        "success": True,
                        "action": "get_stream_url",
                        "data": {"stream_url": "rtsp://test:554/stream"},
                    },
                    "capture": {
                        "success": True,
                        "action": "capture",
                        "data": {"media_path": "/tmp/test.mp4"},
                    },
                    "start_recording": {
                        "success": True,
                        "action": "start_recording",
                        "data": {"recording_id": "rec_123"},
                    },
                    "stop_recording": {
                        "success": True,
                        "action": "stop_recording",
                        "data": {"recording_id": "rec_123", "duration": 60},
                    },
                },
                "system_management": {
                    "info": {
                        "success": True,
                        "action": "info",
                        "data": {"version": "1.0.0", "uptime": 3600},
                    },
                    "status": {
                        "success": True,
                        "action": "status",
                        "data": {"healthy": True, "services": []},
                    },
                    "logs": {
                        "success": True,
                        "action": "logs",
                        "data": {"entries": [], "count": 0},
                    },
                    "health": {
                        "success": True,
                        "action": "health",
                        "data": {"status": "healthy", "checks": {}},
                    },
                },
                "ptz_management": {
                    "move": {
                        "success": True,
                        "action": "move",
                        "data": {"pan": 0.5, "tilt": 0.0, "zoom": 0.0},
                    },
                    "stop": {"success": True, "action": "stop", "data": {"stopped": True}},
                    "home": {"success": True, "action": "home", "data": {"moved_to_home": True}},
                    "list_presets": {
                        "success": True,
                        "action": "list_presets",
                        "data": {"presets": []},
                    },
                    "recall_preset": {
                        "success": True,
                        "action": "recall_preset",
                        "data": {"preset_name": "test", "recalled": True},
                    },
                },
                "security_management": {
                    "status": {
                        "success": True,
                        "action": "status",
                        "data": {"connected": True, "devices": []},
                    },
                    "nest_status": {
                        "success": True,
                        "action": "nest_status",
                        "data": {"devices": [], "alerts": []},
                    },
                    "nest_alerts": {
                        "success": True,
                        "action": "nest_alerts",
                        "data": {"alerts": [], "total_alerts": 0},
                    },
                },
                "medical_management": {
                    "get_device_status": {
                        "success": True,
                        "action": "get_device_status",
                        "data": {"device_id": "scanner_1", "status": "ready"},
                    },
                    "scan_document": {
                        "success": True,
                        "action": "scan_document",
                        "data": {"scan_id": "scan_123", "path": "/tmp/scan.jpg"},
                    },
                },
            },
            "resources": {
                "cameras": {"uri": "resource://cameras", "content": {"cameras": []}},
                "devices": {"uri": "resource://devices", "content": {"devices": []}},
                "system": {"uri": "resource://system", "content": {"status": "ok"}},
            },
            "delays": {},  # Tool -> delay in seconds for testing timeouts
            "errors": {},  # Tool -> error response for testing error handling
        }

    def configure_response(self, tool: str, action: str, response: dict[str, Any]):
        """Configure a specific tool/action response."""
        if tool not in self.response_config["tools"]:
            self.response_config["tools"][tool] = {}
        self.response_config["tools"][tool][action] = response

    def configure_delay(self, tool: str, action: str, delay: float):
        """Configure a delay for a specific tool/action."""
        key = f"{tool}.{action}"
        self.response_config["delays"][key] = delay

    def configure_error(self, tool: str, action: str, error: dict[str, Any]):
        """Configure an error response for a specific tool/action."""
        key = f"{tool}.{action}"
        self.response_config["errors"][key] = error

    def get_response(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Get the appropriate response for a request."""
        self.request_count += 1
        request_info = {
            "id": self.request_count,
            "method": method,
            "params": params,
            "timestamp": time.time(),
        }
        self.requests_received.append(request_info)

        # Handle different MCP methods
        if method == "initialize":
            response = {
                "jsonrpc": "2.0",
                "id": self.request_count,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"listChanged": True},
                    },
                    "serverInfo": {"name": "mock-devices-mcp", "version": "1.0.0"},
                },
            }
        elif method == "tools/list":
            # Return list of available tools
            tools = []
            for tool_name, actions in self.response_config["tools"].items():
                for action_name in actions.keys():
                    tools.append(
                        {
                            "name": f"{tool_name}.{action_name}",
                            "description": f"Mock {tool_name} {action_name} tool",
                            "inputSchema": {"type": "object", "properties": {}, "required": []},
                        }
                    )

            response = {"jsonrpc": "2.0", "id": self.request_count, "result": {"tools": tools}}
        elif method == "tools/call":
            tool_call = params
            tool_name = tool_call.get("name", "")
            tool_call.get("arguments", {})

            # Parse tool and action from name (format: "tool.action")
            if "." in tool_name:
                tool, action = tool_name.split(".", 1)
            else:
                tool = tool_name
                action = "default"

            # Check for configured error
            error_key = f"{tool}.{action}"
            if error_key in self.response_config["errors"]:
                response = {
                    "jsonrpc": "2.0",
                    "id": self.request_count,
                    "error": self.response_config["errors"][error_key],
                }
            else:
                # Get configured response
                tool_config = self.response_config["tools"].get(tool, {})
                tool_response = tool_config.get(
                    action, {"success": False, "error": f"Unknown tool/action: {tool}.{action}"}
                )

                response = {"jsonrpc": "2.0", "id": self.request_count, "result": tool_response}

            # Apply delay if configured
            if error_key in self.response_config["delays"]:
                delay = self.response_config["delays"][error_key]
                time.sleep(delay)

        elif method == "resources/list":
            resources = list(self.response_config["resources"].values())
            response = {
                "jsonrpc": "2.0",
                "id": self.request_count,
                "result": {"resources": resources},
            }
        elif method == "resources/read":
            uri = params.get("uri", "")
            resource = self.response_config["resources"].get(uri, {"error": f"Resource not found: {uri}"})
            response = {"jsonrpc": "2.0", "id": self.request_count, "result": resource}
        else:
            response = {
                "jsonrpc": "2.0",
                "id": self.request_count,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }

        self.responses_sent.append({"request": request_info, "response": response, "timestamp": time.time()})

        return response

    async def run_stdio_server(self):
        """Run the mock server using stdio (for testing MCP clients)."""
        self.running = True
        logger.info("Mock MCP server started (stdio mode)")

        try:
            while self.running:
                # Read from stdin
                line = sys.stdin.readline().strip()
                if not line:
                    break

                try:
                    request = json.loads(line)
                    response = self.get_response(request["method"], request.get("params", {}))

                    # Write to stdout
                    logger.info(json.dumps(response), flush=True)

                except json.JSONDecodeError as e:
                    # Send error response for invalid JSON
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": f"Parse error: {e}"},
                    }
                    logger.info(json.dumps(error_response), flush=True)

                except Exception as e:
                    # Send error response for other exceptions
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32603, "message": f"Internal error: {e}"},
                    }
                    logger.info(json.dumps(error_response), flush=True)

        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            logger.info("Mock MCP server stopped")

    def get_statistics(self) -> dict[str, Any]:
        """Get server statistics."""
        return {
            "requests_received": len(self.requests_received),
            "responses_sent": len(self.responses_sent),
            "uptime": time.time() - (self.requests_received[0]["timestamp"] if self.requests_received else time.time()),
            "running": self.running,
        }


class MockMCPClient:
    """
    Mock MCP client for testing server-side functionality.

    This simulates what a real MCP client would send to test server behavior.
    """

    def __init__(self, server: MockMCPServer):
        self.server = server
        self.responses_received = []

    async def call_tool(self, tool: str, action: str, **arguments) -> dict[str, Any]:
        """Call a tool on the mock server."""
        method = "tools/call"
        params = {"name": f"{tool}.{action}", "arguments": arguments}

        response = self.server.get_response(method, params)
        self.responses_received.append(response)

        if "error" in response:
            raise Exception(f"MCP Error: {response['error']}")

        return response.get("result", {})

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools."""
        response = self.server.get_response("tools/list", {})
        self.responses_received.append(response)

        if "error" in response:
            raise Exception(f"MCP Error: {response['error']}")

        return response.get("result", {}).get("tools", [])

    async def list_resources(self) -> list[dict[str, Any]]:
        """List available resources."""
        response = self.server.get_response("resources/list", {})
        self.responses_received.append(response)

        if "error" in response:
            raise Exception(f"MCP Error: {response['error']}")

        return response.get("result", {}).get("resources", [])

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource."""
        response = self.server.get_response("resources/read", {"uri": uri})
        self.responses_received.append(response)

        if "error" in response:
            raise Exception(f"MCP Error: {response['error']}")

        return response.get("result", {})


# Convenience functions for testing


def create_mock_server_with_data(**tool_responses) -> MockMCPServer:
    """Create a mock server with custom tool responses."""
    server = MockMCPServer()

    for tool_action, response in tool_responses.items():
        if "." in tool_action:
            tool, action = tool_action.split(".", 1)
            server.configure_response(tool, action, response)

    return server


def create_failing_mock_server() -> MockMCPServer:
    """Create a mock server that returns errors for all requests."""
    server = MockMCPServer()

    # Configure all tools to fail
    for tool_name, actions in server.response_config["tools"].items():
        for action_name in actions:
            server.configure_error(
                tool_name,
                action_name,
                {"code": -32000, "message": f"Mock server error for {tool_name}.{action_name}"},
            )

    return server


def create_slow_mock_server(delay: float = 2.0) -> MockMCPServer:
    """Create a mock server with configurable delays."""
    server = MockMCPServer()

    # Add delays to all operations
    for tool_name, actions in server.response_config["tools"].items():
        for action_name in actions:
            server.configure_delay(tool_name, action_name, delay)

    return server


# Test utilities


async def run_mcp_test_scenario(
    server: MockMCPServer, client: MockMCPClient, scenario: list[dict[str, Any]]
) -> dict[str, Any]:
    """
    Run a test scenario with the mock server and client.

    Args:
        server: Mock MCP server
        client: Mock MCP client
        scenario: List of test steps

    Returns:
        Test results
    """
    results = {"steps_executed": 0, "errors": [], "responses": [], "server_stats": {}}

    for step in scenario:
        step_type = step.get("type", "tool_call")

        try:
            if step_type == "tool_call":
                response = await client.call_tool(step["tool"], step["action"], **step.get("arguments", {}))
                results["responses"].append(response)
            elif step_type == "list_tools":
                response = await client.list_tools()
                results["responses"].append(response)
            elif step_type == "list_resources":
                response = await client.list_resources()
                results["responses"].append(response)
            elif step_type == "read_resource":
                response = await client.read_resource(step["uri"])
                results["responses"].append(response)

            results["steps_executed"] += 1

        except Exception as e:
            results["errors"].append({"step": step, "error": str(e)})

    results["server_stats"] = server.get_statistics()
    return results


if __name__ == "__main__":
    # Run as a standalone MCP server for testing
    logging.basicConfig(level=logging.INFO)
    server = MockMCPServer()
    asyncio.run(server.run_stdio_server())
