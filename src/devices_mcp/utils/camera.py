"""
Camera management and control utilities.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from ..core.models import CameraInfo, CameraStatus, PTZPosition
from .exceptions import CameraConnectionError, CameraNotSupportedError

logger = logging.getLogger(__name__)


@dataclass
class CameraManager:
    """
    Manages connections to multiple Tapo cameras.
    """

    cameras: Dict[str, CameraInfo] = field(default_factory=dict)
    _client: Optional[httpx.AsyncClient] = None

    def __post_init__(self):
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        """Initialize the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0, verify=True, follow_redirects=True)

    async def disconnect(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def add_camera(self, camera_config: Dict[str, Any]) -> CameraInfo:
        """
        Add a new camera to the manager.

        Args:
            camera_config: Camera configuration dictionary

        Returns:
            CameraInfo for the added camera

        Raises:
            CameraConnectionError: If unable to connect to the camera
            CameraAuthError: If authentication fails
            CameraNotSupportedError: If the camera is not supported
        """
        try:
            # This would contain the actual camera connection logic
            # For now, we'll just create a basic camera info object
            camera = CameraInfo(
                id=camera_config.get("id") or f"camera_{len(self.cameras) + 1}",
                name=camera_config.get("name", "Unnamed Camera"),
                model=camera_config.get("model", "Tapo Camera"),
                ip_address=camera_config["host"],
                is_online=True,
                last_seen=datetime.utcnow(),
            )

            async with self._lock:
                self.cameras[camera.id] = camera

            return camera

        except Exception as e:
            logger.exception("Failed to add camera %s", camera_config.get("name"))
            raise CameraConnectionError(f"Failed to add camera: {e}") from e

    async def remove_camera(self, camera_id: str) -> bool:
        """
        Remove a camera from the manager.

        Args:
            camera_id: ID of the camera to remove

        Returns:
            True if the camera was removed, False if not found
        """
        async with self._lock:
            if camera_id in self.cameras:
                del self.cameras[camera_id]
                return True
            return False

    async def get_camera(self, camera_id: str) -> Optional[CameraInfo]:
        """
        Get a camera by ID.

        Args:
            camera_id: ID of the camera to get

        Returns:
            CameraInfo if found, None otherwise
        """
        return self.cameras.get(camera_id)

    async def get_camera_status(self, camera_id: str) -> CameraStatus:
        """
        Get the status of a camera.

        Args:
            camera_id: ID of the camera

        Returns:
            CameraStatus with current status information

        Raises:
            CameraConnectionError: If the camera is not found or not connected
        """
        camera = await self.get_camera(camera_id)
        if not camera:
            raise CameraConnectionError(f"Camera {camera_id} not found")

        # This would contain actual status checking logic
        return CameraStatus(
            camera_id=camera_id,
            is_online=camera.is_online,
            last_seen=camera.last_seen,
            firmware_version="1.0.0",  # Example
            uptime=3600,  # Example
            storage_used=0.5,  # Example
            current_bitrate=2048,  # Example in kbps
            resolution="1920x1080",  # Example
        )

    async def get_ptz_position(self, _camera_id: str) -> PTZPosition:
        """
        Get the current PTZ position of a camera.

        Args:
            camera_id: ID of the camera

        Returns:
            Current PTZ position

        Raises:
            CameraNotSupportedError: If the camera doesn't support PTZ
            CameraConnectionError: If unable to get the position
        """
        # This would contain actual PTZ position retrieval logic
        return PTZPosition(pan=0, tilt=0, zoom=1.0)

    async def move_ptz(self, camera_id: str, direction: str, speed: int = 50) -> None:
        """
        Move the PTZ camera in a specific direction.

        Args:
            camera_id: ID of the camera
            direction: Direction to move (up, down, left, right, etc.)
            speed: Movement speed (1-100)

        Raises:
            CameraNotSupportedError: If the camera doesn't support PTZ
            CameraConnectionError: If the command fails
        """
        # This would contain actual PTZ movement logic
        logger.info(f"Moving camera {camera_id} {direction} at speed {speed}")

    async def take_snapshot(self, _camera_id: str) -> bytes:
        """
        Take a snapshot from the camera.

        Args:
            camera_id: ID of the camera

        Returns:
            JPEG image data

        Raises:
            CameraConnectionError: If unable to take a snapshot
        """
        # This would contain actual snapshot logic
        raise CameraConnectionError("Snapshot not implemented")

    async def get_stream_url(self, camera_id: str, stream_type: str = "rtsp") -> str:
        """
        Get a stream URL for the camera.

        Args:
            camera_id: ID of the camera
            stream_type: Type of stream (rtsp, hls, etc.)

        Returns:
            URL for the stream

        Raises:
            CameraNotSupportedError: If the stream type is not supported
            CameraConnectionError: If unable to get the stream URL
        """
        camera = await self.get_camera(camera_id)
        if not camera:
            raise CameraConnectionError(f"Camera {camera_id} not found")

        # This would generate the appropriate stream URL
        if stream_type.lower() == "rtsp":
            return f"rtsp://{camera.ip_address}/stream1"
        raise CameraNotSupportedError(f"Stream type not supported: {stream_type}")

    async def refresh_all(self) -> None:
        """
        Refresh the status of all cameras.
        """
        # This would update the status of all cameras
        for camera_id in list(self.cameras.keys()):
            try:
                status = await self.get_camera_status(camera_id)
                self.cameras[camera_id].is_online = status.is_online
                self.cameras[camera_id].last_seen = status.last_seen
            except Exception:
                logger.exception("Error refreshing camera %s", camera_id)
                self.cameras[camera_id].is_online = False
