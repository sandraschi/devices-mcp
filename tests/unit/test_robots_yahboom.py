"""Tests for Yahboom robot routes via yahboom-mcp proxy."""

from datetime import datetime
from unittest.mock import patch

import pytest
from backend.routes import robots as robots_module
from backend.routes.robots import Robot, RobotStatus, RobotType, _robots
from backend.server import WebServer
from fastapi.testclient import TestClient

from devices_mcp.integrations.yahboom_client import YahboomMcpClient


@pytest.fixture
def client():
    server = WebServer()
    return TestClient(server.app)


@pytest.fixture
def yahboom_robot():
    _robots.clear()
    robot = Robot(
        id="yahboom_car",
        name="Test Yahboom",
        type=RobotType.YAHBOOM,
        status=RobotStatus.OFFLINE,
        capabilities=robots_module.get_default_capabilities(RobotType.YAHBOOM),
        position=robots_module.RobotPosition(),
        last_seen=datetime.now(),
        ip_address="192.168.1.11",
    )
    _robots[robot.id] = robot
    yield robot
    _robots.clear()


@pytest.fixture
def mock_yahboom_client():
    client = YahboomMcpClient("http://127.0.0.1:10892")

    async def fake_request(method, path, *, params=None, json_body=None):
        if path == "/api/v1/health":
            return {
                "status": "online",
                "robot_connection": {
                    "ros": "connected",
                    "cmd_vel_ready": True,
                    "ip": "192.168.1.11",
                },
            }
        if path == "/api/v1/telemetry":
            return {
                "status": "live",
                "source": "live",
                "battery": 88.0,
                "voltage": 12.1,
                "position": {"x": 1.0, "y": 2.0, "z": 0.0},
                "imu": {"heading": 90.0},
            }
        if path == "/api/v1/control/move":
            return {"status": "success", "command": params or {}}
        if path == "/api/v1/stop_all":
            return {"success": True}
        if path == "/api/v1/reconnect":
            return {"success": True, "status": "online"}
        return {"success": True}

    client._request = fake_request  # type: ignore[method-assign]
    return client


class TestYahboomRobotsAPI:
    def test_list_robots_refreshes_yahboom(self, client, yahboom_robot, mock_yahboom_client):
        with patch.object(robots_module, "_yahboom_client_for_config", return_value=mock_yahboom_client):
            response = client.get("/api/robots/")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            robot = data["robots"][0]
            assert robot["type"] == "yahboom"
            assert robot["connection"]["ros_connected"] is True
            assert robot["battery_percentage"] == 88.0

    def test_yahboom_move_command(self, client, yahboom_robot, mock_yahboom_client):
        with patch.object(robots_module, "_yahboom_client_for_config", return_value=mock_yahboom_client):
            response = client.post(
                "/api/robots/yahboom_car/command",
                json={"command": "start_patrol", "parameters": {"linear": 0.2, "angular": 0.1}},
            )
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert yahboom_robot.status == robots_module.RobotStatus.PATROLLING

    def test_yahboom_connection_endpoint(self, client, mock_yahboom_client):
        with patch.object(robots_module, "_yahboom_client_for_config", return_value=mock_yahboom_client):
            response = client.get("/api/robots/yahboom/connection")
            assert response.status_code == 200
            data = response.json()
            assert data["telemetry_live"] is True
            assert data["connection"]["robot_ip"] == "192.168.1.11"

    def test_yahboom_reconnect(self, client, mock_yahboom_client):
        with patch.object(robots_module, "_yahboom_client_for_config", return_value=mock_yahboom_client):
            response = client.post("/api/robots/yahboom/reconnect")
            assert response.status_code == 200
            assert response.json()["success"] is True
