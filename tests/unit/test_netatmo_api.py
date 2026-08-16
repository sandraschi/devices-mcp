"""Tests for Netatmo status lazy initialization."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from backend.server import WebServer
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(WebServer().app)


def test_netatmo_status_lazy_init_when_token_present(client):
    mock_svc = MagicMock()
    mock_svc.is_api_ready.return_value = True
    mock_svc.last_error = None

    with patch("devices_mcp.config.get_config") as mock_cfg:
        mock_cfg.return_value = {
            "weather": {
                "integrations": {
                    "netatmo": {
                        "enabled": True,
                        "client_id": "id",
                        "client_secret": "secret",
                        "refresh_token": "refresh-token",
                    }
                }
            }
        }
        with patch("devices_mcp.integrations.netatmo_client.PYATMO_AVAILABLE", True):
            with patch(
                "devices_mcp.integrations.netatmo_client.NetatmoService.get_existing_instance", return_value=None
            ):
                with patch(
                    "devices_mcp.integrations.netatmo_client.NetatmoService.get_instance",
                    new_callable=AsyncMock,
                    return_value=mock_svc,
                ):
                    r = client.get("/api/netatmo/status")
    assert r.status_code == 200
    data = r.json()
    assert data["connected"] is True
