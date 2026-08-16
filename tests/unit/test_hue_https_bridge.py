"""Tests for Hue Bridge Pro HTTPS support."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devices_mcp.tools.lighting.hue_tools import (
    _hue_api_error,
    create_hue_bridge_client,
    probe_hue_bridge,
    validate_hue_username,
)


def test_hue_api_error_unauthorized():
    payload = [{"error": {"type": 1, "description": "unauthorized user"}}]
    err = _hue_api_error(payload)
    assert err is not None
    assert err["type"] == 1


@pytest.mark.asyncio
async def test_probe_hue_bridge_pro_uses_https():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "name": "Hue Bridge pro",
        "modelid": "BSB003",
        "apiversion": "1.77.0",
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await probe_hue_bridge("192.168.0.236")

    assert result["reachable"] is True
    assert result["requires_https"] is True
    assert result["modelid"] == "BSB003"
    assert result["port"] == 443


@pytest.mark.asyncio
async def test_validate_hue_username_rejects_unauthorized():
    mock_bridge = MagicMock()
    mock_bridge.request.return_value = [{"error": {"type": 1, "description": "unauthorized user"}}]

    ok, err = await validate_hue_username("192.168.0.236", "bad-user", mock_bridge)
    assert ok is False
    assert err is not None
    assert "unauthorized" in err.lower()


@pytest.mark.asyncio
async def test_validate_hue_username_accepts_config():
    mock_bridge = MagicMock()
    mock_bridge.request.return_value = {"name": "Hue Bridge pro", "modelid": "BSB003"}

    ok, err = await validate_hue_username("192.168.0.236", "good-user", mock_bridge)
    assert ok is True
    assert err is None


def test_create_hue_bridge_client_https():
    pytest.importorskip("phue")
    bridge = create_hue_bridge_client("192.168.0.236", "user", requires_https=True)
    assert bridge.__class__.__name__ == "HueHttpsBridge"
