"""Tests for Tapo P115 history API."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from backend.routes.sensors import _downsample_points, _energy_timestamp_to_iso


def test_energy_timestamp_to_iso_from_unix():
    ts = int(datetime(2026, 5, 24, 12, 0, tzinfo=UTC).timestamp())
    iso = _energy_timestamp_to_iso(ts)
    assert "2026-05-24" in iso


def test_downsample_points_keeps_last():
    points = [{"power_w": i} for i in range(1000)]
    out = _downsample_points(points, max_points=100)
    assert len(out) <= 101
    assert out[-1]["power_w"] == 999


def test_history_endpoint_returns_points():
    from backend.server import WebServer
    from fastapi.testclient import TestClient

    mock_device = MagicMock()
    mock_device.name = "Aircon"
    mock_device.current_power = 120.0
    mock_device.voltage = 230.0
    mock_device.current = 0.5

    history_rows = [
        {
            "device_id": "tapo_p115_aircon",
            "timestamp": int(datetime.now(tz=UTC).timestamp()) - 3600,
            "power_w": 100.0,
            "voltage_v": 230.0,
            "current_a": 0.4,
        },
        {
            "device_id": "tapo_p115_aircon",
            "timestamp": int(datetime.now(tz=UTC).timestamp()),
            "power_w": 120.0,
            "voltage_v": 231.0,
            "current_a": 0.5,
        },
    ]

    with patch("backend.routes.sensors.tapo_plug_manager.get_device_status", return_value=mock_device):
        with patch("backend.routes.sensors.get_sensors_db") as mock_db:
            mock_db.return_value.get_energy_history.return_value = history_rows
            client = TestClient(WebServer().app)
            r = client.get("/api/sensors/tapo-p115/tapo_p115_aircon/history?hours=24")

    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert data["data_points"][0]["power_w"] == 100.0
