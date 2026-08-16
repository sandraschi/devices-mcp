from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devices_mcp.ingest.tapo_p115 import TapoP115IngestionService


@pytest.mark.asyncio
async def test_tapo_p115_retry_logic():
    # Mock config
    config = {
        "account": {"email": "test@example.com", "password": "password"},
        "devices": [{"host": "192.168.0.17", "name": "Test Plug"}],
    }

    # We need to mock ApiClient *inside* the service's module
    with patch("devices_mcp.ingest.tapo_p115.ApiClient") as MockApiClient:
        mock_client_instance = AsyncMock()
        MockApiClient.return_value = mock_client_instance

        # Mock plug that fails twice then succeeds
        mock_plug = AsyncMock()

        # Mock device info return value for the 3rd attempt
        success_info = MagicMock()
        success_info.nickname = "Success Plug"
        success_info.model = "P115"
        success_info.device_id = "test_id"
        success_info.device_on = True

        # Power data for success
        success_power = MagicMock()
        success_power.current_power = 42.0
        success_power.voltage = 230.0
        success_power.current = 0.18

        # Energy data for success
        success_energy = MagicMock()
        success_energy.today_energy = 500
        success_energy.month_energy = 15000

        # Side effects for get_device_info to simulate retries
        # First call to get_device_info in the loop fails
        # Second call to get_device_info in the loop fails
        # Third call to get_device_info in the loop succeeds
        # Wait, the loop calls get_device_info multiple times *per attempt* in the real code
        # Line 151, then line 161.

        # Let's just make the whole p115() call fail or something higher level.
        # Actually, let's make p115() fail.

        side_effects = [
            Exception('Http(reqwest::Error { kind: Request, message: "channel closed" })'),
            Exception('Http(reqwest::Error { kind: Request, message: "channel closed" })'),
            mock_plug,
        ]

        mock_client_instance.p115.side_effect = side_effects

        # Configure success responses for when it finally succeeds
        mock_plug.get_device_info.return_value = success_info
        mock_plug.get_current_power.return_value = success_power
        mock_plug.get_energy_usage.return_value = success_energy

        service = TapoP115IngestionService(config=config)

        # Mock asyncio.sleep to avoid waiting
        with patch("asyncio.sleep", AsyncMock()) as mock_sleep:
            snapshot = await service._fetch_device_snapshot("192.168.0.17")

            # Verify results
            assert snapshot is not None
            # The name in snapshot comes from metadata.get("name") if present
            assert snapshot["name"] == "Test Plug"
            assert mock_client_instance.p115.call_count == 3
            assert mock_sleep.call_count == 2
