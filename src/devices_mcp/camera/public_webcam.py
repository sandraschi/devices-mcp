"""Public webcam camera implementation for external webcams."""

import logging

import aiohttp

from .base import CameraFactory, CameraType
from .webcam import WebCamera

logger = logging.getLogger(__name__)


@CameraFactory.register(CameraType.PUBLIC_WEBCAM)
class PublicWebcam(WebCamera):
    """Public webcam implementation for external webcams."""

    def __init__(self, config, mock_webcam=None):
        super().__init__(config, mock_webcam)
        self._webcam_url = self.config.params.get("url", "")
        self._location = self.config.params.get("location", "Unknown")
        self._description = self.config.params.get("description", "")
        self._update_interval = self.config.params.get("update_interval", 30)  # seconds

    async def get_status(self) -> dict:
        """Get public webcam status."""
        status = await super().get_status()
        status.update(
            {
                "type": CameraType.PUBLIC_WEBCAM.value,
                "webcam_url": self._webcam_url,
                "location": self._location,
                "description": self._description,
                "update_interval": self._update_interval,
                "public_webcam_capable": True,
                "ptz_capable": False,  # Public webcams don't have PTZ
                "digital_zoom_capable": False,  # No control over public cams
            }
        )
        return status

    async def get_stream_url(self) -> str | None:
        """Get the public webcam URL for streaming."""
        if self._webcam_url:
            return self._webcam_url
        return None

    async def get_snapshot(self) -> bytes | None:
        """Get a snapshot from the public webcam."""
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.get(self._webcam_url, timeout=aiohttp.ClientTimeout(total=10)) as response,
            ):
                if response.status == 200:
                    return await response.read()
                logger.warning(f"Failed to get snapshot from {self._webcam_url}: HTTP {response.status}")
                return None
        except Exception:
            logger.exception("Error getting snapshot from public webcam {self.config.name}:")
            return None

    async def test_connection(self) -> bool:
        """Test if the public webcam is accessible."""
        try:
            async with (
                aiohttp.ClientSession() as session,
                session.head(self._webcam_url, timeout=aiohttp.ClientTimeout(total=5)) as response,
            ):
                return response.status == 200
        except Exception as e:
            logger.warning(f"Connection test failed for {self.config.name}: {e}")
            return False
