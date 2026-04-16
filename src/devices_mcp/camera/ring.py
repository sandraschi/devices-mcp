"""Ring doorbell camera implementation."""

import asyncio
import io
import logging
from pathlib import Path

from oauthlib.oauth2 import MissingTokenError
from PIL import Image
from ring_doorbell import Auth, Ring

from .base import BaseCamera, CameraFactory, CameraType

logger = logging.getLogger(__name__)


@CameraFactory.register(CameraType.RING)
class RingCamera(BaseCamera):
    """Ring doorbell camera implementation."""

    def __init__(self, config, mock_ring=None):
        super().__init__(config)
        self._mock_ring = mock_ring
        self._ring = None
        self._device = None
        self._stream_url = None
        # Ring cameras have speakerphone capabilities
        self._speakerphone_capable = True
        self._speakerphone_enabled = False
        # Doorbell event tracking
        self._doorbell_events = []

    async def connect(self) -> bool:
        """Initialize connection to the Ring doorbell."""
        try:
            if self._mock_ring:
                # Use mock camera for testing
                await self._mock_ring.connect()
            else:
                # Use real camera for production
                # Initialize Ring authentication
                token_data = None
                if "token_file" in self.config.params:
                    # Load token from file
                    token_file = Path(self.config.params["token_file"])
                    if token_file.exists():
                        import json

                        token_data = json.loads(token_file.read_text())

                auth = Auth(
                    self.config.params.get("token_updater", lambda _x: None),
                    token_data,
                )

                # Create Ring instance
                self._ring = Ring(auth)

                # Authenticate
                try:
                    await asyncio.get_event_loop().run_in_executor(None, lambda: self._ring.update_data())
                except MissingTokenError:
                    # If no token, try to authenticate with username/password
                    if not all(k in self.config.params for k in ["username", "password"]):
                        raise ValueError("Ring authentication requires either a token or username/password") from None

                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self._ring.create_session(
                            self.config.params["username"], self.config.params["password"]
                        ),
                    )

                # Find the specific device
                device_id = self.config.params.get("device_id")
                if device_id:
                    self._device = self._ring.doorbell(device_id)
                else:
                    # Get first available doorbell
                    devices = self._ring.doorbells
                    if not devices:
                        raise ValueError("No Ring doorbells found")
                    self._device = devices[0]

        except Exception as e:
            self._is_connected = False
            logger.exception("Failed to connect to Ring")
            raise ConnectionError(f"Failed to connect to Ring: {e}") from e
        else:
            self._is_connected = True
            return True

    async def disconnect(self) -> None:
        """Close connection to the camera."""
        self._is_connected = False
        self._device = None
        self._ring = None

    async def capture_still(self, save_path: str | None = None) -> Image.Image:
        """Capture a still image from the camera."""
        if not await self.is_connected():
            await self.connect()

        try:
            # Get snapshot from Ring
            snapshot = await asyncio.get_event_loop().run_in_executor(None, lambda: self._device.get_snapshot())

            if not snapshot:
                raise RuntimeError("Failed to capture snapshot from Ring")

            # Convert to PIL Image
            image = Image.open(io.BytesIO(snapshot))

            # Save if path provided
            if save_path:
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(save_path)

        except Exception as e:
            self._is_connected = False
            logger.exception("Failed to capture image from Ring")
            raise RuntimeError(f"Failed to capture image: {e}") from e
        else:
            return image

    async def get_stream_url(self) -> str | None:
        """Get the stream URL for the camera.

        Ring doorbells use WebRTC for live streaming, not HTTP URLs.
        This method returns None to indicate WebRTC should be used instead.
        """
        if not await self.is_connected():
            await self.connect()

        # Ring doorbells require WebRTC for live streaming
        # The stream viewer should detect this and use WebRTC endpoints
        logger.info("Ring doorbell live streaming requires WebRTC - no HTTP URL available")
        return None

    async def get_status(self) -> dict:
        """Get camera status."""
        if not await self.is_connected():
            return {"connected": False, "error": "Not connected to Ring"}

        try:
            # Get device health
            health = await asyncio.get_event_loop().run_in_executor(None, lambda: self._device.health)

            return {
                "connected": True,
                "model": self._device.family,
                "battery_life": health.get("battery_life"),
                "firmware": health.get("firmware_version"),
                "streaming": await self.is_streaming(),
                "speakerphone_capable": self._speakerphone_capable,
                "speakerphone_enabled": self._speakerphone_enabled,
                "doorbell_events": len(await self.get_doorbell_events(limit=5)),  # Recent events count
            }

        except Exception as e:
            self._is_connected = False
            logger.exception("Error getting Ring status")
            return {
                "connected": False,
                "error": str(e),
                "speakerphone_capable": False,
                "speakerphone_enabled": False,
                "doorbell_events": 0,
            }

    async def get_info(self) -> dict:
        """Get comprehensive Ring camera information."""
        try:
            info = {
                "name": self.config.name,
                "type": self.config.type.value,
                "connected": await self.is_connected(),
                "streaming": await self.is_streaming(),
                "capabilities": {
                    "video_capture": True,
                    "image_capture": True,
                    "streaming": True,
                    "ptz": False,
                },
            }

            # Add Ring-specific information if connected
            if await self.is_connected():
                try:
                    health = await asyncio.get_event_loop().run_in_executor(None, lambda: self._device.health)

                    info.update(
                        {
                            "model": self._device.family,
                            "name": self._device.name,
                            "battery_life": health.get("battery_life"),
                            "firmware_version": health.get("firmware_version"),
                            "wifi_signal": health.get("wifi_signal_category"),
                            "device_id": self._device.id,
                        }
                    )
                except Exception as e:
                    info["device_info_error"] = str(e)

        except Exception as e:
            return {
                "name": self.config.name,
                "type": self.config.type.value,
                "error": f"Failed to get camera info: {e}",
            }
        else:
            return info

    # Speakerphone functionality for Ring cameras

    async def enable_speakerphone(self) -> bool:
        """Enable speakerphone mode for two-way audio on Ring cameras."""
        if not self._speakerphone_capable:
            logger.warning("This Ring camera does not support speakerphone")
            return False

        try:
            # Ring cameras support two-way audio through WebRTC
            # This would use the Ring API to enable speakerphone
            if self._device:
                # Enable speakerphone mode
                # Note: This is a placeholder - actual implementation depends on ring-doorbell API
                logger.info("Enabling speakerphone mode on Ring camera")
                self._speakerphone_enabled = True
                return True
            logger.error("Ring camera not connected")
            return False
        except Exception:
            logger.exception("Failed to enable speakerphone on Ring camera:")
            return False

    async def disable_speakerphone(self) -> bool:
        """Disable speakerphone mode on Ring cameras."""
        try:
            if self._device:
                logger.info("Disabling speakerphone mode on Ring camera")
                self._speakerphone_enabled = False
                return True
            logger.warning("Ring camera not connected, speakerphone already disabled")
            self._speakerphone_enabled = False
            return True
        except Exception:
            logger.exception("Failed to disable speakerphone on Ring camera:")
            return False

    async def get_speakerphone_status(self) -> dict[str, any]:
        """Get speakerphone status for Ring cameras."""
        return {
            "speakerphone_capable": self._speakerphone_capable,
            "speakerphone_enabled": self._speakerphone_enabled,
            "device_supports_speakers": True,  # Ring cameras have speakers
            "audio_output_available": True,
            "manufacturer": "Ring (Amazon)",
            "note": "Ring cameras support two-way audio with built-in speakers via WebRTC",
            "speaker_quality": "good",  # Ring speakers are generally good quality
        }

    # Doorbell detection functionality

    async def get_doorbell_events(self, limit: int = 10) -> list[dict]:
        """Get recent doorbell events (dings)."""
        if not await self.is_connected():
            return []

        try:
            # Get doorbell history from Ring API
            history = await asyncio.get_event_loop().run_in_executor(None, lambda: self._device.history(limit=limit))

            events = []
            for event in history:
                if event.get("kind") == "ding":  # Doorbell press event
                    events.append(
                        {
                            "event_id": event.get("id"),
                            "timestamp": event.get("created_at"),
                            "event_type": "doorbell_press",
                            "answered": event.get("answered", False),
                            "recording_available": bool(event.get("recording", {}).get("status") == "ready"),
                            "recording_id": event.get("recording", {}).get("id"),
                            "device_id": str(self._device.id),
                            "device_name": self._device.name,
                        }
                    )

            return events

        except Exception:
            logger.exception("Failed to get doorbell events:")
            return []

    async def get_last_doorbell_event(self) -> dict | None:
        """Get the most recent doorbell event."""
        events = await self.get_doorbell_events(limit=1)
        return events[0] if events else None

    async def has_unanswered_doorbell(self) -> bool:
        """Check if there are unanswered doorbell presses."""
        event = await self.get_last_doorbell_event()
        if not event:
            return False
        return not event.get("answered", False)
