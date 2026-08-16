"""ONVIF camera implementation for Tapo and other ONVIF-compatible cameras."""

import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse

from PIL import Image

from .base import BaseCamera, CameraFactory, CameraType

logger = logging.getLogger(__name__)


class ONVIFCameraWrapper:
    """Wrapper for python-onvif-zeep camera interface."""

    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self._camera = None
        self._ptz = None
        self._media = None
        self._profiles = None

    def connect(self) -> bool:
        """Connect to ONVIF camera - clears cached connection state."""
        try:
            from onvif import ONVIFCamera

            # Clear any cached connection state to force fresh auth
            self._camera = None
            self._ptz = None
            self._media = None
            self._profiles = None

            # Create fresh connection (no caching - always re-authenticate)
            # Set shorter timeout to prevent 20+ second delays
            import zeep

            transport = zeep.transports.Transport(timeout=10)  # 10 second timeout
            self._camera = ONVIFCamera(self.host, self.port, self.username, self.password, transport=transport)
            logger.info(f"ONVIF camera connected at {self.host}:{self.port} (fresh connection)")
            return True
        except Exception as e:
            logger.warning("Failed to connect to ONVIF camera at %s:%s: %s", self.host, self.port, e)
            # Don't raise exception - just return False for graceful failure
            return False

    def get_device_info(self) -> dict:
        """Get device information."""
        if not self._camera:
            raise RuntimeError("Camera not connected")
        info = self._camera.devicemgmt.GetDeviceInformation()
        return {
            "manufacturer": info.Manufacturer,
            "model": info.Model,
            "firmware_version": info.FirmwareVersion,
            "serial_number": info.SerialNumber,
            "hardware_id": info.HardwareId,
        }

    def get_media_profiles(self) -> list:
        """Get available media profiles."""
        if not self._camera:
            raise RuntimeError("Camera not connected")
        if not self._media:
            self._media = self._camera.create_media_service()
        if not self._profiles:
            self._profiles = self._media.GetProfiles()
        return self._profiles

    def get_stream_uri(self, profile_token: str | None = None) -> str:
        """Get RTSP stream URI for a profile."""
        if not self._camera:
            raise RuntimeError("Camera not connected")
        if not self._media:
            self._media = self._camera.create_media_service()

        profiles = self.get_media_profiles()
        if not profiles:
            raise RuntimeError("No media profiles available")

        # Use specified profile or first one (mainStream)
        if profile_token:
            profile = next((p for p in profiles if p.token == profile_token), profiles[0])
        else:
            profile = profiles[0]

        # Create proper request object for GetStreamUri
        req = self._media.create_type("GetStreamUri")
        req.ProfileToken = profile.token
        req.StreamSetup = {
            "Stream": "RTP-Unicast",
            "Transport": {"Protocol": "RTSP"},
        }
        uri_response = self._media.GetStreamUri(req)
        return uri_response.Uri

    def get_snapshot_uri(self, profile_token: str | None = None) -> str:
        """Get snapshot URI for a profile."""
        if not self._camera:
            raise RuntimeError("Camera not connected")
        if not self._media:
            self._media = self._camera.create_media_service()

        profiles = self.get_media_profiles()
        if not profiles:
            raise RuntimeError("No media profiles available")

        # Use jpegStream profile if available, otherwise first profile
        if profile_token:
            profile = next((p for p in profiles if p.token == profile_token), profiles[0])
        else:
            # Try to find jpegStream profile
            jpeg_profile = next((p for p in profiles if "jpeg" in p.Name.lower()), None)
            profile = jpeg_profile or profiles[0]

        # Create proper request for GetSnapshotUri
        req = self._media.create_type("GetSnapshotUri")
        req.ProfileToken = profile.token
        uri_response = self._media.GetSnapshotUri(req)
        return uri_response.Uri

    def get_ptz_service(self):
        """Get PTZ service."""
        if not self._camera:
            raise RuntimeError("Camera not connected")
        if not self._ptz:
            self._ptz = self._camera.create_ptz_service()
        return self._ptz

    def continuous_move(self, pan: float = 0, tilt: float = 0, zoom: float = 0):
        """Start continuous PTZ movement."""
        ptz = self.get_ptz_service()
        profiles = self.get_media_profiles()
        if not profiles:
            raise RuntimeError("No media profiles for PTZ")

        # Ensure we have valid velocity values
        # Tapo C200 might need specific velocity ranges
        pan = float(pan) if pan != 0 else 0.0
        tilt = float(tilt) if tilt != 0 else 0.0
        zoom = float(zoom) if zoom != 0 else 0.0

        # Create velocity structure - ensure proper format for ONVIF
        velocity = {
            "PanTilt": {
                "x": pan,  # Pan velocity (-1.0 to 1.0)
                "y": tilt,  # Tilt velocity (-1.0 to 1.0)
            }
        }

        # Only add zoom if it's non-zero (some cameras don't support zoom)
        if zoom != 0:
            velocity["Zoom"] = {"x": zoom}

        request = ptz.create_type("ContinuousMove")
        request.ProfileToken = profiles[0].token
        request.Velocity = velocity

        logger.debug(f"PTZ continuous move: pan={pan}, tilt={tilt}, zoom={zoom}")
        ptz.ContinuousMove(request)

    def relative_move(self, pan_normalized: float = 0, tilt_normalized: float = 0, zoom: float = 0):
        """Move PTZ camera relatively using normalized ONVIF coordinates (-1.0 to 1.0)."""
        self.get_ptz_service()  # Ensure PTZ service is available
        profiles = self.get_media_profiles()
        if not profiles:
            raise RuntimeError("No media profiles for PTZ")

        # Get current position (normalized -1.0 to 1.0)
        current_pos = self.get_current_position()
        if not current_pos:
            # If we can't get current position, use goto_position with the requested coordinates
            logger.warning("Cannot get current PTZ position, using absolute movement")
            self.goto_position(pan_normalized, tilt_normalized, zoom)
            return

        # Calculate new position using normalized coordinates
        new_pan = current_pos.get("pan", 0) + pan_normalized
        new_tilt = current_pos.get("tilt", 0) + tilt_normalized
        new_zoom = current_pos.get("zoom", 0) + zoom

        # Clamp to valid ONVIF ranges (-1.0 to 1.0)
        new_pan = max(-1.0, min(1.0, new_pan))
        new_tilt = max(-1.0, min(1.0, new_tilt))
        new_zoom = max(0.0, min(1.0, new_zoom))  # Zoom is usually 0.0 to 1.0

        logger.debug(
            f"Relative move: current=({current_pos.get('pan', 0):.3f}, {current_pos.get('tilt', 0):.3f}) -> "
            f"target=({new_pan:.3f}, {new_tilt:.3f})"
        )

        # Use goto_position for absolute movement
        self.goto_position(new_pan, new_tilt, new_zoom)

    def stop_move(self):
        """Stop PTZ movement."""
        ptz = self.get_ptz_service()
        profiles = self.get_media_profiles()
        if not profiles:
            return

        request = ptz.create_type("Stop")
        request.ProfileToken = profiles[0].token
        request.PanTilt = True
        request.Zoom = True
        ptz.Stop(request)

    def go_to_preset(self, preset_token: str):
        """Go to a PTZ preset."""
        ptz = self.get_ptz_service()
        profiles = self.get_media_profiles()
        if not profiles:
            raise RuntimeError("No media profiles for PTZ")

        request = ptz.create_type("GotoPreset")
        request.ProfileToken = profiles[0].token
        request.PresetToken = preset_token
        ptz.GotoPreset(request)

    def get_presets(self) -> list:
        """Get PTZ presets."""
        ptz = self.get_ptz_service()
        profiles = self.get_media_profiles()
        if not profiles:
            return []

        presets = ptz.GetPresets(profiles[0].token)
        return [{"token": p.token, "name": p.Name} for p in presets]

    def get_current_position(self) -> dict:
        """Get current PTZ position."""
        ptz = self.get_ptz_service()
        profiles = self.get_media_profiles()
        if not profiles:
            return {}

        try:
            status = ptz.GetStatus(profiles[0].token)
            position = status.Position if hasattr(status, "Position") else {}

            result = {}
            if hasattr(position, "PanTilt"):
                result["pan"] = getattr(position.PanTilt, "x", 0)
                result["tilt"] = getattr(position.PanTilt, "y", 0)
            if hasattr(position, "Zoom"):
                result["zoom"] = getattr(position.Zoom, "x", 0)

            return result
        except Exception as e:
            logger.warning(f"Could not get PTZ position: {e}")
            return {}

    def goto_position(self, pan: float, tilt: float, zoom: float = 0):
        """Go to absolute PTZ position."""
        ptz = self.get_ptz_service()
        profiles = self.get_media_profiles()
        if not profiles:
            raise RuntimeError("No media profiles for PTZ")

        request = ptz.create_type("AbsoluteMove")
        request.ProfileToken = profiles[0].token
        request.Position = {"PanTilt": {"x": pan, "y": tilt}, "Zoom": {"x": zoom}}
        ptz.AbsoluteMove(request)


@CameraFactory.register(CameraType.ONVIF)
class ONVIFBasedCamera(BaseCamera):
    """ONVIF-based camera implementation."""

    def __init__(self, config, mock_camera=None):
        super().__init__(config)
        self._camera: ONVIFCameraWrapper | None = None
        self._mock_camera = mock_camera
        self._stream_url: str | None = None
        self._snapshot_url: str | None = None

    async def connect(self) -> bool:
        """Initialize connection to the ONVIF camera."""
        # If already connected, return True
        if self._is_connected and self._camera:
            return True

        try:
            if self._mock_camera:
                self._camera = self._mock_camera
            else:
                host = self.config.params["host"]
                port = self.config.params.get("onvif_port", 2020)
                username = self.config.params["username"]
                password = self.config.params["password"]

                # Create wrapper (reuse if already exists and valid)
                if not self._camera:
                    self._camera = ONVIFCameraWrapper(host, port, username, password)

                # Connect in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                connected = await loop.run_in_executor(None, self._camera.connect)

                if not connected:
                    raise ConnectionError(f"ONVIF handshake failed for {host}:{port}")

            self._is_connected = True
            host = self.config.params.get("host", "unknown")
            logger.info("Successfully connected to ONVIF camera at %s", host)
            return True

        except Exception as e:
            self._is_connected = False
            self._camera = None
            host = self.config.params.get("host", "unknown")
            error_msg = str(e)
            logger.exception("Failed to connect to ONVIF camera at %s", host)
            raise ConnectionError(f"Failed to connect to ONVIF camera {host}: {error_msg}") from e

    async def disconnect(self) -> None:
        """Close connection to the camera."""
        self._is_connected = False
        self._camera = None
        self._stream_url = None
        self._snapshot_url = None

    async def capture_still(self, save_path: str | None = None) -> Image.Image:
        """Capture a still image from the camera via RTSP stream.

        Note: Tapo cameras don't support ONVIF GetSnapshotUri, so we grab
        a frame from the RTSP stream using OpenCV.
        """
        if not await self.is_connected():
            await self.connect()

        try:
            import cv2

            loop = asyncio.get_event_loop()

            # Get RTSP stream URL
            stream_url = await self.get_stream_url()
            if not stream_url:
                raise RuntimeError("Could not get stream URL")

            # Add auth credentials to RTSP URL
            username = self.config.params["username"]
            password = self.config.params["password"]
            # Parse and rebuild URL with auth
            parsed = urlparse(stream_url)
            auth_url = f"rtsp://{username}:{password}@{parsed.hostname}:{parsed.port or 554}{parsed.path}"

            # Capture frame from RTSP in thread pool
            def grab_frame():
                cap = cv2.VideoCapture(auth_url)
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    ret, frame = cap.read()
                    if not ret:
                        raise RuntimeError("Failed to grab frame from RTSP stream")
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    return Image.fromarray(frame_rgb)
                finally:
                    cap.release()

            image = await loop.run_in_executor(None, grab_frame)

            # Save if path provided
            if save_path:
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(save_path)

            return image

        except Exception as e:
            logger.exception("Failed to capture ONVIF snapshot via RTSP")
            raise RuntimeError(f"Failed to capture image: {e}") from e

    async def get_stream_url(self) -> str | None:
        """Get the RTSP stream URL for the camera - CRITICAL: Must work for streaming."""
        # Ensure we're connected
        if not await self.is_connected():
            try:
                logger.info(f"Connecting to {self.config.name} to get stream URL...")
                await asyncio.wait_for(self.connect(), timeout=15.0)
            except TimeoutError:
                logger.exception(f"Camera {self.config.name} connection timed out when getting stream URL")
                return None
            except Exception:
                logger.exception(f"Camera {self.config.name} connection failed when getting stream URL")
                return None

        # Use cached URL if available and we're connected (stream URLs don't change frequently)
        if self._stream_url and await self.is_connected() and self._camera:
            logger.debug(f"Using cached stream URL for {self.config.name}")
            return self._stream_url

        # Get fresh stream URL - this is critical for streaming
        if not self._camera:
            logger.error(f"Camera {self.config.name} wrapper is None - cannot get stream URL")
            return None

        try:
            loop = asyncio.get_event_loop()
            stream_url = await asyncio.wait_for(loop.run_in_executor(None, self._camera.get_stream_uri), timeout=10.0)
            if stream_url:
                logger.info(f"Got stream URL for {self.config.name}: {stream_url[:50]}...")
                self._stream_url = stream_url
                return stream_url
            logger.error(f"Camera {self.config.name} returned None stream URL")
            return None
        except TimeoutError:
            logger.exception(f"Failed to get ONVIF stream URI for {self.config.name} - timed out")
            self._stream_url = None
            return None
        except Exception:
            logger.exception("Failed to get ONVIF stream URL for")
            self._stream_url = None  # Clear cache on error
            # Don't raise - return None so caller can handle gracefully
            return None

    async def get_status(self) -> dict:
        """Get camera status with detailed capabilities."""
        if not await self.is_connected():
            try:
                await self.connect()
            except Exception as e:
                return {
                    "connected": False,
                    "error": str(e),
                    "resolution": "N/A",
                    "ptz_capable": False,
                    "audio_capable": False,
                    "streaming_capable": False,
                    "capture_capable": False,
                }

        try:
            loop = asyncio.get_event_loop()
            device_info = await loop.run_in_executor(None, self._camera.get_device_info)

            # Check PTZ capability - bounded so a slow PTZ WSDL fetch cannot blow the
            # caller's status budget. A failed probe must NOT reset the connection:
            # otherwise every status call restarts the cold ONVIF handshake and the
            # camera reports "Status check timed out" forever after each restart.
            ptz_capable = False
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, self._camera.get_ptz_service),
                    timeout=2.0,
                )
                ptz_capable = True
            except Exception as e:
                logger.debug(f"PTZ service not available for {self.config.name}: {e}")

            # Get profiles for resolution info
            profiles = await loop.run_in_executor(None, self._camera.get_media_profiles)
            resolution = "Unknown"
            if profiles and hasattr(profiles[0], "VideoEncoderConfiguration"):
                vec = profiles[0].VideoEncoderConfiguration
                if vec and hasattr(vec, "Resolution"):
                    resolution = f"{vec.Resolution.Width}x{vec.Resolution.Height}"

            return {
                "connected": True,
                "model": device_info.get("model", "Unknown"),
                "firmware": device_info.get("firmware_version", "Unknown"),
                "manufacturer": device_info.get("manufacturer", "Unknown"),
                "streaming": await self.is_streaming(),
                "resolution": resolution,
                "ptz_capable": ptz_capable,
                "digital_zoom_capable": True,  # Digital zoom always available
                "audio_capable": False,  # ONVIF audio check would need more work
                "streaming_capable": True,
                "capture_capable": True,
            }
        except Exception as e:
            self._is_connected = False
            return {
                "connected": False,
                "error": str(e),
                "resolution": "N/A",
                "ptz_capable": False,
                "digital_zoom_capable": True,  # Digital zoom always available even on error
                "audio_capable": False,
                "streaming_capable": False,
                "capture_capable": False,
            }

    async def get_info(self) -> dict:
        """Get comprehensive ONVIF camera information."""
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

            if await self.is_connected():
                try:
                    loop = asyncio.get_event_loop()
                    device_info = await loop.run_in_executor(None, self._camera.get_device_info)
                    info.update(
                        {
                            "model": device_info.get("model"),
                            "firmware_version": device_info.get("firmware_version"),
                            "serial_number": device_info.get("serial_number"),
                            "manufacturer": device_info.get("manufacturer"),
                            "hardware_id": device_info.get("hardware_id"),
                        }
                    )
                except Exception as e:
                    info["device_info_error"] = str(e)

            return info

        except Exception as e:
            return {
                "name": self.config.name,
                "type": self.config.type.value,
                "host": self.config.params.get("host", ""),
                "error": f"Failed to get camera info: {e}",
            }

    # PTZ Methods
    async def ptz_move(self, pan: float = 0, tilt: float = 0, zoom: float = 0):
        """Move PTZ camera relatively by degrees.

        Parameters:
            pan: Pan movement in degrees (positive = right, negative = left)
            tilt: Tilt movement in degrees (positive = up, negative = down)
            zoom: Zoom movement (relative, positive = zoom in, negative = zoom out)
        """
        # Only reconnect if we're sure we're not connected
        # This prevents unnecessary reconnections that cause delays
        if not self._is_connected or not self._camera:
            logger.debug("PTZ: Camera not connected, connecting...")
            await self.connect()

        # Quick connection check - if this fails, try reconnect
        try:
            if hasattr(self._camera, "_camera") and self._camera._camera:
                # Test if the underlying connection is still valid
                self._camera._camera.devicemgmt.GetDeviceInformation()
            else:
                raise Exception("Invalid camera connection")
        except Exception:
            logger.warning("PTZ: Connection test failed, reconnecting...")
            await self.connect()

        # Use normalized ONVIF coordinates (-1.0 to 1.0)
        # Larger values give bigger movements
        pan_normalized = pan * 0.3  # 0.3 = reasonable movement size
        tilt_normalized = tilt * 0.3  # 0.3 = reasonable movement size
        zoom_relative = zoom * 0.1  # Reasonable zoom steps

        # Log PTZ movement for debugging
        logger.debug(
            f"PTZ move requested: pan={pan} ({pan_normalized:.3f} normalized), tilt={tilt} ({tilt_normalized:.3f} normalized), zoom={zoom}"
        )

        loop = asyncio.get_event_loop()
        try:
            # Use relative movement instead of continuous
            await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self._camera.relative_move(pan_normalized, tilt_normalized, zoom_relative),
                ),
                timeout=8.0,  # Longer timeout for positioning
            )
            logger.debug("PTZ relative move executed successfully")
        except TimeoutError:
            logger.exception("PTZ move timed out after 8 seconds")
            # Reset connection state on timeout
            self._is_connected = False
            raise Exception("PTZ operation timed out") from None
        except Exception:
            logger.exception("PTZ move failed")
            # Reset connection state on any error
            self._is_connected = False
            raise

    async def ptz_stop(self):
        """Stop PTZ movement."""
        if not await self.is_connected():
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._camera.stop_move)

    async def ptz_go_to_preset(self, preset_token: str):
        """Go to PTZ preset."""
        if not await self.is_connected():
            await self.connect()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._camera.go_to_preset(preset_token))

    async def ptz_get_current_position(self) -> dict:
        """Get current PTZ position asynchronously."""
        if not await self.is_connected():
            await self.connect()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._camera.get_current_position)

    async def ptz_goto_position(self, pan: float, tilt: float, zoom: float = 0):
        """Go to absolute PTZ position asynchronously."""
        if not await self.is_connected():
            await self.connect()

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._camera.goto_position(pan, tilt, zoom))

    async def ptz_get_presets(self) -> list:
        """Get PTZ presets."""
        if not await self.is_connected():
            await self.connect()

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._camera.get_presets)
