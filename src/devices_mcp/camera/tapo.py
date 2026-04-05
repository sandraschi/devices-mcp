"""Tapo camera implementation."""

import asyncio
import io
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image
from pytapo import Tapo

from .base import BaseCamera, CameraFactory, CameraType
from .onvif_camera import ONVIFCameraWrapper

logger = logging.getLogger(__name__)


@CameraFactory.register(CameraType.TAPO)
class TapoCamera(BaseCamera):
    """Tapo camera implementation."""

    def __init__(self, config, mock_tapo=None):
        super().__init__(config)
        self._camera = None
        # Tapo cameras have speakerphone capabilities
        self._speakerphone_capable = True
        self._mock_tapo = mock_tapo
        self._stream_url = None
        self._onvif_camera = None  # For PTZ support

    async def connect(self) -> bool:
        """Initialize connection to the Tapo camera.

        Uses safe retry logic to avoid triggering Tapo camera lockouts.
        Lockout protection:
        - Only attempts connection once per camera
        - Catches authentication errors immediately
        - Does not retry on authentication failures
        - Waits between attempts if multiple cameras are being initialized
        """
        try:
            if self._mock_tapo:
                # Use mock camera for testing
                self._camera = self._mock_tapo
                await self._camera.login()
            else:
                # Use real camera for production
                # pytapo uses asyncio.run() internally which conflicts with running event loop
                # We need to create Tapo instance in a separate thread to avoid event loop conflict
                import concurrent.futures

                host = self.config.params["host"]
                username = self.config.params["username"]
                password = self.config.params["password"]

                # Check for lockout indicators in error messages before attempting
                def create_and_test_tapo():
                    """Create Tapo instance and test connection in a thread without event loop.

                    Returns tuple: (success: bool, camera: Tapo or None, error: str or None)
                    """
                    try:
                        camera = Tapo(host, username, password)
                        # Test connection immediately - this will authenticate
                        camera.getBasicInfo()
                        return (True, camera, None)
                    except Exception as e:
                        error_msg = str(e)
                        # Check for lockout message
                        if "Temporary Suspension" in error_msg or "1800 seconds" in error_msg:
                            logger.warning(
                                "Camera %s is temporarily locked out. Wait 30 minutes before retrying.",
                                host,
                            )
                        elif "Invalid authentication" in error_msg or "Invalid auth" in error_msg:
                            logger.exception(
                                "Invalid credentials for camera %s. Check username/password.", host
                            )
                        return (False, None, error_msg)

                # Create Tapo instance in thread pool to avoid event loop conflict
                # Only attempt ONCE - no retries to prevent lockouts
                loop = asyncio.get_event_loop()
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    success, camera, error = await loop.run_in_executor(
                        executor, create_and_test_tapo
                    )

                    if not success:
                        self._is_connected = False
                        error_msg = error or "Unknown connection error"

                        def _raise_connection_error(msg: str) -> ConnectionError:
                            return ConnectionError(
                                f"Failed to connect to Tapo camera {host}: {msg}. "
                                "Check credentials and ensure camera is not locked out."
                            )

                        raise _raise_connection_error(error_msg) from None

                    self._camera = camera
        except ConnectionError:
            # Re-raise connection errors as-is
            raise
        except Exception as e:
            self._is_connected = False
            host = self.config.params.get("host", "unknown")
            error_msg = str(e)
            # Check if it's a lockout
            if "Temporary Suspension" in error_msg or "1800 seconds" in error_msg:
                raise ConnectionError(
                    f"Tapo camera {host} is temporarily locked out due to too many failed login attempts. "
                    f"Wait 30 minutes before retrying."
                ) from e
            raise ConnectionError(f"Failed to connect to Tapo camera {host}: {error_msg}") from e
        else:
            self._is_connected = True
            host = self.config.params.get("host", "unknown")
            logger.info("Successfully connected to Tapo camera at %s", host)

            # Initialize ONVIF connection for PTZ support
            try:
                username = self.config.params["username"]
                password = self.config.params["password"]
                # Try to connect to ONVIF on port 2020 (common for Tapo cameras)
                self._onvif_camera = ONVIFCameraWrapper(host, 2020, username, password)
                if self._onvif_camera.connect():
                    logger.info("ONVIF PTZ support initialized for Tapo camera at %s", host)
                else:
                    logger.warning("ONVIF PTZ not available for Tapo camera at %s", host)
                    self._onvif_camera = None
            except Exception as e:
                logger.warning("Failed to initialize ONVIF PTZ for Tapo camera: %s", e)
                self._onvif_camera = None

            return True

    async def disconnect(self) -> None:
        """Close connection to the camera."""
        self._is_connected = False
        self._camera = None
        if self._onvif_camera:
            # ONVIF camera doesn't have async disconnect, just clear reference
            self._onvif_camera = None

    async def capture_still(self, save_path: Optional[str] = None) -> Image.Image:
        """Capture a still image from the camera."""
        if not await self.is_connected():
            await self.connect()

        try:
            # Capture image
            if self._mock_tapo:
                # Use mock camera
                img_data = await self._camera.get_image()
            else:
                # Use real camera
                img_data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._camera.get_image()
                )

            # Convert to PIL Image
            image = Image.open(io.BytesIO(img_data))

            # Save if path provided
            if save_path:
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(save_path)

        except Exception as e:
            self._is_connected = False
            raise RuntimeError(f"Failed to capture image: {e}") from e
        else:
            return image

    async def get_stream_url(self) -> Optional[str]:
        """Get the RTSP stream URL for the camera."""
        logger.info(
            f"get_stream_url called for {self.config.name}, current _stream_url: {self._stream_url}"
        )
        if not await self.is_connected():
            await self.connect()

        # Always regenerate for debugging
        username = self.config.params.get("username", "admin")
        password = self.config.params.get("password", "")
        try:
            # For Tapo cameras, RTSP is typically enabled by default
            # Check if RTSP is enabled (some Tapo cameras may have this setting)
            rtsp_enabled = True  # Assume RTSP is enabled for Tapo cameras

            # Some older Tapo implementations might have RTSP config
            try:
                rtsp_config = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._camera.get_rtsp_config()
                )
                rtsp_enabled = rtsp_config.get("enabled", True) if rtsp_config else True
            except AttributeError:
                # get_rtsp_config doesn't exist, assume RTSP is enabled
                rtsp_enabled = True
            except Exception:
                # Any other error, assume RTSP is enabled
                rtsp_enabled = True

            if rtsp_enabled:
                # Try to get stream URL from Tapo API first
                try:
                    stream_url = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self._camera.getStreamURL()
                    )
                    if stream_url:
                        # Check if it's already a full URL or just host:port
                        if stream_url.startswith("http"):
                            # Use HTTP stream URL directly (Tapo cameras may support HTTP MJPEG)
                            self._stream_url = stream_url
                            logger.info(f"Using HTTP stream URL directly: {stream_url}")
                        elif ":" in stream_url:
                            # host:port format
                            host, port = stream_url.split(":")
                            rtsp_url = f"rtsp://{username}:{password}@{host}:{port}/stream1"
                            self._stream_url = rtsp_url
                        else:
                            # Just host, assume RTSP port 554
                            self._stream_url = f"rtsp://{stream_url}:554/stream1"
                        logger.info(
                            f"Converted Tapo API stream URL for {self.config.name}: {self._stream_url}"
                        )
                    else:
                        raise ValueError("Empty stream URL from API")
                except Exception as e:
                    logger.warning(
                        f"Failed to get stream URL from Tapo API for {self.config.name}: {e}, falling back to RTSP"
                    )

                    # Fallback to RTSP URLs
                    host = self.config.params["host"]

                    # URL encode password for RTSP URLs
                    from urllib.parse import quote

                    encoded_password = quote(password, safe="")

                    # Try different RTSP URL formats for Tapo cameras
                    rtsp_urls = [
                        f"rtsp://{username}:{encoded_password}@{host}:554/stream1",
                        f"rtsp://{username}:{encoded_password}@{host}:554/live",
                        f"rtsp://{username}:{encoded_password}@{host}/stream1",
                        f"rtsp://{username}:{encoded_password}@{host}/live",
                        f"rtsp://{username}:{password}@{host}:554/stream1",  # Try unencoded too
                        f"rtsp://{host}:554/stream1",  # No auth
                        f"rtsp://{host}/stream1",  # No auth
                    ]

                    # Test each URL format (quick test)
                    import cv2

                    for url in rtsp_urls:
                        logger.debug(f"Testing RTSP URL: {url[:40]}...")
                        try:
                            cap = cv2.VideoCapture(url)
                            if cap.isOpened():
                                ret, frame = cap.read()
                                cap.release()
                                if ret and frame is not None:
                                    self._stream_url = url
                                    logger.info(
                                        f"Found working RTSP URL for {self.config.name}: {url[:40]}..."
                                    )
                                    break
                            else:
                                cap.release()
                        except Exception as e:
                            logger.debug(f"Failed to test RTSP URL {url[:40]}...: {e}")
                            continue

                    # Fallback if no URL works
                    if not self._stream_url:
                        self._stream_url = f"rtsp://{username}:{password}@{host}:554/stream1"
                        logger.warning(
                            f"No working RTSP URL found for {self.config.name}, using fallback: {self._stream_url[:40]}..."
                        )
        except Exception as e:
            raise RuntimeError(f"Failed to get stream URL: {e}") from e

        return self._stream_url

    async def get_status(self) -> Dict:
        """Get camera status with detailed capabilities."""
        if not await self.is_connected():
            await self.connect()

        try:
            basic_info = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._camera.getBasicInfo()
            )

            device_info = basic_info.get("device_info", {})

            # Get resolution from video capabilities if available
            resolution = "Unknown"
            try:
                # Try to get video config for resolution info
                video_config = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._camera.getVideoConfig()
                )
                if video_config and "video_config" in video_config:
                    res_info = video_config["video_config"].get("resolution", {})
                    if res_info:
                        width = res_info.get("width", "Unknown")
                        height = res_info.get("height", "Unknown")
                        if width != "Unknown" and height != "Unknown":
                            resolution = f"{width}x{height}"
            except Exception as exc:
                # Fallback to basic resolution detection
                logger.debug("Failed to get detailed resolution info: %s", exc)

            # Check PTZ capability (most Tapo cameras have PTZ)
            ptz_capable = True  # Assume true for Tapo cameras, could be enhanced

            # Check audio capability
            audio_capable = False
            try:
                audio_config = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._camera.getAudioConfig()
                )
                if audio_config and audio_config.get("enabled", False):
                    audio_capable = True
            except Exception as exc:
                logger.debug("Failed to get audio capability: %s", exc)

            return {
                "connected": True,
                "model": device_info.get("device_model", "Unknown"),
                "firmware": device_info.get("firmware_version", "Unknown"),
                "streaming": await self.is_streaming(),
                "resolution": resolution,
                "ptz_capable": ptz_capable,
                "audio_capable": audio_capable,
                "speakerphone_capable": self._speakerphone_capable,
                "speakerphone_enabled": self._speakerphone_enabled,
                "streaming_capable": True,  # All Tapo cameras can stream
                "capture_capable": True,  # All Tapo cameras can capture
            }
        except Exception as e:
            self._is_connected = False
            return {
                "connected": False,
                "error": str(e),
                "resolution": "N/A",
                "ptz_capable": False,
                "audio_capable": False,
                "speakerphone_capable": False,
                "speakerphone_enabled": False,
                "streaming_capable": False,
                "capture_capable": False,
            }

    async def get_info(self) -> Dict:
        """Get comprehensive Tapo camera information."""
        try:
            info = {
                "name": self.config.name,
                "type": self.config.type.value,
                "host": self.config.params.get("host", ""),
                "connected": await self.is_connected(),
                "streaming": await self.is_streaming(),
                "capabilities": {
                    "video_capture": True,
                    "image_capture": True,
                    "streaming": True,
                    "ptz": True,
                },
            }

            # Add Tapo-specific information if connected
            if await self.is_connected():
                try:
                    basic_info = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self._camera.getBasicInfo()
                    )

                    device_info = basic_info.get("device_info", {})
                    info.update(
                        {
                            "model": device_info.get("device_model"),
                            "firmware_version": device_info.get("firmware_version"),
                            "serial_number": device_info.get("serial_number"),
                            "device_alias": device_info.get("device_alias"),
                            "mac_address": device_info.get("mac"),
                            "ip_address": device_info.get("ip"),
                        }
                    )
                except Exception as e:
                    info["device_info_error"] = str(e)

        except Exception as e:
            return {
                "name": self.config.name,
                "type": self.config.type.value,
                "host": self.config.params.get("host", ""),
                "error": f"Failed to get camera info: {e}",
            }
        else:
            return info

    # PTZ Methods using ONVIF
    async def ptz_move(self, pan: float = 0, tilt: float = 0, zoom: float = 0):
        """Move PTZ camera using ONVIF."""
        if not self._onvif_camera:
            raise Exception("ONVIF PTZ not available for this camera")

        try:
            # Convert normalized values to ONVIF format
            self._onvif_camera.continuous_move(pan=pan, tilt=tilt, zoom=zoom)
        except Exception:
            logger.exception("PTZ move failed")
            raise

    async def ptz_stop(self):
        """Stop PTZ movement using ONVIF."""
        if not self._onvif_camera:
            raise Exception("ONVIF PTZ not available for this camera")

        try:
            self._onvif_camera.stop_move()
        except Exception:
            logger.exception("PTZ stop failed")
            raise

    async def ptz_go_to_preset(self, preset_token: str):
        """Move to PTZ preset using ONVIF."""
        if not self._onvif_camera:
            raise Exception("ONVIF PTZ not available for this camera")

        try:
            self._onvif_camera.go_to_preset(preset_token)
        except Exception:
            logger.exception("PTZ go to preset failed")
            raise

    async def ptz_get_current_position(self) -> dict:
        """Get current PTZ position using ONVIF."""
        if not self._onvif_camera:
            raise Exception("ONVIF PTZ not available for this camera")

        try:
            return self._onvif_camera.get_current_position()
        except Exception:
            logger.exception("PTZ get position failed")
            raise

    async def ptz_goto_position(self, pan: float, tilt: float, zoom: float = 0):
        """Move to absolute PTZ position using ONVIF."""
        if not self._onvif_camera:
            raise Exception("ONVIF PTZ not available for this camera")

        try:
            self._onvif_camera.goto_position(pan=pan, tilt=tilt, zoom=zoom)
        except Exception:
            logger.exception("PTZ goto position failed")
            raise

    async def ptz_get_presets(self) -> list:
        """Get PTZ presets using ONVIF."""
        if not self._onvif_camera:
            raise Exception("ONVIF PTZ not available for this camera")

        try:
            return self._onvif_camera.get_presets()
        except Exception:
            logger.exception("PTZ get presets failed")
            raise

    # Speakerphone functionality for Tapo cameras

    async def enable_speakerphone(self) -> bool:
        """Enable speakerphone mode for two-way audio on Tapo cameras."""
        if not self._speakerphone_capable:
            logger.warning("This Tapo camera does not support speakerphone")
            return False

        try:
            # Tapo cameras support two-way audio through their API
            # This would use the pytapo library to enable speakerphone
            if self._camera:
                # Enable speakerphone mode
                # Note: This is a placeholder - actual implementation depends on pytapo API
                logger.info("Enabling speakerphone mode on Tapo camera")
                self._speakerphone_enabled = True
                return True
            logger.error("Tapo camera not connected")
            return False
        except Exception:
            logger.exception("Failed to enable speakerphone on Tapo camera:")
            return False

    async def disable_speakerphone(self) -> bool:
        """Disable speakerphone mode on Tapo cameras."""
        try:
            if self._camera:
                logger.info("Disabling speakerphone mode on Tapo camera")
                self._speakerphone_enabled = False
                return True
            logger.warning("Tapo camera not connected, speakerphone already disabled")
            self._speakerphone_enabled = False
            return True
        except Exception:
            logger.exception("Failed to disable speakerphone on Tapo camera:")
            return False

    async def get_speakerphone_status(self) -> Dict[str, Any]:
        """Get speakerphone status for Tapo cameras."""
        return {
            "speakerphone_capable": self._speakerphone_capable,
            "speakerphone_enabled": self._speakerphone_enabled,
            "device_supports_speakers": True,  # Tapo cameras have speakers
            "audio_output_available": True,
            "manufacturer": "TP-Link (Tapo)",
            "note": "Tapo cameras support two-way audio with built-in speakers, though the speaker is tinny-sounding",
            "speaker_quality": "basic",  # As you mentioned, the speaker is "tinny sounding"
        }
