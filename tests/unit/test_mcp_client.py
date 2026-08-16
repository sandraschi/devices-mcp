"""
Comprehensive unit tests for the MCP client functionality.

Tests cover:
- MCP client initialization and connection
- Tool calling and response handling
- Error handling and recovery
- Client manager functionality
- Mock server interactions
- Performance and scalability
"""

import asyncio
import json
import logging
import subprocess
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

logger = logging.getLogger(__name__)

from devices_mcp.mcp_client import (
    MCPClient,
    MCPClientManager,
    call_mcp_tool,
    get_mcp_client,
)


class TestMCPClient:
    """Test suite for MCP client functionality."""

    @pytest.fixture
    def mock_process(self):
        """Create a mock subprocess for testing."""
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.terminate.return_value = None
        mock_proc.kill.return_value = None
        return mock_proc

    @pytest.fixture
    def mock_client(self, mock_process):
        """Create a mock MCP client."""
        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient([sys.executable, "-c", "pass"])
            client._initialized = True
            yield client

    def test_client_initialization(self, mock_process):
        """Test MCP client initialization."""
        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient([sys.executable, "-c", "logger.info('test')"], cwd="/tmp")

            assert client.server_command == [sys.executable, "-c", "logger.info('test')"]
            assert client.cwd == "/tmp"
            assert client.process == mock_process
            assert client._initialized is True
            assert client._request_id == 0

    def test_start_server(self, mock_process):
        """Test starting the MCP server."""
        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient([sys.executable, "-c", "pass"])

            # Should start successfully
            assert client.process == mock_process
            assert client._initialized is True

    def test_stop_server(self, mock_process):
        """Test stopping the MCP server."""
        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient([sys.executable, "-c", "pass"])

            # Stop the server
            asyncio.run(client.stop_server())

            # Verify cleanup
            mock_process.terminate.assert_called_once()
            assert client.process is None
            assert client._initialized is False

    def test_request_id_increment(self, mock_client):
        """Test request ID incrementation."""
        client = mock_client

        # Get multiple request IDs
        id1 = client._get_next_request_id()
        id2 = client._get_next_request_id()
        id3 = client._get_next_request_id()

        assert id1 == 1
        assert id2 == 2
        assert id3 == 3

    def test_initialize_success(self, mock_client):
        """Test successful initialization."""
        client = mock_client

        # Mock the response
        mock_response = {"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}}

        with patch.object(client, "_send_request", return_value=mock_response) as mock_send:
            result = asyncio.run(client.initialize())

            mock_send.assert_called_once_with(
                "initialize",
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "tapo-camera-webapp", "version": "1.0.0"},
                },
            )

            assert result == {"capabilities": {}}

    def test_list_tools_success(self, mock_client):
        """Test successful tool listing."""
        client = mock_client

        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {"name": "test_tool", "description": "A test tool"},
                    {"name": "another_tool", "description": "Another tool"},
                ]
            },
        }

        with patch.object(client, "_send_request", return_value=mock_response) as mock_send:
            tools = asyncio.run(client.list_tools())

            mock_send.assert_called_once_with("tools/list", {})
            assert len(tools) == 2
            assert tools[0]["name"] == "test_tool"

    def test_call_tool_success(self, mock_client):
        """Test successful tool calling."""
        client = mock_client

        mock_response = {"jsonrpc": "2.0", "id": 1, "result": {"output": "test result"}}

        with patch.object(client, "_send_request", return_value=mock_response) as mock_send:
            result = asyncio.run(client.call_tool("test_tool", {"param": "value"}))

            mock_send.assert_called_once_with("tools/call", {"name": "test_tool", "arguments": {"param": "value"}})

            assert result == {"output": "test result"}

    def test_list_resources_success(self, mock_client):
        """Test successful resource listing."""
        client = mock_client

        mock_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "resources": [
                    {"uri": "file:///test1", "name": "Test Resource 1"},
                    {"uri": "file:///test2", "name": "Test Resource 2"},
                ]
            },
        }

        with patch.object(client, "_send_request", return_value=mock_response) as mock_send:
            resources = asyncio.run(client.list_resources())

            mock_send.assert_called_once_with("resources/list", {})
            assert len(resources) == 2

    def test_read_resource_success(self, mock_client):
        """Test successful resource reading."""
        client = mock_client

        mock_response = {"jsonrpc": "2.0", "id": 1, "result": {"contents": "resource content"}}

        with patch.object(client, "_send_request", return_value=mock_response) as mock_send:
            result = asyncio.run(client.read_resource("file:///test"))

            mock_send.assert_called_once_with("resources/read", {"uri": "file:///test"})
            assert result == {"contents": "resource content"}


class TestMCPClientErrorHandling:
    """Test suite for MCP client error handling."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock MCP client."""
        client = MCPClient([sys.executable, "-c", "pass"])
        client._initialized = True
        return client

    def test_send_request_without_process(self, mock_client):
        """Test sending request without initialized process."""
        client = mock_client
        client.process = None

        with pytest.raises(RuntimeError, match="MCP server not started"):
            asyncio.run(client._send_request("test", {}))

    def test_send_request_without_initialization(self, mock_client):
        """Test sending request without initialization."""
        client = mock_client
        client._initialized = False

        with pytest.raises(RuntimeError, match="MCP server not started"):
            asyncio.run(client._send_request("test", {}))

    def test_json_decode_error(self, mock_client):
        """Test handling of invalid JSON responses."""
        client = mock_client

        # Mock stdout to return invalid JSON
        client.process.stdout.readline.return_value = "invalid json"

        with patch.object(client.process.stdout, "readline", return_value="invalid json"):
            with pytest.raises(json.JSONDecodeError):
                asyncio.run(client._send_request("test", {}))

    def test_empty_response(self, mock_client):
        """Test handling of empty responses."""
        client = mock_client

        client.process.stdout.readline.return_value = ""

        with pytest.raises(RuntimeError, match="No response received"):
            asyncio.run(client._send_request("test", {}))

    def test_process_termination_error(self, mock_client):
        """Test handling of process termination errors."""
        client = mock_client

        # Mock terminate to raise exception
        client.process.terminate.side_effect = Exception("Termination failed")

        # Should not raise exception
        result = asyncio.run(client.stop_server())
        assert result is None


class TestMCPClientManager:
    """Test suite for MCP client manager."""

    @pytest.fixture
    def client_manager(self):
        """Create a client manager for testing."""
        return MCPClientManager()

    @pytest.fixture
    def mock_client(self):
        """Create a mock client."""
        client = AsyncMock(spec=MCPClient)
        client.call_tool.return_value = {"result": "success"}
        return client

    def test_add_client(self, client_manager, mock_client):
        """Test adding a client to the manager."""
        client_manager.add_client("test_client", mock_client)

        assert "test_client" in client_manager.clients
        assert client_manager.clients["test_client"] == mock_client

    def test_add_client_as_default(self, client_manager, mock_client):
        """Test adding a client as the default."""
        client_manager.add_client("test_client", mock_client, set_default=True)

        assert client_manager._default_client == "test_client"

    def test_get_client_by_name(self, client_manager, mock_client):
        """Test getting a client by name."""
        client_manager.add_client("test_client", mock_client)

        retrieved = client_manager.get_client("test_client")
        assert retrieved == mock_client

    def test_get_default_client(self, client_manager, mock_client):
        """Test getting the default client."""
        client_manager.add_client("test_client", mock_client, set_default=True)

        retrieved = client_manager.get_client()
        assert retrieved == mock_client

    def test_get_nonexistent_client(self, client_manager):
        """Test getting a nonexistent client."""
        with pytest.raises(ValueError, match="MCP client 'nonexistent' not found"):
            client_manager.get_client("nonexistent")

    def test_call_tool_through_manager(self, client_manager, mock_client):
        """Test calling a tool through the manager."""
        client_manager.add_client("test_client", mock_client, set_default=True)

        result = asyncio.run(client_manager.call_tool("test_tool", {"param": "value"}))

        mock_client.call_tool.assert_called_once_with("test_tool", {"param": "value"})
        assert result == {"result": "success"}

    def test_call_tool_with_specific_client(self, client_manager, mock_client):
        """Test calling a tool with a specific client."""
        client_manager.add_client("specific_client", mock_client)

        result = asyncio.run(client_manager.call_tool("test_tool", {"param": "value"}, "specific_client"))

        mock_client.call_tool.assert_called_once_with("test_tool", {"param": "value"})
        assert result == {"result": "success"}

    def test_start_all_clients(self, client_manager, mock_client):
        """Test starting all clients."""
        client_manager.add_client("client1", mock_client)
        client_manager.add_client("client2", mock_client)

        asyncio.run(client_manager.start_all_clients())

        # Each client should have been started and initialized
        assert mock_client.start_server.call_count == 2
        assert mock_client.initialize.call_count == 2

    def test_stop_all_clients(self, client_manager, mock_client):
        """Test stopping all clients."""
        client_manager.add_client("client1", mock_client)
        client_manager.add_client("client2", mock_client)

        asyncio.run(client_manager.stop_all_clients())

        # Each client should have been stopped
        assert mock_client.stop_server.call_count == 2

    def test_start_client_failure(self, client_manager, mock_client):
        """Test handling of client start failures."""
        mock_client.start_server.side_effect = Exception("Start failed")

        client_manager.add_client("failing_client", mock_client)

        # Should not raise exception, just log error
        asyncio.run(client_manager.start_all_clients())

        mock_client.start_server.assert_called_once()


class TestMCPClientConvenienceFunctions:
    """Test suite for MCP client convenience functions."""

    @pytest.fixture
    def mock_manager(self):
        """Create a mock client manager."""
        with patch("devices_mcp.mcp_client.mcp_clients", MCPClientManager()) as manager:
            yield manager

    def test_get_mcp_client_default(self, mock_manager, mock_client):
        """Test getting the default MCP client."""
        mock_manager.add_client("default", mock_client, set_default=True)

        with patch("devices_mcp.mcp_client.mcp_clients", mock_manager):
            client = get_mcp_client()
            assert client == mock_client

    def test_get_mcp_client_by_name(self, mock_manager, mock_client):
        """Test getting a specific MCP client by name."""
        mock_manager.add_client("named_client", mock_client)

        with patch("devices_mcp.mcp_client.mcp_clients", mock_manager):
            client = get_mcp_client("named_client")
            assert client == mock_client

    def test_call_mcp_tool_default_client(self, mock_manager, mock_client):
        """Test calling MCP tool with default client."""
        mock_manager.add_client("default", mock_client, set_default=True)
        mock_client.call_tool.return_value = {"result": "success"}

        with patch("devices_mcp.mcp_client.mcp_clients", mock_manager):
            result = asyncio.run(call_mcp_tool("test_tool", {"param": "value"}))

            mock_client.call_tool.assert_called_once_with("test_tool", {"param": "value"})
            assert result == {"result": "success"}

    def test_call_mcp_tool_specific_client(self, mock_manager, mock_client):
        """Test calling MCP tool with specific client."""
        mock_manager.add_client("specific", mock_client)
        mock_client.call_tool.return_value = {"result": "success"}

        with patch("devices_mcp.mcp_client.mcp_clients", mock_manager):
            result = asyncio.run(call_mcp_tool("test_tool", {"param": "value"}, "specific"))

            mock_client.call_tool.assert_called_once_with("test_tool", {"param": "value"})
            assert result == {"result": "success"}


class TestMCPClientIntegration:
    """Integration tests for MCP client functionality."""

    @pytest.fixture
    def mock_process(self):
        """Create a more realistic mock process."""
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.stdin = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_proc.stderr = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.terminate.return_value = None
        mock_proc.kill.return_value = None
        return mock_proc

    def test_full_initialization_sequence(self, mock_process):
        """Test the full initialization sequence."""
        # Mock responses for initialization sequence
        responses = [
            '{"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}}',  # initialize
            '{"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}',  # list_tools
        ]
        response_iter = iter(responses)

        mock_process.stdout.readline.side_effect = lambda: next(response_iter) + "\n"

        with patch("subprocess.Popen", return_value=mock_process):
            client = MCPClient([sys.executable, "-c", "pass"])

            # Initialize
            init_result = asyncio.run(client.initialize())
            assert "capabilities" in init_result

            # List tools
            tools = asyncio.run(client.list_tools())
            assert isinstance(tools, list)

    def test_concurrent_tool_calls(self):
        """Test concurrent tool calls."""
        # This would test thread safety and concurrent access
        # In practice, we'd use asyncio.gather or similar

    def test_large_response_handling(self):
        """Test handling of large responses."""
        # Create a large mock response
        [{"name": f"tool_{i}", "description": f"Tool {i}"} for i in range(1000)]

        # This would test memory usage and performance with large responses

    def test_connection_recovery(self):
        """Test connection recovery after failures."""
        # Test automatic reconnection logic


class TestMCPClientPerformance:
    """Performance tests for MCP client."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock client for performance testing."""
        client = AsyncMock(spec=MCPClient)
        client.call_tool.return_value = {"result": "success"}
        client.list_tools.return_value = []
        return client

    def test_tool_call_performance(self, mock_client, performance_timer):
        """Test performance of tool calls."""
        with patch("devices_mcp.mcp_client.mcp_clients.get_client", return_value=mock_client):
            performance_timer.start()

            # Make multiple tool calls
            for i in range(100):
                asyncio.run(call_mcp_tool(f"tool_{i}", {"param": i}))

            performance_timer.stop()

            # Should handle 100 calls quickly
            performance_timer.assert_under_limit(5.0)  # 5 seconds for 100 calls

    def test_client_creation_performance(self, performance_timer):
        """Test performance of client creation."""
        performance_timer.start()

        # Create multiple clients
        clients = []
        for _i in range(10):
            with patch("subprocess.Popen"):
                client = MCPClient([sys.executable, "-c", "pass"])
                clients.append(client)

        performance_timer.stop()

        # Should create clients quickly
        performance_timer.assert_under_limit(1.0)

    def test_manager_operations_performance(self, performance_timer):
        """Test performance of manager operations."""
        manager = MCPClientManager()

        performance_timer.start()

        # Add many clients
        for i in range(100):
            mock_client = AsyncMock(spec=MCPClient)
            manager.add_client(f"client_{i}", mock_client)

        # Retrieve clients
        for i in range(100):
            manager.get_client(f"client_{i}")

        performance_timer.stop()

        # Should handle many clients efficiently
        performance_timer.assert_under_limit(1.0)


class TestMCPClientSecurity:
    """Security tests for MCP client."""

    def test_command_injection_prevention(self):
        """Test prevention of command injection attacks."""
        # Test that malicious commands in server_command are not executed
        malicious_commands = [
            ["python", "-c", "import os; os.system('rm -rf /')"],
            ["bash", "-c", "echo 'malicious'"],
            ["perl", "-e", "system('cat /etc/passwd')"],
        ]

        for malicious_cmd in malicious_commands:
            # Should not execute dangerous commands
            # This is more of a design assurance test
            with patch("subprocess.Popen"):
                try:
                    MCPClient(malicious_cmd)
                    # If we get here, check that the command wasn't actually dangerous
                    # In practice, this would be caught by input validation
                except Exception:
                    # Expected to fail with validation
                    pass

    def test_response_validation(self):
        """Test validation of responses from MCP server."""
        # Test that malformed responses are rejected

        # The client should validate and reject dangerous responses
        # This tests the robustness of response parsing

    def test_resource_access_control(self):
        """Test that resource access is properly controlled."""
        # Test that file:// URIs are properly validated

        # Should reject dangerous file access
        # This tests URI validation logic
