"""Tests for unified sensor registry."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_sensor_overview_includes_tapo():
    with patch(
        "devices_mcp.tools.energy.tapo_plug_tools.tapo_plug_manager.get_all_devices",
        new_callable=AsyncMock,
        return_value=[MagicMock(device_id="p1", name="Plug")],
    ):
        with patch("devices_mcp.integrations.shelly_client.get_shelly_client", return_value=None):
            with patch("devices_mcp.integrations.homeassistant_client.get_homeassistant_client", return_value=None):
                with patch("devices_mcp.integrations.ring_client.get_ring_client", return_value=None):
                    from devices_mcp.core.sensor_registry import get_sensor_overview

                    overview = await get_sensor_overview()
    assert overview["total_sources"] >= 1
    tapo = next(s for s in overview["sources"] if s["id"] == "tapo_p115")
    assert tapo["count"] == 1
