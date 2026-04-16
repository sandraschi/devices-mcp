"""Windows webcam implementation that proxies to Windows camera server."""

import io
import logging
import os
from urllib.parse import urljoin

import aiohttp
from PIL import Image

from .base import BaseCamera, CameraFactory, CameraType

logger = logging.getLogger(__name__)


@CameraFactory.register(CameraType.WEBCAM)
class WindowsWebCamera(BaseCamera):
    """Webcam implementation that proxies to Windows camera server."""

    def __init__(self, config, mock_webcam=None):
        super().__init__(config)
        self._device_id = int(self.config.params.get("device_id", 0))
        # Must match scripts/windows_camera_server.py (default port 10715, path /camera/{id}/mjpeg).
        # Use 127.0.0.1 to avoid IPv6 resolution issues with uvicorn.
        self._windows_server_url = os.environ.get("WINDOWS_CAMERA_SERVER_URL", "http://127.0.0.1:10715").rstrip("/")
        self._mock_webcam = mock_webcam
        self._session = None

    async def connect(self) -> bool:
        """Connect to Windows camera server."""
        try:
            logger.info(f"WindowsWebCamera.connect() called for device {self._device_id}")

            if self._mock_webcam:
                # Use mock camera for testing
                await self._mock_webcam.connect()
                self._is_connected = True
                return True

            # Create HTTP session
            self._session = aiohttp.ClientSession()
            logger.info(f"Created HTTP session for Windows camera {self._device_id}")

            # Test connection to Windows camera server
            status_url = urljoin(self._windows_server_url, "/status")
            logger.info(f"Checking Windows camera server status at: {status_url}")

            async with self._session.get(status_url) as response:
                logger.info(f"Windows camera server response status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Windows camera server status data: {data}")
                    cameras = data.get("cameras", {})
                    cam_key = str(self._device_id)

                    if cam_key in cameras and cameras[cam_key].get("has_frame"):
                        self._is_connected = True
                        logger.info(f"Connected to Windows camera {self._device_id}")
                        return True
                    logger.warning(
                        f"Camera {self._device_id} not available on Windows server. Available cameras: {list(cameras.keys())}"
                    )
                    return False
                logger.error(f"Windows camera server status check failed: {response.status}")
                return False

        except Exception:
            logger.exception("Failed to connect to Windows camera server")
            self._is_connected = False
            return False

    async def disconnect(self):
        """Disconnect from camera."""
        self._is_connected = False
        if self._session:
            await self._session.close()
            self._session = None

    async def is_connected(self) -> bool:
        """Check if camera is connected."""
        return self._is_connected

    async def capture_image(self) -> Image.Image | None:
        """Capture image from camera."""
        if not self._is_connected or not self._session:
            return None

        try:
            snapshot_url = urljoin(self._windows_server_url, f"/camera/{self._device_id}/snapshot")
            async with self._session.get(snapshot_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return Image.open(io.BytesIO(image_data))
                logger.error(f"Failed to get snapshot: {response.status}")
                return None
        except Exception:
            logger.exception("Error capturing image:")
            return None

    async def capture_still(self, save_path: str | None = None) -> Image.Image:
        """Capture a still image from the camera."""
        image = await self.capture_image()
        if image is None:
            raise RuntimeError(f"Failed to capture image from Windows camera {self._device_id}")

        if save_path:
            image.save(save_path)

        return image

    async def get_stream_url(self) -> str | None:
        """Get stream URL for camera."""
        if not self._is_connected:
            return None

        # Return URL to Windows camera server MJPEG stream
        return urljoin(self._windows_server_url, f"/camera/{self._device_id}/mjpeg")

    async def get_status(self) -> dict:
        """Get camera status."""
        try:
            # Always create a new session if needed, don't rely on persistent connection
            # for status checks as they can happen before connect()
            async with aiohttp.ClientSession() as session:
                status_url = urljoin(self._windows_server_url, "/status")
                async with session.get(status_url, timeout=2.0) as response:
                    if response.status == 200:
                        data = await response.json()
                        cameras = data.get("cameras", {})
                        cam_key = str(self._device_id)

                        if cam_key in cameras:
                            cam_info = cameras[cam_key]
                            # Update internal state based on latest status
                            self._is_connected = True
                            return {
                                "connected": True,
                                "model": f"Windows Camera {self._device_id}",
                                "streaming": cam_info.get("has_frame", False),
                                "resolution": "Unknown",
                                "ptz_capable": False,
                                "audio_capable": False,
                                "streaming_capable": True,
                                "capture_capable": True,
                            }
                        return {
                            "connected": False,
                            "error": f"Camera {self._device_id} not found on server. Avail: {list(cameras.keys())}",
                        }
                    return {"connected": False, "error": f"Server returned {response.status}"}
        except Exception as e:
            self._is_connected = False
            return {"connected": False, "error": f"Connection failed: {e!s}"}


@CameraFactory.register(CameraType.MICROSCOPE)
class WindowsMicroscopeCamera(WindowsWebCamera):
    """Microscope camera implementation that proxies to Windows camera server."""

    async def get_status(self) -> dict:
        """Get microscope camera status."""
        base_status = await super().get_status()
        if base_status.get("connected"):
            base_status.update(
                {
                    "magnification": self.config.params.get("magnification", 50.0),
                    "led_brightness": self.config.params.get("led_brightness", 80),
                    "focus_mode": self.config.params.get("focus_mode", "auto"),
                    "microscope_features": {
                        "focus_control": True,
                        "led_lighting": True,
                        "calibration": True,
                        "measurement": True,
                    },
                }
            )
        return base_status
