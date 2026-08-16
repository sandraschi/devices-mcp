from unittest.mock import AsyncMock, patch

import pytest

from devices_mcp.integrations.vbot_client import VbotClient


@pytest.fixture
def mock_session():
    with patch("aiohttp.ClientSession") as mock:
        session = AsyncMock()
        mock.return_value = session
        yield session


@pytest.fixture
def client(mock_session):
    return VbotClient("http://test-server:8001")


@pytest.mark.asyncio
async def test_connect_success(client, mock_session):
    # Mock the response for the connection test tool call
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"result": {"success": True, "status": "ok"}}
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.connect()

    assert result["success"] is True
    assert client.session is not None
    # Verify we called the robotics_system status tool
    mock_session.post.assert_called_with(
        "http://test-server:8001/api/v1/tools/robotics_system",
        json={"operation": "status"},
    )


@pytest.mark.asyncio
async def test_create_vbot(client, mock_session):
    client.session = mock_session

    # Mock response
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"result": {"success": True, "robot_id": "scout_01"}}
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.create_vbot(robot_type="scout", position={"x": 1.0, "y": 0.0, "z": 0.0}, platform="unity")

    assert result["success"] is True
    assert result["robot_id"] == "scout_01"

    # Verify tool call args
    mock_session.post.assert_called_with(
        "http://test-server:8001/api/v1/tools/robot_virtual",
        json={
            "operation": "create",
            "robot_type": "scout",
            "platform": "unity",
            "position": {"x": 1.0, "y": 0.0, "z": 0.0},
        },
    )


@pytest.mark.asyncio
async def test_move_vbot(client, mock_session):
    client.session = mock_session

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json.return_value = {"result": {"success": True}}
    mock_session.post.return_value.__aenter__.return_value = mock_response

    await client.move_vbot("scout_01", linear=0.5, angular=0.1)

    # Check that robot_behavior tool was called with correct wheel speeds
    args = mock_session.post.call_args[1]["json"]
    assert args["robot_id"] == "scout_01"
    assert args["action"] == "animate_movement"
    # Linear + Angular calculation check
    assert args["wheel_speeds"]["front_left"] == 0.6  # 0.5 + 0.1
    assert args["wheel_speeds"]["front_right"] == 0.4  # 0.5 - 0.1


@pytest.mark.asyncio
async def test_error_handling(client, mock_session):
    client.session = mock_session

    # Mock error response
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text.return_value = "Internal Server Error"
    mock_session.post.return_value.__aenter__.return_value = mock_response

    result = await client.get_vbot_status("scout_01")

    assert result["success"] is False
    assert "HTTP 500" in result["error"]
