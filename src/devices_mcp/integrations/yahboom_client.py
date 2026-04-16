import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class YahboomClient:
    """Mock client for Yahboom ROS 2 Robot Car."""

    def __init__(self, host: str = "192.168.0.100", port: int = 5000):
        self.host = host
        self.port = port
        self.is_connected = False
        self.battery_level = 95.0
        self.status = "idle"
        self.last_command = None

    async def connect(self):
        """Simulate connection to the robot."""
        logger.info(f"Connecting to Yahboom robot at {self.host}:{self.port}...")
        await time.sleep(0.5)
        self.is_connected = True
        logger.info("Yahboom connected (MOCK).")

    async def get_status(self) -> dict[str, Any]:
        """Return the current status of the robot."""
        # Simulate slight battery drain
        self.battery_level = max(0.0, self.battery_level - 0.01)
        return {
            "connected": self.is_connected,
            "battery": round(self.battery_level, 2),
            "status": self.status,
            "last_command": self.last_command,
            "mode": "ROS2_AUTO",
            "sensors": {"lidar": "active", "imu": "calibrated", "camera": "streaming"},
        }

    async def move(self, direction: str, speed: float = 0.5):
        """Simulate moving the robot."""
        if not self.is_connected:
            raise ConnectionError("Yahboom is not connected.")

        self.status = f"moving_{direction}"
        self.last_command = f"move_{direction}_{speed}"
        logger.info(f"Yahboom moving {direction} at speed {speed}")
        # In a real app, this would send a ROS 2 command or HTTP request
        return True

    async def stop(self):
        """Stop the robot."""
        self.status = "idle"
        self.last_command = "stop"
        logger.info("Yahboom stopped.")
        return True
