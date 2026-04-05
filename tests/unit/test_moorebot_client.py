"""
Unit tests for Moorebot Scout client

**Timestamp**: 2025-12-02
**Status**: Mock-based tests, ready for hardware testing when robot arrives
"""

import pytest

from devices_mcp.integrations.moorebot_client import (
    MoorebotScoutClient,
    MoorebotSensorData,
    MoorebotStatus,
)
from devices_mcp.utils.mock_moorebot import (
    MOCK_DOCK_FAILURE,
    MOCK_DOCK_SUCCESS,
    MOCK_MOVE_SUCCESS,
    MOCK_PATROL_SUCCESS,
    MOCK_SENSOR_DATA,
    MOCK_STATUS_CHARGING,
    MOCK_STATUS_IDLE,
    MOCK_STATUS_MOVING,
    MockMoorebotScout,
)


@pytest.fixture
def moorebot_client():
    """Create mock Moorebot Scout client"""
    return MoorebotScoutClient("192.168.1.100", mock_mode=True)


@pytest.fixture
def mock_scout():
    """Create mock Scout instance"""
    return MockMoorebotScout()


class TestMoorebotScoutClient:
    """Test Moorebot Scout client functionality"""

    @pytest.mark.asyncio
    async def test_connect_mock_mode(self, moorebot_client):
        """Test connection in mock mode"""
        result = await moorebot_client.connect()

        assert result["success"] is True
        assert result["mock_mode"] is True
        assert result["ip_address"] == "192.168.1.100"
        assert moorebot_client._connected is True
        assert moorebot_client._status == MoorebotStatus.IDLE

    @pytest.mark.asyncio
    async def test_get_status_idle(self, moorebot_client):
        """Test getting status when robot is idle"""
        await moorebot_client.connect()
        status = await moorebot_client.get_status()

        assert status["success"] is True
        assert status["status"] == MoorebotStatus.IDLE.value
        assert "battery_level" in status
        assert "position" in status
        assert status["mock_mode"] is True

    @pytest.mark.asyncio
    async def test_get_status_not_connected(self, moorebot_client):
        """Test getting status when not connected"""
        status = await moorebot_client.get_status()

        assert status["success"] is False
        assert "error" in status

    @pytest.mark.asyncio
    async def test_get_sensor_data(self, moorebot_client):
        """Test getting sensor data"""
        await moorebot_client.connect()
        sensors = await moorebot_client.get_sensor_data()

        assert isinstance(sensors, MoorebotSensorData)
        assert 0.0 <= sensors.tof_distance <= 3.0
        assert sensors.light_ch0 > 0
        assert sensors.light_ch1 > 0
        assert len(sensors.imu_orientation) == 4
        assert len(sensors.imu_angular_velocity) == 3
        assert len(sensors.imu_linear_acceleration) == 3

    @pytest.mark.asyncio
    async def test_move_forward(self, moorebot_client):
        """Test moving robot forward"""
        await moorebot_client.connect()
        result = await moorebot_client.move(linear=0.3, angular=0.0)

        assert result["success"] is True
        assert result["linear"] == 0.3
        assert result["angular"] == 0.0
        assert moorebot_client._status == MoorebotStatus.MOVING

    @pytest.mark.asyncio
    async def test_move_rotate(self, moorebot_client):
        """Test rotating robot in place"""
        await moorebot_client.connect()
        result = await moorebot_client.move(linear=0.0, angular=1.0)

        assert result["success"] is True
        assert result["linear"] == 0.0
        assert result["angular"] == 1.0

    @pytest.mark.asyncio
    async def test_stop(self, moorebot_client):
        """Test emergency stop"""
        await moorebot_client.connect()
        await moorebot_client.move(linear=0.3, angular=0.0)
        result = await moorebot_client.stop()

        assert result["success"] is True
        assert result["linear"] == 0.0
        assert result["angular"] == 0.0

    @pytest.mark.asyncio
    async def test_start_patrol(self, moorebot_client):
        """Test starting patrol route"""
        await moorebot_client.connect()
        result = await moorebot_client.start_patrol("default")

        assert result["success"] is True
        assert result["route"] == "default"
        assert result["waypoints"] > 0
        assert moorebot_client._status == MoorebotStatus.PATROLLING

    @pytest.mark.asyncio
    async def test_stop_patrol(self, moorebot_client):
        """Test stopping patrol"""
        await moorebot_client.connect()
        await moorebot_client.start_patrol("default")
        result = await moorebot_client.stop_patrol()

        assert result["success"] is True
        assert moorebot_client._status == MoorebotStatus.IDLE

    @pytest.mark.asyncio
    async def test_return_to_dock_success(self, moorebot_client):
        """Test successful docking"""
        await moorebot_client.connect()
        result = await moorebot_client.return_to_dock()

        assert "success" in result
        # Docking can fail realistically, so check for both cases
        if result["success"]:
            assert result["docking_status"] == "success"
        else:
            assert "error" in result
            assert "suggestion" in result

    @pytest.mark.asyncio
    async def test_get_camera_snapshot(self, moorebot_client):
        """Test getting camera snapshot"""
        await moorebot_client.connect()
        snapshot = await moorebot_client.get_camera_snapshot()

        assert isinstance(snapshot, bytes)
        assert len(snapshot) > 0

    @pytest.mark.asyncio
    async def test_get_video_stream_url(self, moorebot_client):
        """Test getting video stream URL"""
        url = await moorebot_client.get_video_stream_url()

        assert url.startswith("rtsp://")
        assert "192.168.1.100" in url
        assert ":8554" in url

    @pytest.mark.asyncio
    async def test_disconnect(self, moorebot_client):
        """Test disconnecting from robot"""
        await moorebot_client.connect()
        await moorebot_client.disconnect()

        assert moorebot_client._connected is False
        assert moorebot_client._status == MoorebotStatus.OFFLINE


class TestMockMoorebotScout:
    """Test mock Scout behaviors"""

    def test_mock_status_generation(self, mock_scout):
        """Test mock status data generation"""
        status = mock_scout.get_mock_status()

        assert status["success"] is True
        assert status["status"] in ["idle", "moving", "patrolling", "charging"]
        assert 0 <= status["battery_level"] <= 100
        assert "position" in status
        assert status["mock_mode"] is True

    def test_mock_sensor_generation(self, mock_scout):
        """Test mock sensor data generation"""
        sensors = mock_scout.get_mock_sensors()

        assert 0.0 <= sensors["tof_distance"] <= 3.0
        assert sensors["light_ch0"] > 0
        assert sensors["light_ch1"] > 0
        assert "imu" in sensors
        assert sensors["mock_mode"] is True

    def test_simulate_movement(self, mock_scout):
        """Test movement simulation"""
        initial_x = mock_scout.x
        mock_scout.simulate_movement(0.3, 0.0, 5.0)

        assert mock_scout.x > initial_x
        assert mock_scout.status == "moving"

    def test_simulate_patrol(self, mock_scout):
        """Test patrol simulation"""
        result = mock_scout.simulate_patrol("default")

        assert result["success"] is True
        assert result["waypoints"] > 0
        assert result["estimated_duration"] > 0

    def test_simulate_docking_realistic(self, mock_scout):
        """Test realistic docking (sometimes fails)"""
        # Run multiple docking attempts to test randomness
        attempts = 10
        successes = 0
        failures = 0

        for _ in range(attempts):
            result = mock_scout.simulate_docking()
            if result["success"]:
                successes += 1
            else:
                failures += 1

        # Should have both successes and failures (realistic behavior)
        assert successes > 0
        assert failures > 0  # Known docking issue!

    def test_room_detection(self, mock_scout):
        """Test room detection based on position"""
        # Living room
        mock_scout.x = 2.0
        mock_scout.y = 2.0
        assert mock_scout._get_current_room() == "living_room"

        # Bedroom
        mock_scout.x = 6.0
        mock_scout.y = 1.5
        assert mock_scout._get_current_room() == "bedroom"

        # Kitchen
        mock_scout.x = 1.0
        mock_scout.y = 5.0
        assert mock_scout._get_current_room() == "kitchen"


class TestMockFixtures:
    """Test pre-defined mock fixtures"""

    def test_mock_status_fixtures(self):
        """Test status fixture data"""
        assert MOCK_STATUS_IDLE["status"] == "idle"
        assert MOCK_STATUS_MOVING["status"] == "moving"
        assert MOCK_STATUS_CHARGING["status"] == "charging"
        assert MOCK_STATUS_CHARGING["charging"] is True

    def test_mock_sensor_fixture(self):
        """Test sensor fixture data"""
        assert "tof_distance" in MOCK_SENSOR_DATA
        assert "imu" in MOCK_SENSOR_DATA
        assert "light_ch0" in MOCK_SENSOR_DATA

    def test_mock_move_fixture(self):
        """Test move fixture data"""
        assert MOCK_MOVE_SUCCESS["success"] is True
        assert "linear" in MOCK_MOVE_SUCCESS
        assert "angular" in MOCK_MOVE_SUCCESS

    def test_mock_patrol_fixture(self):
        """Test patrol fixture data"""
        assert MOCK_PATROL_SUCCESS["success"] is True
        assert MOCK_PATROL_SUCCESS["waypoints"] > 0

    def test_mock_dock_fixtures(self):
        """Test docking fixture data"""
        assert MOCK_DOCK_SUCCESS["success"] is True
        assert MOCK_DOCK_FAILURE["success"] is False
        assert "suggestion" in MOCK_DOCK_FAILURE


# Integration tests placeholder (require hardware)
@pytest.mark.skip(reason="Requires physical hardware - XMas 2025")
class TestMoorebotHardware:
    """Hardware integration tests (run when robot arrives)"""

    @pytest.mark.asyncio
    async def test_real_connection(self):
        """Test real robot connection"""
        client = MoorebotScoutClient("192.168.1.100", mock_mode=False)
        result = await client.connect()
        assert result["success"] is True
        await client.disconnect()

    @pytest.mark.asyncio
    async def test_real_movement(self):
        """Test real robot movement"""
        client = MoorebotScoutClient("192.168.1.100", mock_mode=False)
        await client.connect()
        result = await client.move(0.1, 0.0, 1.0)
        assert result["success"] is True
        await client.disconnect()
