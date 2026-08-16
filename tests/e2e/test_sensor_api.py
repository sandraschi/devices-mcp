from datetime import datetime, timedelta

import pytest
from backend.server import WebServer
from fastapi.testclient import TestClient

from devices_mcp.tools.energy.tapo_plug_tools import (
    EnergyUsageData,
    TapoSmartPlug,
    tapo_plug_manager,
)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Provide a TestClient with sensor endpoints patched to deterministic data."""
    server = WebServer()
    app = server.app

    sample_device = TapoSmartPlug(
        device_id="tapo_p115_fixture",
        name="Fixture Plug",
        location="Lab",
        power_state=True,
        current_power=42.0,
        voltage=120.0,
        current=0.35,
        daily_energy=0.8,
        monthly_energy=24.0,
        daily_cost=0.10,
        monthly_cost=3.00,
        last_seen=datetime.utcnow().isoformat() + "Z",
        automation_enabled=False,
        energy_monitoring=True,
        power_schedule="08:00-22:00",
        energy_saving_mode=False,
    )

    sample_history = [
        EnergyUsageData(
            timestamp=(datetime.utcnow() - timedelta(hours=1)).isoformat(),
            device_id="tapo_p115_fixture",
            power_consumption=40.0,
            energy_consumption=0.04,
            cost=0.0048,
        )
    ]

    async def fake_get_all_devices():
        return [sample_device]

    async def fake_get_device_status(device_id: str):
        return sample_device if device_id == "tapo_p115_fixture" else None

    async def fake_get_energy_usage_history(device_id: str, hours: int = 24):
        if device_id != "tapo_p115_fixture":
            return []
        return sample_history

    monkeypatch.setattr(tapo_plug_manager, "get_all_devices", fake_get_all_devices)
    monkeypatch.setattr(tapo_plug_manager, "get_device_status", fake_get_device_status)
    monkeypatch.setattr(tapo_plug_manager, "get_energy_usage_history", fake_get_energy_usage_history)
    tapo_plug_manager.get_device_host = lambda device_id: "192.168.1.120"

    return TestClient(app)


def test_list_tapo_p115_devices(client: TestClient) -> None:
    response = client.get("/api/sensors/tapo-p115")
    assert response.status_code == 200
    payload = response.json()

    assert payload["count"] == 1
    device = payload["devices"][0]
    assert device["device_id"] == "tapo_p115_fixture"
    assert device["current_power"] == 42.0
    assert device["host"] == "192.168.1.120"


def test_get_tapo_p115_history(client: TestClient) -> None:
    response = client.get("/api/sensors/tapo-p115/tapo_p115_fixture/history?hours=4")
    assert response.status_code == 200
    payload = response.json()

    assert payload["device_id"] == "tapo_p115_fixture"
    assert payload["count"] == 1
    datapoint = payload["data_points"][0]
    assert datapoint["power_consumption"] == 40.0
    assert datapoint["energy_consumption"] == 0.04
