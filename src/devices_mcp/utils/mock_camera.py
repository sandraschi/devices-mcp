"""
Mock camera implementations for testing.

Provides mock implementations of all camera types that don't require real hardware.
"""

import asyncio
import io
import logging
from typing import Any, Dict

from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)


class MockTapoCamera:
    """Mock Tapo camera that simulates real camera behavior without hardware."""

    def __init__(self, config: Dict[str, Any]):
        self.host = config.get("host", "192.168.1.100")
        self.username = config.get("username", "admin")
        self.password = config.get("password", "password")
        self._connected = False
        self._basic_info = {
            "device_info": {"device_model": "Tapo C200"},
            "firmware_version": "1.0.0",
            "mac": "00:11:22:33:44:55",
        }

    async def login(self):
        """Mock login - always succeeds."""
        await asyncio.sleep(0.1)  # Simulate network delay
        self._connected = True
        logger.debug(f"Mock Tapo camera login successful for {self.host}")

    async def getBasicInfo(self):  # noqa: N802 - matches pytapo API naming
        """Mock getBasicInfo - returns simulated device info."""
        if not self._connected:
            await self.login()
        await asyncio.sleep(0.05)  # Simulate network delay
        return self._basic_info

    async def get_image(self):
        """Mock get_image - returns a generated test image."""
        if not self._connected:
            await self.login()

        await asyncio.sleep(0.1)  # Simulate capture delay

        # Create a test image
        img = Image.new("RGB", (1920, 1080), color="lightblue")
        draw = ImageDraw.Draw(img)

        # Add some test content
        draw.text((100, 100), f"Mock Tapo Camera\n{self.host}", fill="black")
        draw.rectangle([50, 50, 1870, 1030], outline="red", width=5)

        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        return img_bytes.getvalue()

    async def disconnect(self):
        """Mock disconnect."""
        self._connected = False
        logger.debug(f"Mock Tapo camera disconnected from {self.host}")


class MockWebCamera:
    """Mock webcam that simulates USB/webcam behavior without hardware."""

    def __init__(self, config: Dict[str, Any]):
        self.device_id = config.get("device_id", 0)
        self._connected = False
        self._streaming = False
        self._resolution = (1920, 1080)
        self._fps = 30

    async def connect(self):
        """Mock webcam connection."""
        await asyncio.sleep(0.1)  # Simulate initialization delay
        self._connected = True
        logger.debug(f"Mock webcam {self.device_id} connected")

    async def disconnect(self):
        """Mock webcam disconnection."""
        self._connected = False
        self._streaming = False
        logger.debug(f"Mock webcam {self.device_id} disconnected")

    async def start_streaming(self):
        """Mock start streaming."""
        if not self._connected:
            await self.connect()
        self._streaming = True
        logger.debug(f"Mock webcam {self.device_id} started streaming")

    async def stop_streaming(self):
        """Mock stop streaming."""
        self._streaming = False
        logger.debug(f"Mock webcam {self.device_id} stopped streaming")

    async def capture_frame(self):
        """Mock frame capture - returns a generated test image."""
        if not self._connected:
            await self.connect()

        await asyncio.sleep(1.0 / self._fps)  # Simulate frame rate

        # Create a test frame
        img = Image.new("RGB", self._resolution, color="lightgreen")
        draw = ImageDraw.Draw(img)

        # Add test content
        draw.text((100, 100), f"Mock Webcam {self.device_id}", fill="black")
        draw.text(
            (100, 150), f"Resolution: {self._resolution[0]}x{self._resolution[1]}", fill="black"
        )
        draw.text((100, 200), f"FPS: {self._fps}", fill="black")
        draw.rectangle(
            [50, 50, self._resolution[0] - 50, self._resolution[1] - 50], outline="blue", width=3
        )

        return img

    def is_connected(self) -> bool:
        """Check if mock webcam is connected."""
        return self._connected

    def is_streaming(self) -> bool:
        """Check if mock webcam is streaming."""
        return self._streaming and self._connected


class MockRingCamera:
    """Mock Ring camera that simulates Ring doorbell behavior without hardware."""

    def __init__(self, config: Dict[str, Any]):
        self.username = config.get("username", "test@example.com")
        self.password = config.get("password", "password")
        self._connected = False
        self._devices = [
            {
                "id": "mock_ring_1",
                "name": "Front Door",
                "device_type": "doorbell",
                "battery_level": 85,
                "signal_strength": 4,
            }
        ]

    async def connect(self):
        """Mock Ring connection."""
        await asyncio.sleep(0.2)  # Simulate Ring API delay
        self._connected = True
        logger.debug(f"Mock Ring camera connected for {self.username}")

    async def disconnect(self):
        """Mock Ring disconnection."""
        self._connected = False
        logger.debug(f"Mock Ring camera disconnected for {self.username}")

    async def get_devices(self):
        """Mock get devices."""
        if not self._connected:
            await self.connect()
        await asyncio.sleep(0.1)  # Simulate API call
        return self._devices

    async def get_live_stream_url(self, device_id: str):
        """Mock live stream URL."""
        if not self._connected:
            await self.connect()
        await asyncio.sleep(0.1)  # Simulate API call
        return f"rtmp://mock.ring.com/live/{device_id}"


class MockPetcubeCamera:
    """Mock Petcube camera that simulates Petcube behavior without hardware."""

    def __init__(self, config: Dict[str, Any]):
        self.email = config.get("email", "test@example.com")
        self.password = config.get("password", "password")
        self.device_id = config.get("device_id", "mock_petcube_1")
        self._connected = False
        self._device_info = {
            "id": self.device_id,
            "name": "Mock Petcube",
            "type": "petcube",
            "battery_level": 90,
            "online": True,
        }

    async def connect(self):
        """Mock Petcube connection."""
        await asyncio.sleep(0.15)  # Simulate Petcube API delay
        self._connected = True
        logger.debug(f"Mock Petcube camera connected for {self.email}")

    async def disconnect(self):
        """Mock Petcube disconnection."""
        self._connected = False
        logger.debug(f"Mock Petcube camera disconnected for {self.email}")

    async def get_device_info(self, _device_id: str):
        """Mock get device info."""
        if not self._connected:
            await self.connect()
        await asyncio.sleep(0.1)  # Simulate API call
        return self._device_info

    async def get_live_stream_url(self, device_id: str):
        """Mock live stream URL."""
        if not self._connected:
            await self.connect()
        await asyncio.sleep(0.1)  # Simulate API call
        return f"rtmp://mock.petcube.com/live/{device_id}"
