"""Tests for Ring client refresh and token helpers."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from devices_mcp.integrations.ring_client import RingClient, ring_has_cached_token


def test_ring_has_cached_token_false_when_missing(tmp_path: Path):
    assert ring_has_cached_token(str(tmp_path / "missing.cache")) is False


def test_ring_has_cached_token_true(tmp_path: Path):
    p = tmp_path / "ring_token.cache"
    p.write_text(json.dumps({"access_token": "x"}), encoding="utf-8")
    assert ring_has_cached_token(str(p)) is True


@pytest.mark.asyncio
async def test_update_data_calls_ring_update_in_thread():
    client = RingClient(email="a@b.com", password="secret", token_file="x.cache")
    client._initialized = True
    client._ring = MagicMock()
    client._ring.devices_data = {"doorbots": {}}

    with patch.object(client, "_fetch_alarm_data", new_callable=AsyncMock) as mock_alarm:
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            await client._update_data(force=True)

    mock_thread.assert_awaited_once()
    mock_alarm.assert_awaited_once()
    assert "doorbells" not in client._cache
