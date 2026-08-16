"""Tests for Ring API routes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.server import WebServer
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    server = WebServer()
    return TestClient(server.app)


class TestRingAPI:
    def test_status_disabled(self, client):
        with patch("devices_mcp.config.get_config") as mock_cfg:
            mock_cfg.return_value = {"ring": {"enabled": False}}
            r = client.get("/api/ring/status")
        assert r.status_code == 200
        data = r.json()
        assert data["enabled"] is False
        assert data["connected"] is False

    def test_init_requires_password_without_token(self, client):
        with patch("devices_mcp.config.get_config") as mock_cfg:
            mock_cfg.return_value = {
                "ring": {
                    "enabled": True,
                    "email": "user@example.com",
                    "password": None,
                    "token_file": "missing.cache",
                }
            }
            with patch(
                "devices_mcp.integrations.ring_client.ring_has_cached_token",
                return_value=False,
            ):
                r = client.post("/api/ring/init")
        assert r.status_code == 400
        assert "password" in r.json()["detail"].lower()

    def test_init_allows_token_only(self, client):
        mock_client = MagicMock()
        mock_client.is_2fa_pending = False
        mock_client.is_initialized = True
        mock_client.last_error = None

        with patch("devices_mcp.config.get_config") as mock_cfg:
            mock_cfg.return_value = {
                "ring": {
                    "enabled": True,
                    "email": "user@example.com",
                    "password": None,
                    "token_file": "ring_token.cache",
                }
            }
            with patch(
                "devices_mcp.integrations.ring_client.ring_has_cached_token",
                return_value=True,
            ):
                with patch(
                    "backend.routes.ring.init_ring_client",
                    new_callable=AsyncMock,
                    return_value=mock_client,
                ):
                    r = client.post("/api/ring/init")
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_refresh_returns_summary(self, client):
        mock_client = MagicMock()
        mock_client.is_initialized = True
        mock_client._update_data = AsyncMock()
        mock_client.get_summary = AsyncMock(
            return_value={
                "initialized": True,
                "2fa_pending": False,
                "doorbells": [{"id": "1", "name": "Front"}],
                "doorbell_count": 1,
                "alarm": None,
                "alarm_devices": {"total": 2, "contact_sensors": 1, "motion_sensors": 1},
                "recent_events": [],
                "last_event": None,
            }
        )

        with patch("backend.routes.ring.get_ring_client", return_value=mock_client):
            r = client.post("/api/ring/refresh")
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["summary"]["doorbell_count"] == 1
