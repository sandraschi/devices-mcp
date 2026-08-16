from unittest.mock import AsyncMock, patch

import pytest
from backend.server import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Mock the VbotClient inside robots.py to prevent real network calls
    with patch("backend.routes.robots._vbot_client") as mock_vbot:
        # Setup mock return values
        mock_vbot.create_vbot = AsyncMock(return_value={"success": True, "robot_id": "scout_01"})
        mock_vbot.list_vbots = AsyncMock(
            return_value={
                "success": True,
                "vbots": [{"id": "scout_01", "type": "scout"}],
            }
        )
        mock_vbot.move_vbot = AsyncMock(return_value={"success": True})

        with TestClient(create_app()) as test_client:
            yield test_client


def test_get_robots(client):
    response = client.get("/api/robots")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "robots" in data


def test_create_virtual_robot(client):
    payload = {"robot_type": "scout", "platform": "unity"}
    response = client.post("/api/robots/active/virtual", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["robot_id"] == "scout_01"


def test_control_robot(client):
    # Test valid command
    response = client.post(
        "/api/robots/scout_01/command",
        json={"command": "move", "params": {"linear": 0.5, "angular": 0.0}},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True

    # Test invalid command
    response = client.post("/api/robots/scout_01/command", json={"command": "invalid_cmd"})
    assert response.status_code == 400
    assert response.json()["success"] is False


def test_get_capabilities(client):
    response = client.get("/api/robots/types/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "scout" in data["capabilities"]
    assert "go2" in data["capabilities"]
