"""
Integration tests for web API endpoints.
"""

from unittest.mock import AsyncMock, patch

import pytest
from backend.server import create_app
from fastapi.testclient import TestClient


class TestWebAPI:
    """Test web API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)

    @pytest.mark.integration
    @pytest.mark.mock
    def test_health_endpoint(self, client):
        """Test health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.mock
    def test_dashboard_endpoint(self, client):
        """Test dashboard endpoint returns 200."""
        response = client.get("/")
        assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.mock
    def test_api_cameras_endpoint(self, client):
        """Test cameras API endpoint."""
        with patch("backend.routes.cameras.call_mcp_tool") as mock_call:
            mock_call.return_value = {"cameras": []}

            response = client.get("/api/cameras")
            assert response.status_code == 200

            data = response.json()
            assert "cameras" in data
            assert "count" in data

    @pytest.mark.integration
    @pytest.mark.mock
    def test_connection_health_endpoint(self, client):
        """Test connection health endpoint."""
        response = client.get("/api/system/connection-health")
        assert response.status_code == 200

        data = response.json()
        assert "total_devices" in data
        assert "online" in data
        assert "offline" in data
        assert "health_percentage" in data
        assert "devices" in data


class TestMCPIntegration:
    """Test MCP server integration."""

    @pytest.mark.integration
    @pytest.mark.mock
    @pytest.mark.asyncio
    async def test_mcp_tool_call(self):
        """Test MCP tool calling."""
        from devices_mcp.mcp_client import call_mcp_tool

        with patch("devices_mcp.mcp_client.MCPClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.start_server.return_value = None
            mock_client.call_tool.return_value = {"cameras": []}
            mock_client_class.return_value = mock_client

            result = await call_mcp_tool("camera_management", {"action": "list"})
            assert result == {"cameras": []}
