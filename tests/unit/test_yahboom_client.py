"""Tests for yahboom-mcp HTTP client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from devices_mcp.integrations.yahboom_client import (
    YahboomMcpClient,
    mcp_call_succeeded,
)


def test_mcp_call_succeeded_variants():
    assert mcp_call_succeeded({"success": True}) is True
    assert mcp_call_succeeded({"status": "success"}) is True
    assert mcp_call_succeeded({"status": "online"}) is True
    assert mcp_call_succeeded({"success": False}) is False


def test_connection_summary():
    client = YahboomMcpClient("http://127.0.0.1:10892")
    summary = client.connection_summary(
        {
            "status": "online",
            "robot_connection": {
                "ros": "connected",
                "cmd_vel_ready": True,
                "ip": "192.168.1.11",
                "video": "active",
                "ssh": "connected",
            },
        }
    )
    assert summary["mcp_online"] is True
    assert summary["ros_connected"] is True
    assert summary["robot_ip"] == "192.168.1.11"


@pytest.mark.asyncio
async def test_move_parses_status_success():
    client = YahboomMcpClient("http://127.0.0.1:10892")
    mock_response = AsyncMock()
    mock_response.raise_for_status = lambda: None
    mock_response.content = b'{"status":"success","command":{"linear":0.2}}'
    mock_response.json = lambda: {"status": "success", "command": {"linear": 0.2}}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = await client.move(linear=0.2, angular=0.0)
        assert mcp_call_succeeded(result) is True


@pytest.mark.asyncio
async def test_unreachable_returns_error_dict():
    client = YahboomMcpClient("http://127.0.0.1:10892")
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.get.side_effect = httpx.ConnectError("refused", request=httpx.Request("GET", client.base_url))
        mock_client_cls.return_value = mock_client

        result = await client.health()
        assert result["success"] is False
        assert "unreachable" in result["error"]
