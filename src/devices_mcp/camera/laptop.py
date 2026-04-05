"""Laptop camera implementation for built-in laptop cameras."""

import asyncio
import contextlib
import logging
from typing import Dict, Optional

import cv2
from PIL import Image

from .base import BaseCamera, CameraFactory, CameraType

logger = logging.getLogger(__name__)


@CameraFactory.register(CameraType.LAPTOP)
class LaptopCamera(BaseCamera):
    """Laptop camera implementation for built-in cameras."""

    def __init__(self, config, mock_webcam=None):
        super().__init__(config)
        self._cap = None
        self._device_id = int(self.config.params.get("device_id", 0))  # Usually 0 for built-in
        self._frame = None
        self._frame_lock = asyncio.Lock()
        self._mock_webcam = mock_webcam
        self._is_built_in = True

    async def _capture_loop(self):
        """Background task to capture frames."""
        while self._is_connected:
            try:
                if self._mock_webcam:
                    # Use mock camera
                    frame = await self._cap.capture_frame()
                    async with self._frame_lock:
                        self._frame = frame
                else:
                    # Use real camera
                    ret, frame = self._cap.read()
                    if ret:
                        async with self._frame_lock:
                            self._frame = frame
            except Exception as e:
                logger.debug(f"Error in capture loop: {e}")
            finally:
                # Always sleep to prevent tight polling loops
                # 0.1 seconds = 10 FPS (reasonable for status monitoring)
                await asyncio.sleep(0.1)

    async def connect(self) -> bool:
        """Initialize connection to the laptop camera."""
        try:
            if self._mock_webcam:
                # Use mock webcam for testing
                self._cap = self._mock_webcam
                await self._cap.connect()
            else:
                # Use real laptop camera for production
                # Laptop cameras are typically device 0 or 1
                for device_id in [0, 1, 2]:  # Try common laptop camera IDs
                    self._cap = cv2.VideoCapture(device_id)
                    if self._cap.isOpened():
                        # Test if this is actually a built-in camera
                        ret, frame = self._cap.read()
                        if ret and frame is not None:
                            self._device_id = device_id
                            logger.info(f"Connected to laptop camera at device {device_id}")
                            break
                        self._cap.release()

                if not self._cap or not self._cap.isOpened():
                    raise RuntimeError("Could not find laptop camera")

        except Exception as e:
            self._is_connected = False
            if self._cap and not self._mock_webcam:
                self._cap.release()
                self._cap = None
            raise ConnectionError(f"Failed to connect to laptop camera: {e}") from e
        else:
            self._is_connected = True
            if not self._mock_webcam:
                self._capture_task = asyncio.create_task(self._capture_loop())
            return True

    async def disconnect(self) -> None:
        """Close connection to the laptop camera."""
        self._is_connected = False
        if hasattr(self, "_capture_task"):
            self._capture_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._capture_task

        if self._mock_webcam:
            await self._cap.disconnect()
        elif self._cap:
            self._cap.release()
        self._cap = None

    async def capture_still(self, save_path: Optional[str] = None) -> Image.Image:
        """Capture a still image from the laptop camera."""
        if not await self.is_connected():
            await self.connect()

        try:
            if self._mock_webcam:
                # Use mock camera
                frame = await self._cap.capture_frame()
                image = frame
            else:
                # Use real camera
                ret, frame = self._cap.read()
                if not ret:
                    raise RuntimeError("Failed to capture frame from laptop camera")

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame_rgb)

            # Save if path provided
            if save_path:
                from pathlib import Path

                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(save_path)

            return image

        except Exception as e:
            self._is_connected = False
            raise RuntimeError(f"Failed to capture image from laptop camera: {e}") from e

    async def get_stream_url(self) -> Optional[str]:
        """Laptop cameras typically don't have a stream URL."""
        return None

    async def get_status(self) -> Dict:
        """Get laptop camera status with detailed capabilities."""
        connected = await self.is_connected()

        # Get resolution information if connected
        resolution = "Unknown"
        if connected:
            if self._mock_webcam:
                resolution = f"{self._cap._resolution[0]}x{self._cap._resolution[1]}"
            elif self._cap:
                try:
                    width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    if width > 0 and height > 0:
                        resolution = f"{width}x{height}"
                except Exception as exc:
                    logger.debug("Failed to get laptop camera resolution: %s", exc)

        return {
            "connected": connected,
            "model": f"Laptop Camera Device {self._device_id}",
            "firmware": "N/A",
            "device_id": self._device_id,
            "streaming": await self.is_streaming(),
            "resolution": resolution,
            "ptz_capable": False,  # Laptop cameras don't have PTZ
            "digital_zoom_capable": True,  # Digital zoom always available
            "audio_capable": True,  # Laptop cameras often have audio
            "streaming_capable": True,  # Laptop cameras can stream
            "capture_capable": True,  # Laptop cameras can capture
            "built_in": self._is_built_in,
            "camera_type": "laptop",
        }

    async def get_info(self) -> Dict:
        """Get comprehensive laptop camera information."""
        status = await self.get_status()

        return {
            "name": self.config.name,
            "type": "laptop",
            "device_id": self._device_id,
            "built_in": self._is_built_in,
            "status": status,
            "capabilities": {
                "video_capture": True,
                "audio_capture": True,
                "motion_detection": False,  # Not typically available on laptop cameras
                "night_vision": False,
                "ptz_control": False,
                "privacy_shutter": False,  # Hardware dependent
                "led_indicator": True,  # Usually controlled by OS
            },
            "supported_formats": ["JPEG", "PNG"],
            "max_resolution": status["resolution"],
            "connection_type": "USB (built-in)",
        }
