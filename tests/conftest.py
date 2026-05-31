"""
Comprehensive test configuration for pytest.
This file provides extensive fixtures and mocks for testing the Devices MCP platform.

Features:
- Comprehensive fixtures for all components
- Mock implementations for external services
- Test data factories
- Async testing support
- Performance testing utilities
- Integration testing helpers
"""

import asyncio
import sys
import tempfile
import time
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Also add src directory for MCP imports and web-sota directory for web dashboard imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "web-sota"))

from devices_mcp import TapoCameraMCP
from devices_mcp.core.models import TapoCameraConfig
from devices_mcp.mcp_client import MCPClient, MCPClientManager

# Test configuration constants
TEST_CONFIG = {
    "host": "192.168.1.100",
    "port": 443,
    "username": "testuser",
    "password": "testpass",
    "use_https": True,
    "verify_ssl": False,
    "timeout": 5,
}

TEST_DEVICE_ID = "test-device-123"
TEST_CAMERA_ID = "test-camera-456"
TEST_PLUG_ID = "test-plug-789"


# ============================================================================
# CORE FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def config() -> TapoCameraConfig:
    """Return a test configuration."""
    return TapoCameraConfig(**TEST_CONFIG)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_data():
    """Return sample configuration data."""
    return {
        "tapo": {
            "cameras": [
                {
                    "name": "Kitchen Camera",
                    "host": "192.168.0.164",
                    "username": "sandraschi",
                    "password": "testpass",
                },
                {
                    "name": "Living Room Camera",
                    "host": "192.168.0.206",
                    "username": "sandraschi",
                    "password": "testpass",
                },
            ]
        },
        "energy": {
            "tapo_p115": {
                "account": {"email": "test@example.com", "password": "testpass"},
                "devices": [{"device_id": TEST_PLUG_ID, "name": "Test Plug", "host": "192.168.1.101"}],
            }
        },
    }


# ============================================================================
# MOCKING FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def mock_session():
    """Return a mock aiohttp client session."""
    with patch("aiohttp.ClientSession") as mock_session_class:
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session

        # Mock response for connection test
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"result": {"device_id": TEST_DEVICE_ID}}

        mock_session.request.return_value.__aenter__.return_value = mock_response

        yield mock_session


@pytest.fixture
def mock_mcp_client():
    """Return a mock MCP client."""
    mock_client = AsyncMock(spec=MCPClient)
    mock_client.call_tool.return_value = {"success": True, "data": {}}
    mock_client.list_tools.return_value = []
    mock_client.initialize.return_value = {}
    return mock_client


@pytest.fixture
def mock_mcp_client_manager(mock_mcp_client):
    """Return a mock MCP client manager."""
    with patch("devices_mcp.mcp_client.mcp_clients", MCPClientManager()) as manager:
        manager.add_client("test", mock_mcp_client, set_default=True)
        manager.get_client.return_value = mock_mcp_client
        yield manager


@pytest.fixture
def mock_tapo_plug_manager():
    """Return a mock Tapo plug manager."""
    with patch("devices_mcp.tools.energy.tapo_plug_tools.tapo_plug_manager") as mock_manager:
        mock_manager.get_all_devices.return_value = []
        mock_manager.get_device_status.return_value = Mock()
        mock_manager.toggle_device.return_value = True
        mock_manager.is_device_readonly.return_value = False
        yield mock_manager


@pytest.fixture
def mock_energy_management_tool():
    """Return a mock energy management tool."""
    with patch("devices_mcp.tools.energy.energy_management_tool.EnergyManagementTool") as mock_tool:
        mock_tool.return_value.execute.return_value = {"success": True, "data": {}}
        yield mock_tool


@pytest.fixture
def mock_motion_management_tool():
    """Return a mock motion management tool."""
    with patch("devices_mcp.tools.portmanteau.motion_management") as mock_tool:
        mock_tool.return_value = {"success": True, "data": {}}
        yield mock_tool


@pytest.fixture
def mock_camera_management_tool():
    """Return a mock camera management tool."""
    with patch("devices_mcp.tools.portmanteau.camera_management") as mock_tool:
        mock_tool.return_value = {"success": True, "data": {}}
        yield mock_tool


@pytest.fixture
def mock_media_management_tool():
    """Return a mock media management tool."""
    with patch("devices_mcp.tools.portmanteau.media_management") as mock_tool:
        mock_tool.return_value = {"success": True, "data": {}}
        yield mock_tool


@pytest.fixture
def mock_system_management_tool():
    """Return a mock system management tool."""
    with patch("devices_mcp.tools.portmanteau.system_management") as mock_tool:
        mock_tool.return_value = {"success": True, "data": {}}
        yield mock_tool


# ============================================================================
# COMPONENT FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def tapo_camera(config, mock_session) -> AsyncGenerator[TapoCameraMCP, None]:
    """Return a TapoCameraMCP instance with a mock session."""
    camera = TapoCameraMCP(config=config.dict())

    # Connect the camera
    await camera.connect()

    yield camera

    # Clean up
    if camera._is_connected:
        await camera.disconnect()


@pytest.fixture
def test_client():
    """Return a FastAPI test client."""
    from backend.server import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Return authorization headers for authenticated requests."""
    return {"Authorization": "Bearer test-token"}


# ============================================================================
# DATA FIXTURES
# ============================================================================


@pytest.fixture
def test_image() -> bytes:
    """Return a test image in bytes."""
    # This is a minimal PNG file (1x1 transparent pixel)
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\xdac\x00\x01\x00\x00\x05\x00\x01\x0f\xa5\xea\xfd\x00\x00\x00\x00IEND\xaeB`\x82"
    )


@pytest.fixture
def test_video_data() -> bytes:
    """Return test video data."""
    # Mock video data
    return b"mock_video_data_mp4_format"


@pytest.fixture
def sample_motion_event():
    """Return a sample motion detection event."""
    return {
        "event_id": "motion-123",
        "camera_id": TEST_CAMERA_ID,
        "timestamp": "2023-01-01T12:00:00Z",
        "event_type": "motion_detected",
        "confidence": 0.95,
        "regions": [[100, 100, 200, 200]],
        "metadata": {"brightness": 0.7, "motion_strength": 0.8},
    }


@pytest.fixture
def sample_energy_data():
    """Return sample energy consumption data."""
    return {
        "device_id": TEST_PLUG_ID,
        "timestamp": "2023-01-01T12:00:00Z",
        "current_power": 45.2,
        "voltage": 230.1,
        "current": 0.196,
        "daily_energy": 2.34,
        "monthly_energy": 68.9,
    }


@pytest.fixture
def sample_weather_data():
    """Return sample weather station data."""
    return {
        "station_id": "weather-123",
        "timestamp": "2023-01-01T12:00:00Z",
        "temperature": 22.5,
        "humidity": 65.0,
        "pressure": 1013.25,
        "wind_speed": 12.5,
        "wind_direction": 180,
        "rainfall": 0.0,
        "uv_index": 6.0,
    }


@pytest.fixture
def sample_system_status():
    """Return sample system status data."""
    return {
        "uptime": 3600,
        "cpu_usage": 45.2,
        "memory_usage": 67.8,
        "disk_usage": 23.1,
        "network_rx": 1024000,
        "network_tx": 512000,
        "active_connections": 5,
        "error_count": 0,
    }


# Test utilities
def assert_dict_contains(d: dict[Any, Any], sub_d: dict[Any, Any]) -> None:
    """Assert that dictionary d contains all key-value pairs from sub_d."""
    for key, value in sub_d.items():
        assert key in d, f"Key '{key}' not found in dictionary"
        assert d[key] == value, f"Value for key '{key}' does not match. Expected {value}, got {d[key]}"


# Mock classes for testing
class AsyncContextManagerMock:
    """A mock class for async context managers."""

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# Mock classes for external dependencies
class MockResponse:
    """A mock response class for testing HTTP requests."""

    def __init__(self, status: int, json_data: dict[str, Any] | None = None, text: str | None = None):
        self.status = status
        self._json_data = json_data or {}
        self._text = text or ""

    async def json(self) -> dict[str, Any]:
        """Return the JSON response data."""
        return self._json_data

    async def text(self) -> str:
        """Return the response text."""
        return self._text

    async def read(self) -> bytes:
        """Return the response content as bytes."""
        return self._text.encode() if self._text else b""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


# ============================================================================
# ADDITIONAL FIXTURES
# ============================================================================


@pytest.fixture
def mock_websocket():
    """Return a mock WebSocket for testing real-time connections."""
    return MockWebSocket()


@pytest.fixture
def mock_database():
    """Return a mock database for testing data persistence."""
    return MockDatabase()


# ============================================================================
# HARDWARE TESTING FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def hardware_initializer():
    """Return a HardwareInitializer instance for testing."""
    from devices_mcp.camera.manager import CameraManager
    from devices_mcp.core.hardware_init import HardwareInitializer

    camera_manager = CameraManager()
    initializer = HardwareInitializer(camera_manager=camera_manager)

    yield initializer

    cleanup = getattr(camera_manager, "cleanup", None)
    if cleanup:
        await cleanup()


@pytest.fixture
def mock_hardware_responses():
    """Mock responses for hardware connectivity testing."""
    return {
        "cameras": {"success": True, "count": 2, "cameras": ["cam1", "cam2"]},
        "hue_bridge": {"success": True, "lights_count": 5, "groups_count": 2, "scenes_count": 10},
        "tapo_lighting": {"success": True, "devices_count": 1},
        "tapo_plugs": {"success": True, "devices_count": 3},
        "netatmo": {"success": True, "stations_count": 1, "modules_count": 3},
        "ring": {"success": True, "doorbells_count": 1, "cameras_count": 1},
        "home_assistant": {"success": True, "devices_count": 0},
    }


@pytest.fixture
def mock_config_file(temp_dir, sample_config_data):
    """Create a mock configuration file."""
    config_path = temp_dir / "config.yaml"
    import yaml

    with open(config_path, "w") as f:
        yaml.dump(sample_config_data, f)
    return config_path


# ============================================================================
# PATCH DECORATORS FOR COMMON MOCKS
# ============================================================================


def patch_aiohttp_client():
    """Patch aiohttp client to return mock responses."""
    return patch("aiohttp.ClientSession")


def patch_os_path_exists(exists: bool = True):
    """Patch os.path.exists to return the specified value."""
    return patch("os.path.exists", return_value=exists)


def patch_open():
    """Patch the built-in open function."""
    return patch("builtins.open", new_callable=MagicMock)


def patch_json_load(return_value: Any = None):
    """Patch json.load to return the specified value."""
    return patch("json.load", return_value=return_value)


def patch_json_dump():
    """Patch json.dump to do nothing."""
    return patch("json.dump")


def patch_mcp_call_tool(return_value: dict[str, Any] | None = None):
    """Patch the MCP call_mcp_tool function."""
    return patch(
        "devices_mcp.mcp_client.call_mcp_tool",
        return_value=return_value or {"success": True, "data": {}},
    )


def patch_tapo_plug_manager():
    """Patch the Tapo plug manager."""
    return patch("devices_mcp.tools.energy.tapo_plug_tools.tapo_plug_manager")


def patch_energy_management():
    """Patch the energy management tool."""
    return patch("devices_mcp.tools.portmanteau.energy_management")


def patch_motion_management():
    """Patch the motion management tool."""
    return patch("devices_mcp.tools.portmanteau.motion_management")


def patch_camera_management():
    """Patch the camera management tool."""
    return patch("devices_mcp.tools.portmanteau.camera_management")


def patch_media_management():
    """Patch the media management tool."""
    return patch("devices_mcp.tools.portmanteau.media_management")


def patch_system_management():
    """Patch the system management tool."""
    return patch("devices_mcp.tools.portmanteau.system_management")


def patch_medical_management():
    """Patch the medical management tool."""
    return patch("devices_mcp.tools.portmanteau.medical_management")


# ============================================================================
# EXTENDED TEST DATA
# ============================================================================

# Original test constants for backward compatibility
TEST_DEVICE_INFO = {
    "model": "Tapo C200",
    "fw_ver": "1.0.0",
    "hw_ver": "1.0",
    "type": "SMART.TAPOPLUG",
    "mac": "00-11-22-33-44-55",
    "device_id": "test-device-123",
    "hw_id": "test-hw-id",
    "fw_id": "test-fw-id",
    "oem_id": "test-oem-id",
    "color": "#000000",
    "alias": "Tapo Camera",
    "dev_name": "Tapo Camera C200",
    "icon": "",
    "latitude": 0,
    "longitude": 0,
    "has_set_location_info": False,
    "ip": "192.168.1.100",
    "ssid": "MyWiFi",
    "signal_level": 4,
    "rssi": -50,
    "on_time": 3600,
    "specs": "",
    "lang": "en_US",
    "region": "US",
    "device_on": True,
    "overheated": False,
    "nickname": "My Tapo Camera",
    "location": "Living Room",
}

TEST_CAMERA_STATUS = {
    "device_id": "test-device-123",
    "is_on": True,
    "is_online": True,
    "is_streaming": False,
    "is_recording": False,
    "motion_detection_enabled": True,
    "motion_detected": False,
    "sound_detection_enabled": False,
    "sound_detected": False,
    "privacy_mode": False,
    "led_enabled": True,
    "battery_level": 100,
    "signal_level": 4,
    "rssi": -50,
    "uptime": 3600,
    "last_motion": None,
    "last_sound": None,
    "last_alarm": None,
    "storage": {
        "total_bytes": 10737418240,  # 10 GB
        "used_bytes": 1073741824,  # 1 GB
        "free_bytes": 9663676416,  # 9 GB
        "usage_percent": 10.0,
    },
    "firmware_version": "1.0.0",
    "hardware_version": "1.0",
    "model": "Tapo C200",
    "serial_number": "00-11-22-33-44-55",
    "ip_address": "192.168.1.100",
    "mac_address": "00:11:22:33:44:55",
    "ssid": "MyWiFi",
    "location": "Living Room",
    "timezone": "America/New_York",
    "night_vision_enabled": False,
    "privacy_mode_enabled": False,
    "audio_enabled": True,
    "resolution": "1920x1080",
    "fps": 30,
    "bitrate": 2000,
    "current_zoom": 1.0,
    "current_pan": 0.0,
    "current_tilt": 0.0,
}

EXTENDED_DEVICE_INFO = {
    **TEST_DEVICE_INFO,
    "supported_features": ["motion_detection", "night_vision", "two_way_audio"],
    "firmware_features": ["privacy_mode", "led_control", "auto_tracking"],
    "network_info": {
        "mac_address": "00:11:22:33:44:55",
        "ip_address": "192.168.1.100",
        "subnet_mask": "255.255.255.0",
        "gateway": "192.168.1.1",
        "dns_servers": ["8.8.8.8", "8.8.4.4"],
    },
    "storage_info": {
        "total_space": 32000000000,  # 32GB
        "used_space": 8000000000,  # 8GB
        "free_space": 24000000000,  # 24GB
        "recording_days": 30,
    },
}

EXTENDED_CAMERA_STATUS = {
    **TEST_CAMERA_STATUS,
    "motion_zones": [
        {"id": 1, "name": "Front Door", "enabled": True, "sensitivity": 5},
        {"id": 2, "name": "Driveway", "enabled": True, "sensitivity": 7},
    ],
    "privacy_zones": [{"id": 1, "name": "Neighbor Window", "enabled": True}],
    "scheduled_recordings": [
        {
            "id": 1,
            "name": "Morning Routine",
            "start_time": "07:00",
            "end_time": "09:00",
            "days": ["mon", "tue", "wed", "thu", "fri"],
        }
    ],
}

TEST_STREAM_INFO = {
    "stream_id": "test-stream-123",
    "stream_type": "rtsp",
    "stream_url": "rtsp://192.168.1.100:554/stream1",
    "width": 1920,
    "height": 1080,
    "fps": 30,
    "bitrate": 2048,
    "codec": "H.264",
    "audio_enabled": True,
    "audio_codec": "AAC",
    "audio_bitrate": 128,
    "audio_channels": 2,
    "audio_sample_rate": 44100,
    "status": "active",
    "clients": 1,
    "started_at": "2023-01-01T12:00:00Z",
    "uptime": 60,
    "bytes_sent": 15360000,
    "bytes_received": 0,
    "bitrate_current": 2048,
    "bitrate_max": 4096,
    "bitrate_min": 512,
    "fps_current": 30,
    "fps_max": 30,
    "fps_min": 15,
    "resolution": "1920x1080",
    "quality": "high",
}

TEST_RECORDING_INFO = {
    "recording_id": "test-recording-123",
    "camera_id": "test-device-123",
    "start_time": "2023-01-01T12:00:00Z",
    "end_time": "2023-01-01T12:01:00Z",
    "duration": 60,
    "size_bytes": 15360000,
    "file_path": "/recordings/test-recording-123.mp4",
    "file_format": "mp4",
    "video_codec": "H.264",
    "audio_codec": "AAC",
    "resolution": "1920x1080",
    "fps": 30,
    "bitrate": 2048,
    "audio_bitrate": 128,
    "channels": 2,
    "sample_rate": 44100,
    "status": "completed",
    "motion_detected": True,
    "motion_regions": [[0, 0, 100, 100]],
    "motion_scores": [0.95],
    "motion_timestamps": ["2023-01-01T12:00:30Z"],
    "tags": ["motion"],
    "metadata": {},
}

# ============================================================================
# ADVANCED MOCK CLASSES
# ============================================================================


class MockWebSocket:
    """Mock WebSocket for testing real-time connections."""

    def __init__(self):
        self.sent_messages = []
        self.received_messages = []
        self.closed = False

    async def send_json(self, data: dict[str, Any]):
        """Send JSON data through the WebSocket."""
        self.sent_messages.append(data)

    async def receive_json(self):
        """Receive JSON data from the WebSocket."""
        if self.received_messages:
            return self.received_messages.pop(0)
        # Simulate waiting for a message
        await asyncio.sleep(0.01)
        return {"type": "ping"}

    async def close(self):
        """Close the WebSocket connection."""
        self.closed = True


class MockDatabase:
    """Mock database for testing data persistence."""

    def __init__(self):
        self.data = {}
        self.queries = []

    def insert(self, table: str, data: dict[str, Any]) -> int:
        """Insert data into a table."""
        if table not in self.data:
            self.data[table] = []
        record_id = len(self.data[table]) + 1
        data["id"] = record_id
        self.data[table].append(data)
        self.queries.append(f"INSERT INTO {table}: {data}")
        return record_id

    def select(self, table: str, where: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Select data from a table."""
        if table not in self.data:
            return []

        records = self.data[table]
        if where:
            filtered_records = []
            for record in records:
                if all(record.get(k) == v for k, v in where.items()):
                    filtered_records.append(record)
            records = filtered_records

        self.queries.append(f"SELECT FROM {table} WHERE {where}")
        return records

    def update(self, table: str, where: dict[str, Any], data: dict[str, Any]) -> int:
        """Update records in a table."""
        if table not in self.data:
            return 0

        updated_count = 0
        for record in self.data[table]:
            if all(record.get(k) == v for k, v in where.items()):
                record.update(data)
                updated_count += 1

        self.queries.append(f"UPDATE {table} WHERE {where}: {data}")
        return updated_count

    def delete(self, table: str, where: dict[str, Any]) -> int:
        """Delete records from a table."""
        if table not in self.data:
            return 0

        original_length = len(self.data[table])
        self.data[table] = [
            record for record in self.data[table] if not all(record.get(k) == v for k, v in where.items())
        ]
        deleted_count = original_length - len(self.data[table])

        self.queries.append(f"DELETE FROM {table} WHERE {where}")
        return deleted_count


# ============================================================================
# TEST UTILITIES
# ============================================================================


def assert_dict_contains_keys(d: dict[Any, Any], keys: list[str]) -> None:
    """Assert that dictionary d contains all specified keys."""
    for key in keys:
        assert key in d, f"Key '{key}' not found in dictionary"


def assert_api_response_success(response: dict[str, Any]) -> None:
    """Assert that an API response indicates success."""
    assert "success" in response, "Response missing 'success' field"
    assert response["success"] is True, f"API call failed: {response}"


def assert_api_response_error(response: dict[str, Any], expected_status: int | None = None) -> None:
    """Assert that an API response indicates an error."""
    assert "success" in response, "Response missing 'success' field"
    assert response["success"] is False, "Expected error response but got success"

    if expected_status:
        assert "status_code" in response, "Error response missing status_code"
        assert response["status_code"] == expected_status, (
            f"Expected status {expected_status}, got {response['status_code']}"
        )


def create_mock_http_exception(status_code: int, detail: str) -> HTTPException:
    """Create a mock HTTPException for testing."""
    return HTTPException(status_code=status_code, detail=detail)


def create_mock_pydantic_model(**kwargs) -> BaseModel:
    """Create a mock Pydantic model for testing."""

    class MockModel(BaseModel):
        pass

    # Dynamically add fields
    for key, value in kwargs.items():
        setattr(MockModel, key, value)

    return MockModel(**kwargs)


async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """Wait for a condition to become true."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if await condition_func():
            return True
        await asyncio.sleep(interval)
    return False


# ============================================================================
# PERFORMANCE TESTING UTILITIES
# ============================================================================


@pytest.fixture
def performance_timer():
    """Fixture for measuring performance in tests."""

    class PerformanceTimer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time is None or self.end_time is None:
                return 0
            return self.end_time - self.start_time

        def assert_under_limit(self, limit_seconds: float):
            assert self.elapsed < limit_seconds, f"Operation took {self.elapsed:.2f}s, limit was {limit_seconds}s"

    return PerformanceTimer()
