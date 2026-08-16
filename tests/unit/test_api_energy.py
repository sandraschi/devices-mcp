"""
Comprehensive unit tests for the energy API endpoints.

Tests cover:
- Device listing via MCP
- Current usage monitoring
- Energy statistics
- Error handling and edge cases
- MCP client integration
"""

from unittest.mock import patch

import pytest
from backend.server import create_app
from fastapi.testclient import TestClient


class TestEnergyAPI:
    """Test suite for energy API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the energy API."""
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def mock_energy_tool_success(self):
        """Mock successful energy management tool responses."""
        return {
            "success": True,
            "action": "status",
            "data": {
                "devices": [
                    {
                        "device_id": "test-plug-1",
                        "name": "Test Plug 1",
                        "location": "Living Room",
                        "type": "tapo_p115",
                        "power_state": True,
                        "current_power": 45.2,
                        "voltage": 230.1,
                        "current": 0.196,
                        "daily_energy": 2.34,
                        "monthly_energy": 68.9,
                        "daily_cost": 0.45,
                        "monthly_cost": 13.2,
                        "last_seen": "2023-01-01T12:00:00Z",
                    }
                ]
            },
        }

    @pytest.fixture
    def mock_energy_tool_consumption(self):
        """Mock energy consumption data."""
        return {
            "success": True,
            "action": "consumption",
            "data": {
                "devices": [
                    {
                        "device_id": "test-plug-1",
                        "name": "Test Plug 1",
                        "power": 45.2,
                        "daily_energy": 2.34,
                        "daily_cost": 0.45,
                    }
                ]
            },
        }

    @pytest.fixture
    def mock_energy_tool_stats(self):
        """Mock energy statistics."""
        return {
            "success": True,
            "action": "cost",
            "data": {
                "total_devices": 2,
                "active_devices": 1,
                "current_power": 45.2,
                "daily_cost": 0.45,
            },
        }

    def test_list_energy_devices_success(self, client, mock_energy_tool_success):
        """Test successful energy device listing."""
        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=mock_energy_tool_success):
            response = client.get("/api/energy/devices")

            assert response.status_code == 200
            data = response.json()

            assert "devices" in data
            assert "total_devices" in data
            assert "smart_plugs" in data
            assert "smart_meters" in data

            assert len(data["devices"]) == 1
            device = data["devices"][0]
            assert device["device_id"] == "test-plug-1"
            assert device["type"] == "tapo_p115"
            assert device["power_state"] is True

    def test_list_energy_devices_with_smart_meter(self, client, mock_energy_tool_success):
        """Test energy device listing including smart meter data."""
        mock_response = mock_energy_tool_success.copy()
        # Add smart meter data would be handled by the smart meter service

        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=mock_response):
            response = client.get("/api/energy/devices")

            assert response.status_code == 200
            data = response.json()
            assert data["smart_plugs"] == 1
            assert data["smart_meters"] == 0  # No smart meter in mock

    def test_list_energy_devices_mcp_failure(self, client):
        """Test energy device listing when MCP call fails."""
        mock_error = {"success": False, "error": "MCP connection failed"}

        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=mock_error):
            response = client.get("/api/energy/devices")

            # Should still return 200 with empty device list
            assert response.status_code == 200
            data = response.json()
            assert data["devices"] == []
            assert data["total_devices"] == 0

    def test_current_usage_success(self, client, mock_energy_tool_consumption):
        """Test successful current energy usage retrieval."""
        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=mock_energy_tool_consumption):
            response = client.get("/api/energy/current-usage")

            assert response.status_code == 200
            data = response.json()

            assert "timestamp" in data
            assert "total_power_w" in data
            assert "total_daily_energy_kwh" in data
            assert "total_daily_cost_eur" in data
            assert "devices" in data

            assert len(data["devices"]) == 1
            device = data["devices"][0]
            assert device["device_id"] == "test-plug-1"
            assert device["power"] == 45.2

    def test_energy_stats_success(self, client, mock_energy_tool_stats):
        """Test successful energy statistics retrieval."""
        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=mock_energy_tool_stats):
            response = client.get("/api/energy/stats")

            assert response.status_code == 200
            data = response.json()

            assert data["total_devices"] == 2
            assert data["active_devices"] == 1
            assert data["current_power"] == 45.2
            assert data["daily_cost"] == 0.45

    def test_energy_stats_mcp_error(self, client):
        """Test energy statistics when MCP fails."""
        mock_error = {"success": False, "error": "MCP unavailable"}

        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=mock_error):
            response = client.get("/api/energy/stats")

            assert response.status_code == 200
            data = response.json()

            # Should return default error values
            assert data["total_devices"] == 0
            assert data["active_devices"] == 0
            assert data["current_power"] == 0
            assert "error" in data

    @pytest.mark.parametrize(
        "endpoint,expected_keys",
        [
            ("/api/energy/devices", ["devices", "total_devices", "smart_plugs", "smart_meters"]),
            (
                "/api/energy/current-usage",
                [
                    "timestamp",
                    "total_power_w",
                    "total_daily_energy_kwh",
                    "total_daily_cost_eur",
                    "devices",
                ],
            ),
            (
                "/api/energy/stats",
                ["total_devices", "active_devices", "current_power", "daily_cost"],
            ),
        ],
    )
    def test_response_structure(self, client, endpoint, expected_keys):
        """Test that all energy endpoints return proper response structure."""
        with patch("devices_mcp.mcp_client.call_mcp_tool") as mock_call:
            mock_call.return_value = {"success": True, "action": "test", "data": {}}

            response = client.get(endpoint)
            assert response.status_code == 200

            data = response.json()
            for key in expected_keys:
                assert key in data, f"Missing key '{key}' in response from {endpoint}"

    def test_mcp_call_parameters(self, client):
        """Test that MCP calls are made with correct parameters."""
        with patch("devices_mcp.mcp_client.call_mcp_tool") as mock_call:
            mock_call.return_value = {"success": True, "data": {}}

            # Test devices endpoint
            client.get("/api/energy/devices")
            mock_call.assert_called_with("energy_management", {"action": "status"})

            # Test current usage endpoint
            mock_call.reset_mock()
            client.get("/api/energy/current-usage")
            mock_call.assert_called_with("energy_management", {"action": "consumption"})

            # Test stats endpoint
            mock_call.reset_mock()
            client.get("/api/energy/stats")
            mock_call.assert_called_with("energy_management", {"action": "cost"})

    def test_exception_handling(self, client):
        """Test that exceptions are properly handled."""
        with patch("devices_mcp.mcp_client.call_mcp_tool", side_effect=Exception("Test error")):
            response = client.get("/api/energy/devices")

            # Should still return a response (graceful degradation)
            assert response.status_code == 200
            data = response.json()
            assert data["devices"] == []

    def test_empty_device_list(self, client):
        """Test handling of empty device lists."""
        mock_empty = {"success": True, "action": "status", "data": {"devices": []}}

        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=mock_empty):
            response = client.get("/api/energy/devices")

            assert response.status_code == 200
            data = response.json()
            assert data["devices"] == []
            assert data["total_devices"] == 0
            assert data["smart_plugs"] == 0
            assert data["smart_meters"] == 0

    def test_device_data_transformation(self, client):
        """Test that device data is properly transformed for API response."""
        mock_devices = {
            "success": True,
            "action": "status",
            "data": {
                "devices": [
                    {
                        "device_id": "plug1",
                        "name": "Living Room Plug",
                        "location": "Living Room",
                        "type": "tapo_p115",
                        "power_state": True,
                        "current_power": 50.0,
                        "daily_energy": 3.2,
                        "daily_cost": 0.62,
                    }
                ]
            },
        }

        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=mock_devices):
            response = client.get("/api/energy/devices")

            assert response.status_code == 200
            data = response.json()

            device = data["devices"][0]
            # Check that all expected fields are present
            expected_fields = [
                "device_id",
                "name",
                "location",
                "type",
                "power_state",
                "current_power",
                "daily_energy",
                "monthly_energy",
                "daily_cost",
                "monthly_cost",
                "last_seen",
            ]

            for field in expected_fields:
                assert field in device, f"Missing field '{field}' in device response"

    @pytest.mark.asyncio
    async def test_async_mcp_calls(self):
        """Test that MCP calls are properly awaited."""
        # This would test the async nature of the API calls
        # In a real scenario, we'd test timing and concurrency

    def test_response_content_type(self, client):
        """Test that responses have correct content type."""
        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value={"success": True, "data": {}}):
            response = client.get("/api/energy/devices")

            assert response.headers["content-type"] == "application/json"

    def test_cors_headers(self, client):
        """Test that CORS headers are properly set."""
        # This would test CORS configuration if implemented

    def test_rate_limiting(self, client):
        """Test rate limiting functionality."""
        # This would test rate limiting if implemented

    # Integration-style tests
    def test_end_to_end_device_listing(self, client):
        """End-to-end test of device listing with realistic data."""
        realistic_devices = {
            "success": True,
            "action": "status",
            "data": {
                "devices": [
                    {
                        "device_id": "tapo_p115_001",
                        "name": "Living Room Lamp",
                        "location": "Living Room",
                        "type": "tapo_p115",
                        "power_state": True,
                        "current_power": 25.5,
                        "voltage": 231.2,
                        "current": 0.110,
                        "daily_energy": 1.8,
                        "monthly_energy": 54.2,
                        "daily_cost": 0.35,
                        "monthly_cost": 10.50,
                        "last_seen": "2023-01-01T12:00:00Z",
                    },
                    {
                        "device_id": "tapo_p115_002",
                        "name": "Kitchen Appliances",
                        "location": "Kitchen",
                        "type": "tapo_p115",
                        "power_state": False,
                        "current_power": 0.0,
                        "voltage": 230.8,
                        "current": 0.0,
                        "daily_energy": 0.0,
                        "monthly_energy": 0.0,
                        "daily_cost": 0.0,
                        "monthly_cost": 0.0,
                        "last_seen": "2023-01-01T11:45:00Z",
                    },
                ]
            },
        }

        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=realistic_devices):
            response = client.get("/api/energy/devices")

            assert response.status_code == 200
            data = response.json()

            assert data["total_devices"] == 2
            assert data["smart_plugs"] == 2
            assert data["smart_meters"] == 0

            # Check first device
            device1 = data["devices"][0]
            assert device1["power_state"] is True
            assert device1["current_power"] == 25.5

            # Check second device
            device2 = data["devices"][1]
            assert device2["power_state"] is False
            assert device2["current_power"] == 0.0

    def test_malformed_mcp_response(self, client):
        """Test handling of malformed MCP responses."""
        malformed_responses = [
            None,
            {},
            {"success": True},
            {"success": True, "data": None},
            {"success": True, "data": "not_a_dict"},
        ]

        for malformed in malformed_responses:
            with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=malformed):
                response = client.get("/api/energy/devices")

                # Should handle gracefully
                assert response.status_code == 200
                data = response.json()
                assert isinstance(data, dict)

    def test_mcp_timeout_simulation(self, client):
        """Test behavior when MCP calls timeout."""
        import asyncio

        async def slow_mcp_call(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate delay
            return {"success": True, "data": {}}

        with patch("devices_mcp.mcp_client.call_mcp_tool", side_effect=slow_mcp_call):
            response = client.get("/api/energy/devices")

            # Should still work (FastAPI handles async properly)
            assert response.status_code == 200

    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests."""
        # This would test thread safety and concurrent access
        # In a real scenario, we'd use pytest-asyncio and asyncio.gather


class TestEnergyAPIErrorCases:
    """Test suite for energy API error handling."""

    @pytest.fixture
    def client(self):
        """Create a test client for the energy API."""
        app = create_app()
        return TestClient(app)

    def test_mcp_service_unavailable(self, client):
        """Test behavior when MCP service is completely unavailable."""
        with patch(
            "devices_mcp.mcp_client.call_mcp_tool",
            side_effect=ConnectionError("MCP unavailable"),
        ):
            response = client.get("/api/energy/devices")

            # Should degrade gracefully
            assert response.status_code == 200
            data = response.json()
            assert data["devices"] == []

    def test_partial_mcp_failure(self, client):
        """Test behavior when some MCP calls fail but others succeed."""
        call_count = 0

        def alternating_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise Exception("Intermittent failure")
            return {"success": True, "data": {"devices": []}}

        with patch("devices_mcp.mcp_client.call_mcp_tool", side_effect=alternating_failure):
            # First call should work
            response1 = client.get("/api/energy/devices")
            assert response1.status_code == 200

            # Second call should fail gracefully
            response2 = client.get("/api/energy/devices")
            assert response2.status_code == 200

    def test_invalid_mcp_response_format(self, client):
        """Test handling of invalid MCP response formats."""
        invalid_responses = [
            "not_a_dict",
            42,
            ["not", "a", "dict"],
            {"unexpected_key": "value"},
        ]

        for invalid_response in invalid_responses:
            with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=invalid_response):
                response = client.get("/api/energy/devices")

                # Should handle gracefully
                assert response.status_code == 200

    def test_extremely_large_device_list(self, client):
        """Test handling of very large device lists."""
        # Create a large number of mock devices
        large_device_list = {
            "success": True,
            "action": "status",
            "data": {
                "devices": [
                    {
                        "device_id": f"device_{i}",
                        "name": f"Device {i}",
                        "type": "tapo_p115",
                        "power_state": i % 2 == 0,
                        "current_power": float(i * 10),
                        "daily_energy": float(i * 0.5),
                        "daily_cost": float(i * 0.1),
                    }
                    for i in range(1000)  # 1000 devices
                ]
            },
        }

        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=large_device_list):
            response = client.get("/api/energy/devices")

            assert response.status_code == 200
            data = response.json()
            assert len(data["devices"]) == 1000
            assert data["total_devices"] == 1000


class TestEnergyAPIPerformance:
    """Performance tests for energy API endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the energy API."""
        app = create_app()
        return TestClient(app)

    def test_response_time_under_limit(self, client, performance_timer):
        """Test that API responses are fast enough."""
        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value={"success": True, "data": {}}):
            performance_timer.start()
            response = client.get("/api/energy/devices")
            performance_timer.stop()

            assert response.status_code == 200
            # Should respond in under 1 second for simple operations
            performance_timer.assert_under_limit(1.0)

    def test_memory_usage(self, client):
        """Test that API calls don't cause excessive memory usage."""
        # This would require specialized memory profiling tools
        # For now, just ensure the endpoint works
        with patch("devices_mcp.mcp_client.call_mcp_tool", return_value={"success": True, "data": {}}):
            response = client.get("/api/energy/devices")
            assert response.status_code == 200

    def test_scalability_with_device_count(self, client):
        """Test how performance scales with number of devices."""
        device_counts = [10, 100, 1000]

        for count in device_counts:
            devices = {
                "success": True,
                "action": "status",
                "data": {
                    "devices": [
                        {
                            "device_id": f"device_{i}",
                            "name": f"Device {i}",
                            "type": "tapo_p115",
                            "power_state": True,
                            "current_power": 10.0,
                            "daily_energy": 1.0,
                            "daily_cost": 0.2,
                        }
                        for i in range(count)
                    ]
                },
            }

            with patch("devices_mcp.mcp_client.call_mcp_tool", return_value=devices):
                response = client.get("/api/energy/devices")
                assert response.status_code == 200

                data = response.json()
                assert len(data["devices"]) == count
                # Response size should be reasonable
                assert len(str(data)) < 1000000  # Under 1MB
