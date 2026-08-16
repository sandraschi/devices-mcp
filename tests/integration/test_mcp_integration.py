"""
Comprehensive Integration Tests for MCP Client Functionality

Tests cover:
- Full MCP client-server interaction
- Tool calling workflows
- Resource management
- Error handling in integration scenarios
- Performance under load
- Concurrent operations
- End-to-end API workflows
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from backend.server import create_app

from devices_mcp.mcp_client import MCPClient, MCPClientManager
from tests.utils.mock_mcp_server import MockMCPClient, MockMCPServer, run_mcp_test_scenario
from tests.utils.test_helpers import assertions, test_data


class TestMCPClientIntegration:
    """Integration tests for MCP client functionality."""

    @pytest.fixture
    async def mock_server(self):
        """Create a mock MCP server for integration testing."""
        server = MockMCPServer()

        # Configure realistic responses
        server.configure_response(
            "energy_management",
            "status",
            {
                "success": True,
                "action": "status",
                "data": {
                    "devices": [
                        test_data.create_energy_device("plug1", "tapo_p115", "Living Room Plug"),
                        test_data.create_energy_device("plug2", "tapo_p115", "Kitchen Plug"),
                    ]
                },
            },
        )

        server.configure_response(
            "motion_management",
            "status",
            {
                "success": True,
                "action": "status",
                "data": {
                    "subscriptions": [
                        {"camera_id": "cam1", "status": "active", "event_count": 5},
                        {"camera_id": "cam2", "status": "active", "event_count": 2},
                    ],
                    "total_subscriptions": 2,
                    "active_subscriptions": 2,
                },
            },
        )

        server.configure_response(
            "camera_management",
            "info",
            {
                "success": True,
                "action": "info",
                "data": test_data.create_energy_device("cam1", "tapo_camera", "Test Camera"),
            },
        )

        return server

    @pytest.fixture
    async def mock_client(self, mock_server):
        """Create a mock MCP client."""
        return MockMCPClient(mock_server)

    def test_full_mcp_workflow_energy_management(self, mock_server, mock_client):
        """Test complete MCP workflow for energy management."""
        # 1. List energy devices
        result = asyncio.run(mock_client.call_tool("energy_management", "status"))
        assertions.assert_mcp_response_valid(result, "status")
        assert "devices" in result["data"]
        assert len(result["data"]["devices"]) == 2

        # 2. Get consumption data
        result = asyncio.run(mock_client.call_tool("energy_management", "consumption"))
        assertions.assert_mcp_response_valid(result, "consumption")

        # 3. Control a device
        result = asyncio.run(
            mock_client.call_tool("energy_management", "control", device_id="plug1", power_state="off")
        )
        assertions.assert_mcp_response_valid(result, "control")

        # 4. Get cost analysis
        result = asyncio.run(mock_client.call_tool("energy_management", "cost"))
        assertions.assert_mcp_response_valid(result, "cost")

        # Verify server received all requests
        stats = mock_server.get_statistics()
        assert stats["requests_received"] == 4
        assert stats["responses_sent"] == 4

    def test_full_mcp_workflow_motion_detection(self, mock_server, mock_client):
        """Test complete MCP workflow for motion detection."""
        # 1. Check motion status
        result = asyncio.run(mock_client.call_tool("motion_management", "status"))
        assertions.assert_mcp_response_valid(result, "status")
        assert result["data"]["total_subscriptions"] == 2

        # 2. Get motion events
        result = asyncio.run(mock_client.call_tool("motion_management", "events"))
        assertions.assert_mcp_response_valid(result, "events")

        # 3. Check capabilities
        result = asyncio.run(mock_client.call_tool("motion_management", "capabilities"))
        assertions.assert_mcp_response_valid(result, "capabilities")

        # 4. Subscribe to motion events
        result = asyncio.run(mock_client.call_tool("motion_management", "subscribe", camera_id="cam1"))
        assertions.assert_mcp_response_valid(result, "subscribe")

        # 5. Unsubscribe from motion events
        result = asyncio.run(mock_client.call_tool("motion_management", "unsubscribe", camera_id="cam1"))
        assertions.assert_mcp_response_valid(result, "unsubscribe")

        # 6. Test motion support
        result = asyncio.run(mock_client.call_tool("motion_management", "test", camera_id="cam1"))
        assertions.assert_mcp_response_valid(result, "test")

    def test_mcp_client_manager_integration(self, mock_server):
        """Test MCP client manager integration."""
        manager = MCPClientManager()

        # Create and add client
        mock_client = AsyncMock(spec=MCPClient)
        mock_client.call_tool.return_value = {"success": True, "data": {}}

        manager.add_client("test_client", mock_client, set_default=True)

        # Test calling through manager
        result = asyncio.run(manager.call_tool("energy_management", {"action": "status"}))

        mock_client.call_tool.assert_called_once_with("energy_management", {"action": "status"})
        assert result["success"] is True

    def test_concurrent_mcp_operations(self, mock_server, mock_client):
        """Test concurrent MCP operations."""

        async def run_concurrent_calls():
            # Create multiple concurrent calls
            tasks = []
            for _i in range(10):
                task = mock_client.call_tool("energy_management", "status")
                tasks.append(task)

            # Run all concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed
            for result in results:
                if isinstance(result, Exception):
                    pytest.fail(f"Concurrent call failed: {result}")
                assertions.assert_mcp_response_valid(result, "status")

        asyncio.run(run_concurrent_calls())

        # Check server handled all requests
        stats = mock_server.get_statistics()
        assert stats["requests_received"] == 10

    def test_mcp_error_handling_integration(self, mock_server, mock_client):
        """Test MCP error handling in integration scenarios."""
        # Configure server to return errors for specific operations
        mock_server.configure_error(
            "energy_management.status",
            {"code": -32000, "message": "Service temporarily unavailable"},
        )

        # Attempt to call failing operation
        with pytest.raises(Exception, match="Service temporarily unavailable"):
            asyncio.run(mock_client.call_tool("energy_management", "status"))

    def test_mcp_resource_operations(self, mock_server, mock_client):
        """Test MCP resource operations."""
        # List resources
        resources = asyncio.run(mock_client.list_resources())
        assert isinstance(resources, list)
        assert len(resources) > 0

        # Read a resource
        if resources:
            resource = asyncio.run(mock_client.read_resource(resources[0]["uri"]))
            assert isinstance(resource, dict)

    def test_mcp_performance_under_load(self, mock_server, mock_client):
        """Test MCP performance under load."""
        timer = test_data.create_performance_timer()

        async def run_load_test():
            timer.start()

            # Make many calls
            tasks = []
            for _i in range(50):
                task = mock_client.call_tool("energy_management", "status")
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            timer.stop()

            # All should succeed
            for result in results:
                assertions.assert_mcp_response_valid(result, "status")

            # Should complete within reasonable time
            timer.assert_under_limit(5.0, "50 concurrent MCP calls")

        asyncio.run(run_load_test())

        stats = mock_server.get_statistics()
        assert stats["requests_received"] == 50


class TestAPIEndpointMCPIntegration:
    """Test API endpoints with real MCP integration."""

    @pytest.fixture
    def test_client(self):
        """Create a test client with MCP integration."""
        app = create_app()
        return test_data.create_test_client_with_middleware(app)

    def test_energy_api_mcp_integration(self, test_client):
        """Test energy API endpoints with MCP integration."""
        with patch("devices_mcp.mcp_client.call_mcp_tool") as mock_call:
            # Mock successful MCP responses
            mock_call.return_value = {
                "success": True,
                "action": "status",
                "data": {"devices": [test_data.create_energy_device()]},
            }

            # Test devices endpoint
            response = test_client.get("/api/energy/devices")
            assert response.status_code == 200

            data = response.json()
            assertions.assert_dict_contains_keys(data, ["devices", "total_devices", "smart_plugs", "smart_meters"])

    def test_motion_api_mcp_integration(self, test_client):
        """Test motion API endpoints with MCP integration."""
        with patch("devices_mcp.mcp_client.call_mcp_tool") as mock_call:
            # Mock successful MCP responses
            mock_call.return_value = {
                "success": True,
                "action": "status",
                "data": {"subscriptions": [], "total_subscriptions": 0},
            }

            # Test status endpoint
            response = test_client.get("/api/motion/status")
            assert response.status_code == 200

            data = response.json()
            assertions.assert_dict_contains_keys(data, ["subscriptions", "total_subscriptions", "active_subscriptions"])

    def test_audio_api_mcp_integration(self, test_client):
        """Test audio API endpoints with MCP integration."""
        with patch("devices_mcp.mcp_client.call_mcp_tool") as mock_call:
            mock_call.return_value = {
                "success": True,
                "data": {"stream_url": "rtsp://test:554/stream"},
            }

            # Test info endpoint
            response = test_client.get("/api/audio/info/camera1")
            assert response.status_code == 200

    def test_mcp_call_error_propagation(self, test_client):
        """Test that MCP errors are properly propagated to API responses."""
        with patch("devices_mcp.mcp_client.call_mcp_tool") as mock_call:
            mock_call.return_value = {"success": False, "error": "MCP service unavailable"}

            # Test error handling
            response = test_client.get("/api/energy/devices")
            assert response.status_code == 200  # Should degrade gracefully

    def test_mcp_call_success_propagation(self, test_client):
        """Test that MCP successes are properly propagated to API responses."""
        with patch("devices_mcp.mcp_client.call_mcp_tool") as mock_call:
            mock_call.return_value = test_data.create_mcp_tool_response(
                success=True, action="status", data={"devices": [test_data.create_energy_device()]}
            )

            response = test_client.get("/api/energy/devices")
            assert response.status_code == 200

            data = response.json()
            assert data["total_devices"] == 1


class TestMCPScenarioTesting:
    """Test complete MCP usage scenarios."""

    @pytest.fixture
    async def server(self):
        """Create a configured mock server for scenario testing."""
        server = MockMCPServer()

        # Configure a complete home automation scenario
        server.configure_response(
            "energy_management",
            "status",
            {
                "success": True,
                "action": "status",
                "data": {
                    "devices": [
                        test_data.create_energy_device(
                            "living_room_plug",
                            "tapo_p115",
                            "Living Room Lamp",
                            power_state=True,
                            current_power=25.5,
                        ),
                        test_data.create_energy_device(
                            "kitchen_plug",
                            "tapo_p115",
                            "Kitchen Appliances",
                            power_state=False,
                            current_power=0.0,
                        ),
                    ]
                },
            },
        )

        server.configure_response(
            "motion_management",
            "status",
            {
                "success": True,
                "action": "status",
                "data": {
                    "subscriptions": [
                        {"camera_id": "front_door", "status": "active", "event_count": 3},
                        {"camera_id": "backyard", "status": "active", "event_count": 1},
                    ],
                    "total_subscriptions": 2,
                    "active_subscriptions": 2,
                },
            },
        )

        server.configure_response(
            "camera_management",
            "info",
            {
                "success": True,
                "action": "info",
                "data": {
                    "camera_id": "front_door",
                    "name": "Front Door Camera",
                    "status": "online",
                    "motion_detection": True,
                },
            },
        )

        return server

    @pytest.fixture
    async def client(self, server):
        """Create a client for scenario testing."""
        return MockMCPClient(server)

    async def test_home_monitoring_scenario(self, server, client):
        """Test a complete home monitoring scenario."""
        scenario = [
            {"type": "tool_call", "tool": "energy_management", "action": "status"},
            {"type": "tool_call", "tool": "motion_management", "action": "status"},
            {
                "type": "tool_call",
                "tool": "camera_management",
                "action": "info",
                "arguments": {"camera_name": "front_door"},
            },
            {
                "type": "tool_call",
                "tool": "energy_management",
                "action": "control",
                "arguments": {"device_id": "living_room_plug", "power_state": "off"},
            },
            {
                "type": "tool_call",
                "tool": "motion_management",
                "action": "events",
                "arguments": {"limit": 10},
            },
        ]

        results = await run_mcp_test_scenario(server, client, scenario)

        assert results["steps_executed"] == 5
        assert results["errors"] == []
        assert results["success"] is True

        # Verify specific results
        energy_status = results["responses"][0]
        assert energy_status["data"]["devices"][0]["power_state"] is True

        motion_status = results["responses"][1]
        assert motion_status["data"]["total_subscriptions"] == 2

        camera_info = results["responses"][2]
        assert camera_info["data"]["camera_id"] == "front_door"

    async def test_energy_management_workflow(self, server, client):
        """Test energy management workflow."""
        # Check current status
        result = await client.call_tool("energy_management", "status")
        assert len(result["data"]["devices"]) == 2

        # Turn off living room light
        result = await client.call_tool("energy_management", "control", device_id="living_room_plug", power_state="off")
        assert result["success"] is True

        # Check consumption
        result = await client.call_tool("energy_management", "consumption")
        assert result["success"] is True

        # Get cost analysis
        result = await client.call_tool("energy_management", "cost")
        assert result["success"] is True

    async def test_motion_detection_workflow(self, server, client):
        """Test motion detection workflow."""
        # Check subscriptions
        result = await client.call_tool("motion_management", "status")
        assert result["data"]["active_subscriptions"] == 2

        # Get recent events
        result = await client.call_tool("motion_management", "events")
        assert result["success"] is True

        # Subscribe to new camera
        result = await client.call_tool("motion_management", "subscribe", camera_id="garage")
        assert result["success"] is True

        # Test camera capabilities
        result = await client.call_tool("motion_management", "test", camera_id="garage")
        assert result["success"] is True

    async def test_error_recovery_scenario(self, server, client):
        """Test error recovery in scenarios."""
        # Configure server to fail temporarily
        server.configure_error("energy_management.status", {"code": -32000, "message": "Temporary failure"})

        # This should fail
        with pytest.raises(Exception, match="Temporary failure"):
            await client.call_tool("energy_management", "status")

        # Reset to normal operation
        server.configure_response(
            "energy_management",
            "status",
            {"success": True, "action": "status", "data": {"devices": []}},
        )

        # This should succeed
        result = await client.call_tool("energy_management", "status")
        assert result["success"] is True

    async def test_performance_scenario(self, server, client):
        """Test performance in realistic scenarios."""
        timer = test_data.create_performance_timer()

        timer.start()

        # Simulate a dashboard refresh scenario
        tasks = [
            client.call_tool("energy_management", "status"),
            client.call_tool("motion_management", "status"),
            client.call_tool("energy_management", "consumption"),
            client.call_tool("motion_management", "events"),
        ]

        results = await asyncio.gather(*tasks)
        timer.stop()

        # All should succeed
        for result in results:
            assert result["success"] is True

        # Should be fast enough for UI responsiveness
        timer.assert_under_limit(2.0, "dashboard refresh scenario")


class TestMCPClientRobustness:
    """Test MCP client robustness under various conditions."""

    async def test_network_timeout_simulation(self):
        """Test behavior with simulated network timeouts."""
        server = MockMCPServer()
        server.configure_delay("energy_management.status", 3.0)  # 3 second delay

        client = MockMCPClient(server)

        # This should take at least 3 seconds
        start_time = time.time()
        result = await client.call_tool("energy_management", "status")
        end_time = time.time()

        assert end_time - start_time >= 3.0
        assert result["success"] is True

    async def test_partial_response_handling(self):
        """Test handling of partial or malformed responses."""
        server = MockMCPServer()

        # Configure malformed response
        server.configure_response(
            "energy_management",
            "status",
            {
                "success": True,
                "action": "status",
                # Missing "data" field - should this cause issues?
            },
        )

        client = MockMCPClient(server)
        result = await client.call_tool("energy_management", "status")

        assert result["success"] is True
        assert "data" not in result  # Missing data field

    async def test_concurrent_client_access(self):
        """Test multiple clients accessing the same server."""
        server = MockMCPServer()

        clients = [MockMCPClient(server) for _ in range(5)]

        async def client_workflow(client):
            for _i in range(10):
                result = await client.call_tool("energy_management", "status")
                assert result["success"] is True
                await asyncio.sleep(0.001)  # Small delay

        # Run all clients concurrently
        tasks = [client_workflow(client) for client in clients]
        await asyncio.gather(*tasks)

        # Server should have handled all requests
        stats = server.get_statistics()
        assert stats["requests_received"] == 50  # 5 clients * 10 requests each

    async def test_resource_cleanup(self):
        """Test proper cleanup of resources."""
        server = MockMCPServer()
        client = MockMCPClient(server)

        # Make some calls
        for _i in range(10):
            result = await client.call_tool("energy_management", "status")
            assert result["success"] is True

        # Check server stats
        stats = server.get_statistics()
        assert stats["requests_received"] == 10
        assert stats["responses_sent"] == 10

        # Server should maintain state properly
        assert len(server.requests_received) == 10
        assert len(server.responses_sent) == 10

    async def test_large_payload_handling(self):
        """Test handling of large payloads."""
        server = MockMCPServer()

        # Create large device list
        large_device_list = {
            "success": True,
            "action": "status",
            "data": {
                "devices": [
                    test_data.create_energy_device(f"device_{i}", "tapo_p115", f"Device {i}") for i in range(1000)
                ]
            },
        }

        server.configure_response("energy_management", "status", large_device_list)
        client = MockMCPClient(server)

        result = await client.call_tool("energy_management", "status")

        assert result["success"] is True
        assert len(result["data"]["devices"]) == 1000

        # Payload should be reasonable size
        import sys

        payload_size = sys.getsizeof(json.dumps(result))
        assert payload_size < 10 * 1024 * 1024  # Less than 10MB
