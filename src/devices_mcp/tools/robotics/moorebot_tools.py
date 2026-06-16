"""
Moorebot Scout MCP Tools

Provides MCP tool interface for Moorebot Scout robot control.

**Timestamp**: 2025-12-02
**Status**: Mock mode ready, hardware support when robot arrives
"""

import logging

from devices_mcp.integrations.moorebot_client import MoorebotScoutClient

logger = logging.getLogger(__name__)

# Global client instance (initialized from config)
_moorebot_client: MoorebotScoutClient | None = None


def initialize_moorebot_client(ip_address: str, mock_mode: bool = True):
    """Initialize global Moorebot client"""
    global _moorebot_client
    _moorebot_client = MoorebotScoutClient(ip_address, mock_mode=mock_mode)


def get_moorebot_client() -> MoorebotScoutClient:
    """Get Moorebot client instance"""
    if _moorebot_client is None:
        raise RuntimeError("Moorebot client not initialized")
    return _moorebot_client


async def moorebot_get_status() -> dict:
    """
    Get Moorebot Scout robot status.

    FEATURES:
    - Battery level and charging status
    - Current position and room
    - Movement status (idle/moving/patrolling/charging)
    - WiFi signal strength
    - Sensor health check

    REQUIREMENTS:
    - Robot must be powered on and connected to network
    - Client must be initialized with robot IP address

    Returns:
        Status dict with battery, position, sensors, WiFi signal

    Examples:
        # Get current status
        status = await moorebot_get_status()
        # {
        #   "success": True,
        #   "status": "idle",
        #   "battery_level": 85,
        #   "charging": False,
        #   "position": {"x": 2.5, "y": 1.0, "heading": 45, "room": "living_room"},
        #   "wifi_signal": -45
        # }

    Notes:
        - Battery <20% triggers auto-return-to-dock
        - Position is relative to charging dock (home base at 0,0)
        - Mock mode generates realistic test data
    """
    try:
        client = get_moorebot_client()
        if not client._connected:
            await client.connect()
        return await client.get_status()
    except Exception as e:
        logger.exception("Failed to get Moorebot status:")
        return {
            "success": False,
            "message": str(e),
            "error": str(e),
            "suggestion": "Check robot is powered on and connected to network",
        }


async def moorebot_move(linear: float = 0.0, angular: float = 0.0, duration: float = 0.0) -> dict:
    """
    Move Moorebot Scout with specified velocities.

    FEATURES:
    - Omnidirectional movement (mecanum wheels)
    - Precise velocity control
    - Timed movements or continuous
    - Emergency stop capability

    REQUIREMENTS:
    - Robot must be in idle state (not charging/patrolling)
    - Velocities within safe limits
    - Clear path (obstacle avoidance is basic)

    Args:
        linear: Linear velocity in m/s (forward/backward, range: -0.3 to 0.3)
        angular: Angular velocity in rad/s (rotation, range: -2.0 to 2.0)
        duration: Movement duration in seconds (0 = continuous until stopped)

    Returns:
        Movement confirmation dict

    Examples:
        # Move forward at 0.2 m/s for 3 seconds
        await moorebot_move(linear=0.2, duration=3.0)

        # Rotate in place (clockwise)
        await moorebot_move(angular=-1.0, duration=2.0)

        # Strafe right (mecanum wheels!)
        # Note: Requires custom ROS node for lateral movement

        # Emergency stop
        await moorebot_move(0.0, 0.0)

    Notes:
        - Mecanum wheels allow omnidirectional movement
        - Linear velocity: positive=forward, negative=backward
        - Angular velocity: positive=counter-clockwise, negative=clockwise
        - Robot will stop if ToF sensor detects obstacle <20cm
    """
    try:
        client = get_moorebot_client()

        # Validate velocities
        if not (-0.3 <= linear <= 0.3):
            return {
                "success": False,
                "message": "Linear velocity out of range",
                "error": "Linear velocity out of range",
                "valid_range": "-0.3 to 0.3 m/s",
            }

        if not (-2.0 <= angular <= 2.0):
            return {
                "success": False,
                "message": "Angular velocity out of range",
                "error": "Angular velocity out of range",
                "valid_range": "-2.0 to 2.0 rad/s",
            }

        return await client.move(linear, angular, duration)
    except Exception as e:
        logger.exception("Moorebot move failed:")
        return {"success": False, "message": str(e), "error": str(e)}


async def moorebot_patrol(route: str = "default") -> dict:
    """
    Start autonomous patrol route.

    FEATURES:
    - Pre-defined patrol routes (default, perimeter, rooms)
    - Automatic waypoint navigation
    - Obstacle avoidance during patrol
    - Auto-return-to-dock when complete

    REQUIREMENTS:
    - Robot must be in idle state
    - Battery >30% recommended
    - Clear floor space (remove obstacles)

    Args:
        route: Patrol route name
            - "default": Living room -> Bedroom -> Kitchen -> Home
            - "perimeter": Full apartment perimeter
            - "rooms": Quick check of all rooms

    Returns:
        Patrol status with waypoints and estimated duration

    Examples:
        # Start default patrol
        result = await moorebot_patrol("default")
        # {
        #   "success": True,
        #   "route": "default",
        #   "waypoints": 4,
        #   "estimated_duration": 240
        # }

        # Perimeter security check
        await moorebot_patrol("perimeter")

    Notes:
        - Patrol can be stopped with moorebot_stop_patrol()
        - Robot will pause patrol if battery drops below 25%
        - Custom routes can be defined in configuration
        - Patrols scheduled for Japan trips (Oct annually)
    """
    try:
        client = get_moorebot_client()
        return await client.start_patrol(route)
    except Exception as e:
        logger.exception("Moorebot patrol failed:")
        return {"success": False, "message": str(e), "error": str(e)}


async def moorebot_stop_patrol() -> dict:
    """
    Stop current patrol route.

    Returns:
        Stop confirmation
    """
    try:
        client = get_moorebot_client()
        return await client.stop_patrol()
    except Exception as e:
        logger.exception("Failed to stop patrol:")
        return {"success": False, "message": str(e), "error": str(e)}


async def moorebot_return_to_dock() -> dict:
    """
    Return Moorebot Scout to charging dock.

    FEATURES:
    - Automatic navigation to home base
    - IR beacon tracking for dock location
    - Auto-alignment and docking
    - Charging status monitoring

    REQUIREMENTS:
    - Charging dock must be powered and in clear space
    - Robot should be within 5m of dock
    - Dock should be on hard floor (not carpet)

    Returns:
        Docking status (success or failure with reason)

    Examples:
        # Return to dock
        result = await moorebot_return_to_dock()
        if result["success"]:
            logger.info("Docked successfully, charging")
        else:
            logger.error(f"Docking failed: {result['error']}")
            logger.info(f"Suggestion: {result['suggestion']}")

    Notes:
        - Docking has ~70% success rate (known issue)
        - Common failures: alignment problems, IR interference
        - If docking fails 3 times, manual placement recommended
        - Place dock in well-lit area for better IR detection
    """
    try:
        client = get_moorebot_client()
        return await client.return_to_dock()
    except Exception as e:
        logger.exception("Return to dock failed:")
        return {"success": False, "message": str(e), "error": str(e)}


async def moorebot_get_sensors() -> dict:
    """
    Get current sensor readings from Moorebot Scout.

    FEATURES:
    - Time-of-Flight distance sensor (obstacle detection)
    - IMU data (orientation, acceleration, angular velocity)
    - Light sensor (ambient light level, 2 channels)
    - Timestamp for sensor synchronization

    REQUIREMENTS:
    - Robot must be powered on
    - Sensors initialized (automatic on boot)

    Returns:
        Sensor data dict with ToF, IMU, and light readings

    Examples:
        # Get sensor data
        sensors = await moorebot_get_sensors()
        # {
        #   "tof_distance": 1.235,  # meters
        #   "light_ch0": 45000,     # lux (upper 16 bits)
        #   "light_ch1": 32000,     # lux (lower 16 bits)
        #   "imu": {
        #     "orientation": {"x": 0.0, "y": 0.0, "z": 0.05, "w": 0.998},
        #     "angular_velocity": {"x": 0.001, "y": -0.002, "z": 0.015},
        #     "linear_acceleration": {"x": 0.05, "y": -0.03, "z": 9.78}
        #   },
        #   "timestamp": "2025-12-02T10:30:45.123456"
        # }

    Notes:
        - ToF sensor range: 0.1m to 3.0m
        - IMU provides 6-axis data (gyro + accel)
        - Light sensor useful for room identification
        - Sensor data rate: ~30 Hz
    """
    try:
        client = get_moorebot_client()
        data = await client.get_sensor_data()
        return {
            "success": True,
            "tof_distance": data.tof_distance,
            "light_ch0": data.light_ch0,
            "light_ch1": data.light_ch1,
            "imu": {
                "orientation": {
                    "x": data.imu_orientation[0],
                    "y": data.imu_orientation[1],
                    "z": data.imu_orientation[2],
                    "w": data.imu_orientation[3],
                },
                "angular_velocity": {
                    "x": data.imu_angular_velocity[0],
                    "y": data.imu_angular_velocity[1],
                    "z": data.imu_angular_velocity[2],
                },
                "linear_acceleration": {
                    "x": data.imu_linear_acceleration[0],
                    "y": data.imu_linear_acceleration[1],
                    "z": data.imu_linear_acceleration[2],
                },
            },
            "timestamp": data.timestamp.isoformat(),
        }
    except Exception as e:
        logger.exception("Failed to get sensor data:")
        return {"success": False, "message": str(e), "error": str(e)}


async def moorebot_get_camera_stream() -> dict:
    """
    Get Moorebot Scout camera stream URLs.

    FEATURES:
    - 1080p H.264 video stream
    - 120° wide-angle lens
    - Infrared night vision
    - Two-way audio (AAC)

    REQUIREMENTS:
    - Robot must be powered on
    - Network connectivity required
    - RTSP client for viewing

    Returns:
        Stream URLs (RTSP) for video and audio

    Examples:
        # Get stream URLs
        streams = await moorebot_get_camera_stream()
        # {
        #   "success": True,
        #   "video_url": "rtsp://192.168.1.100:8554/stream",
        #   "audio_url": "rtsp://192.168.1.100:8554/audio",
        #   "resolution": "1080p",
        #   "fps": 30
        # }

        # Use with VLC, FFmpeg, or Frigate NVR
        # ffplay rtsp://192.168.1.100:8554/stream

    Notes:
        - Stream uses RTSP protocol (port 8554)
        - Can be integrated with Frigate NVR
        - Night vision activates automatically in low light
        - Snapshot endpoint also available (JPEG)
    """
    try:
        client = get_moorebot_client()
        video_url = await client.get_video_stream_url()
        audio_url = await client.get_audio_stream_url()

        return {
            "success": True,
            "video_url": video_url,
            "audio_url": audio_url,
            "resolution": "1080p",
            "fps": 30,
            "codec": "H.264",
            "night_vision": True,
        }
    except Exception as e:
        logger.exception("Failed to get camera stream:")
        return {"success": False, "message": str(e), "error": str(e)}
