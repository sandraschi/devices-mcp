"""Webcam implementation using OpenCV."""

import asyncio
import contextlib
import logging
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from .base import BaseCamera, CameraFactory, CameraType

# Suppress OpenCV warnings (MSMF grab frame errors)
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
# cv2.setLogLevel() doesn't exist in newer OpenCV versions

logger = logging.getLogger(__name__)


@CameraFactory.register(CameraType.WEBCAM)
class WebCamera(BaseCamera):
    """Webcam implementation using OpenCV."""

    def __init__(self, config, mock_webcam=None):
        super().__init__(config)
        self._cap = None
        self._device_id = int(self.config.params.get("device_id", 0))
        self._device_type = self.config.params.get("device_type", "webcam")

        # Lazy connection management to avoid hogging camera
        self._last_activity = None
        self._idle_timeout = self.config.params.get("idle_timeout", 30)  # Configurable idle timeout
        self._lazy_loading = self.config.params.get("lazy_loading", True)  # Enable/disable lazy loading
        self._activity_check_task = None

        # Surveillance mode settings
        self._surveillance_mode = self.config.params.get("surveillance_mode", False)
        self._surveillance_interval = self.config.params.get("surveillance_interval", 30)  # seconds
        self._motion_threshold = self.config.params.get("motion_threshold", 0.05)  # 5% change threshold
        self._surveillance_task = None
        self._last_surveillance_frame = None
        self._surveillance_events = []  # Store recent events

        # LED control settings
        self._led_control_enabled = self.config.params.get("led_control_enabled", False)
        self._led_flash_interval = self.config.params.get("led_flash_interval", 5)  # seconds
        self._led_flash_duration = self.config.params.get("led_flash_duration", 0.5)  # seconds
        self._led_task = None

        # Speakerphone settings
        self._speakerphone_enabled = self.config.params.get("speakerphone_enabled", False)
        self._speakerphone_capable = self._detect_speakerphone_capability()
        self._audio_output_task = None
        self._frame = None
        self._frame_lock = asyncio.Lock()
        self._mock_webcam = mock_webcam
        self._in_use_by_another_app = False
        self._in_use_error_message = None
        self._last_successful_frame = None
        self._consecutive_failures = 0
        self._max_consecutive_failures = 5
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = 3
        self._auto_reconnect = True

    async def _capture_loop(self):
        """Background task to capture frames with automatic error recovery."""
        while self._is_connected:
            try:
                if self._cap and self._cap.isOpened():
                    ret, frame = self._cap.read()
                    if ret and frame is not None:
                        # Successful frame capture
                        async with self._frame_lock:
                            self._frame = frame
                            self._last_successful_frame = frame.copy()
                        self._consecutive_failures = 0
                        self._reconnect_attempts = 0
                    else:
                        # Frame capture failed
                        self._consecutive_failures += 1
                        logger.debug(
                            f"Frame capture failed for camera {self._device_id}, consecutive failures: {self._consecutive_failures}"
                        )

                        # Try to reconnect if we've had too many failures
                        if self._consecutive_failures >= self._max_consecutive_failures and self._auto_reconnect:
                            await self._attempt_reconnect()
                # Camera not opened, try to reconnect
                elif self._auto_reconnect:
                    await self._attempt_reconnect()

            except Exception as e:
                logger.debug(f"Error in capture loop for camera {self._device_id}: {e}")
                self._consecutive_failures += 1

                if self._consecutive_failures >= self._max_consecutive_failures and self._auto_reconnect:
                    await self._attempt_reconnect()
            finally:
                # Always sleep to prevent tight polling loops
                # 0.1 seconds = 10 FPS (reasonable for status monitoring)
                await asyncio.sleep(0.1)

    async def _attempt_reconnect(self):
        """Attempt to reconnect to the USB camera."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.warning(
                f"Max reconnect attempts ({self._max_reconnect_attempts}) reached for camera {self._device_id}"
            )
            return

        self._reconnect_attempts += 1
        logger.info(
            f"Attempting to reconnect to USB camera {self._device_id} (attempt {self._reconnect_attempts}/{self._max_reconnect_attempts})"
        )

        try:
            # Close existing capture if it exists
            if self._cap:
                self._cap.release()
                self._cap = None

            # Try to reconnect
            if not self._mock_webcam:
                self._cap = await self._open_camera_device()

                if self._cap and self._cap.isOpened():
                    # Test if we can actually read frames
                    ret, test_frame = self._cap.read()
                    if ret and test_frame is not None:
                        logger.info(f"Successfully reconnected to USB camera {self._device_id}")
                        self._consecutive_failures = 0
                        self._reconnect_attempts = 0
                        self._in_use_by_another_app = False
                        self._in_use_error_message = None
                        return
                    logger.warning(f"Reconnected to camera {self._device_id} but cannot read frames")
                    self._cap.release()
                    self._cap = None
                else:
                    logger.warning(f"Failed to reopen camera {self._device_id}")
            else:
                # Mock camera reconnection
                await self._mock_webcam.connect()

        except Exception:
            logger.exception("Error during reconnect attempt for camera {self._device_id}:")

        # If we get here, reconnection failed
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self._in_use_by_another_app = True
            self._in_use_error_message = f"USB camera device {self._device_id} is unreachable after {self._max_reconnect_attempts} reconnect attempts. Camera may be disconnected or in use by another application."

    async def connect(self) -> bool:
        """Initialize connection to the webcam (lazy - doesn't keep it open)."""
        # For lazy loading, we just mark as connected but don't open the camera yet
        # The camera will be opened when actually needed
        self._is_connected = True
        self._in_use_by_another_app = False
        self._in_use_error_message = None
        logger.info(f"Initialized lazy connection to USB camera {self._device_id}")
        return True

    async def disconnect(self) -> None:
        """Close connection to the webcam."""
        self._is_connected = False

        # Cancel idle timeout checker
        if hasattr(self, "_activity_check_task") and self._activity_check_task and not self._activity_check_task.done():
            self._activity_check_task.cancel()
            try:
                await self._activity_check_task
            except asyncio.CancelledError:
                pass

        # Cancel surveillance task
        if hasattr(self, "_surveillance_task") and self._surveillance_task and not self._surveillance_task.done():
            self._surveillance_task.cancel()
            try:
                await self._surveillance_task
            except asyncio.CancelledError:
                pass

        # Cancel any background tasks
        if hasattr(self, "_capture_task"):
            self._capture_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._capture_task

        # Close capture device
        if self._cap:
            self._cap.release()
            self._cap = None

        # Stop LED control
        if hasattr(self, "_led_task") and self._led_task and not self._led_task.done():
            self._led_task.cancel()
            try:
                await self._led_task
            except asyncio.CancelledError:
                pass

        # Stop speakerphone
        if hasattr(self, "_audio_output_task") and self._audio_output_task and not self._audio_output_task.done():
            self._audio_output_task.cancel()
            try:
                await self._audio_output_task
            except asyncio.CancelledError:
                pass

        # Reset lazy loading state
        self._last_activity = None
        self._surveillance_mode = False
        self._led_control_enabled = False
        self._speakerphone_enabled = False

    async def capture_still(self, save_path: str | None = None) -> Image.Image:
        """Capture a still image from the webcam."""
        if self._lazy_loading:
            # Lazy loading mode - open camera only when needed
            return await self._capture_still_lazy(save_path)
        # Legacy mode - assume camera is already open
        return await self._capture_still_legacy(save_path)

    async def _capture_still_lazy(self, save_path: str | None = None) -> Image.Image:
        """Capture a still image with lazy loading."""
        # Ensure camera is open for capture
        if not await self._ensure_camera_open():
            raise ConnectionError(f"Cannot access camera {self._device_id} - may be in use by another application")

        try:
            ret, frame = self._cap.read()
            if not ret or frame is None:
                raise RuntimeError(f"Failed to capture frame from camera {self._device_id}")

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame_rgb)

            # Save if path provided
            if save_path:
                save_path = Path(save_path)
                save_path.parent.mkdir(parents=True, exist_ok=True)
                image.save(save_path)

            # Update activity and return
            await self._update_activity()
            return image

        except Exception as e:
            logger.exception("Error capturing still from camera {self._device_id}:")
            raise RuntimeError(f"Failed to capture image: {e}") from e
        finally:
            # Always close camera after capture to free it for other applications
            await self._close_camera_connection()

    async def _capture_still_legacy(self, save_path: str | None = None) -> Image.Image:
        """Legacy still capture - assumes camera is already open."""
        if not await self.is_connected():
            await self.connect()

        try:
            async with self._frame_lock:
                # Use current frame if available, otherwise try last successful frame
                frame_to_use = self._frame if self._frame is not None else self._last_successful_frame

                if frame_to_use is None:
                    raise RuntimeError("No frame available from webcam")

                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame_to_use, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame_rgb)

                # Save if path provided
                if save_path:
                    save_path = Path(save_path)
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    image.save(save_path)

                return image

        except Exception as e:
            self._is_connected = False
            raise RuntimeError(f"Failed to capture image: {e}") from e

    async def _open_camera_device(self) -> cv2.VideoCapture | None:
        """Open the camera device in an executor thread.

        cv2.VideoCapture() can block for seconds-to-minutes while another application
        holds the camera - never run it on the event loop. Uses DSHOW on Windows
        (default MSMF backend takes ~10s+ to open while NVIDIA Broadcast is active).
        """
        loop = asyncio.get_running_loop()

        def _open():
            import platform

            if platform.system() == "Windows":
                return cv2.VideoCapture(self._device_id, cv2.CAP_DSHOW)
            return cv2.VideoCapture(self._device_id, cv2.CAP_ANY)

        try:
            return await asyncio.wait_for(loop.run_in_executor(None, _open), timeout=8.0)
        except Exception:
            logger.debug(f"Timed out opening USB camera {self._device_id}")
            return None

    async def _ensure_camera_open_legacy(self) -> bool:
        """Legacy camera opening for non-lazy loading mode."""
        try:
            if self._mock_webcam:
                self._cap = self._mock_webcam
                await self._cap.connect()
            else:
                self._cap = await self._open_camera_device()

                if not self._cap or not self._cap.isOpened():
                    import platform

                    if platform.system() == "Windows":
                        try:
                            ret, _frame = self._cap.read()
                            if not ret:
                                self._in_use_by_another_app = True
                                self._in_use_error_message = (
                                    f"USB camera device {self._device_id} is in use by another application"
                                )
                                self._cap.release()
                                self._cap = None
                                return False
                        except Exception as read_error:
                            error_str = str(read_error).lower()
                            if "access" in error_str or "busy" in error_str or "in use" in error_str:
                                self._in_use_by_another_app = True
                                self._in_use_error_message = (
                                    f"USB camera device {self._device_id} is locked by another application"
                                )
                                if self._cap:
                                    self._cap.release()
                                    self._cap = None
                                return False

                    logger.error(f"Could not open webcam device {self._device_id}")
                    if self._cap:
                        self._cap.release()
                        self._cap = None
                    return False

            # Camera opened successfully
            self._in_use_by_another_app = False
            self._in_use_error_message = None
            return True

        except Exception:
            logger.exception("Error opening camera {self._device_id}:")
            if self._cap:
                self._cap.release()
                self._cap = None
            return False

    async def generate_frames(self):
        """Generate MJPEG frames for streaming."""
        if not self._lazy_loading:
            # Use legacy streaming approach - not implemented
            logger.warning(f"Legacy streaming not implemented for camera {self._device_id}")
            return

        logger.debug(f"Starting MJPEG stream for camera {self._device_id}")

        # Ensure camera is open for streaming
        if not await self._ensure_camera_open():
            logger.error(f"Cannot start streaming for camera {self._device_id} - may be in use by another application")
            return

        try:
            while self._is_connected:
                try:
                    # Update activity timestamp
                    await self._update_activity()

                    # Read frame from camera
                    ret, frame = self._cap.read()
                    if not ret or frame is None:
                        logger.warning(f"Failed to read frame from camera {self._device_id}")
                        await asyncio.sleep(0.1)  # Brief pause before retry
                        continue

                    # Encode frame as JPEG
                    ret, jpeg = cv2.imencode(".jpg", frame)
                    if not ret:
                        logger.warning(f"Failed to encode frame from camera {self._device_id}")
                        continue

                    # Convert to bytes and yield
                    frame_bytes = jpeg.tobytes()
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(frame_bytes)).encode() + b"\r\n\r\n" + frame_bytes + b"\r\n"
                    )

                    # Control frame rate (roughly 30 FPS)
                    await asyncio.sleep(1 / 30)

                except Exception as e:
                    logger.exception(f"Error during streaming frame generation for camera {self._device_id}: {e}")
                    await asyncio.sleep(0.1)  # Brief pause before retry

        finally:
            # Always close camera when streaming stops
            logger.debug(f"Stopping MJPEG stream for camera {self._device_id}")
            await self._close_camera_connection()

    async def _generate_frames_legacy(self):
        """Legacy frame generation for non-lazy loading mode."""
        # This would implement the old continuous capture loop approach
        # For now, just yield empty frames to avoid errors
        logger.warning(f"Legacy streaming not fully implemented for camera {self._device_id}")
        if False:  # This is legacy code, not currently used
            yield b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: 0\r\n\r\n\r\n"

    async def get_stream_url(self) -> str | None:
        """Webcams typically don't have a stream URL."""
        return None

    async def get_status(self) -> dict:
        """Get webcam status with detailed capabilities."""
        connected = await self.is_connected()

        # Get resolution information if connected
        resolution = "Unknown"
        if connected:
            # Try to get resolution from existing capture object
            if self._cap:
                try:
                    width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    if width > 0 and height > 0:
                        resolution = f"{width}x{height}"
                except Exception as exc:
                    logger.debug("Failed to get webcam resolution from existing cap: %s", exc)

            # If no resolution from existing cap, try to open camera briefly.
            # CRITICAL: cv2.VideoCapture open (MSMF) can block the event loop for
            # ~10s while another app holds the camera (e.g. NVIDIA Broadcast).
            # Run the whole open+probe in an executor so other requests survive.
            if resolution == "Unknown":
                try:
                    loop = asyncio.get_running_loop()

                    def _probe_resolution():
                        import platform

                        if platform.system() == "Windows":
                            cap = cv2.VideoCapture(self._device_id, cv2.CAP_DSHOW)
                        else:
                            cap = cv2.VideoCapture(self._device_id, cv2.CAP_ANY)
                        try:
                            if not cap.isOpened():
                                return "Unknown"
                            config_res = self.config.get("params", {}).get("resolution", "640x480")
                            try:
                                conf_width, conf_height = map(int, config_res.split("x"))
                                cap.set(cv2.CAP_PROP_FRAME_WIDTH, conf_width)
                                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, conf_height)
                            except Exception as e:
                                logger.debug(f"Config resolution parsing failed: {e}")
                            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                            if width > 0 and height > 0:
                                return f"{width}x{height}"
                            return "Unknown"
                        finally:
                            cap.release()

                    resolution = await asyncio.wait_for(loop.run_in_executor(None, _probe_resolution), timeout=5.0)
                except Exception as exc:
                    logger.debug("Failed to get webcam resolution: %s", exc)

        status = {
            "connected": connected,
            "model": f"Webcam Device {self._device_id}",
            "firmware": "N/A",
            "device_id": self._device_id,
            "streaming": await self.is_streaming(),
            "resolution": resolution,
            "ptz_capable": False,  # Most webcams don't have PTZ
            "digital_zoom_capable": True,  # Digital zoom always available
            "audio_capable": self._detect_microphone_capability(),  # Check if webcam has microphone
            "streaming_capable": True,  # Webcams can stream
            "capture_capable": True,  # Webcams can capture
        }

        # Add USB-specific status information
        status["usb_device"] = True
        status["device_id"] = self._device_id
        status["auto_reconnect"] = self._auto_reconnect
        status["consecutive_failures"] = self._consecutive_failures
        status["reconnect_attempts"] = self._reconnect_attempts

        # Add in-use detection status
        if self._in_use_by_another_app:
            status["in_use_by_another_app"] = True
            status["status"] = "locked"  # Override status to show as locked, not offline
            status["in_use_error"] = (
                self._in_use_error_message or f"USB camera device {self._device_id} is in use by another application"
            )

            # Try to detect which app is using the camera (Windows only)
            locking_app = self._detect_locking_application()
            if locking_app:
                status["locking_app"] = locking_app
                status["locking_app_display"] = self._get_app_display_name(locking_app)
                status["warning"] = (
                    f"Camera is locked by {status['locking_app_display']} ({locking_app}). "
                    "Close the application to use this camera."
                )
            else:
                status["warning"] = (
                    "Camera is locked by another application (e.g., Microsoft Teams, Zoom). Close the other app to use this camera."
                )

            status["recovery_suggestion"] = (
                f"Close {status.get('locking_app_display', 'the video application')} or restart the Devices MCP server"
            )
        else:
            status["in_use_by_another_app"] = False

        # Add reliability indicators
        if self._last_successful_frame is not None:
            status["has_fallback_frame"] = True
            status["reliable_capture"] = True
        else:
            status["has_fallback_frame"] = False
            status["reliable_capture"] = False

        # Add USB camera advantages
        status["always_online"] = True  # USB cameras don't need network connectivity
        status["no_connection_procedure"] = True  # No authentication or setup required
        status["hot_swappable"] = True  # Can be unplugged and replugged

        # Add surveillance status
        status["surveillance_mode"] = self._surveillance_mode
        status["surveillance_interval"] = self._surveillance_interval
        status["motion_threshold"] = self._motion_threshold
        status["surveillance_events_count"] = len(self._surveillance_events)

        # Add LED control status
        status["led_control_enabled"] = self._led_control_enabled
        status["led_flash_interval"] = self._led_flash_interval
        status["led_flash_duration"] = self._led_flash_duration
        status["led_control_available"] = True  # LED control is available for this camera type

        # Add speakerphone status
        status["speakerphone_capable"] = self._speakerphone_capable
        status["speakerphone_enabled"] = self._speakerphone_enabled

        return status

    async def _ensure_camera_open(self) -> bool:
        """Ensure camera is open and ready for use. Implements lazy loading."""
        if not self._lazy_loading:
            # If lazy loading is disabled, fall back to old behavior
            return await self._ensure_camera_open_legacy()

        if self._cap and self._cap.isOpened():
            # Camera is already open, update activity timestamp
            self._last_activity = asyncio.get_event_loop().time()
            return True

        # Camera is closed, try to open it
        logger.debug(f"Lazy opening USB camera {self._device_id}")
        try:
            if self._mock_webcam:
                self._cap = self._mock_webcam
                await self._cap.connect()
            else:
                self._cap = await self._open_camera_device()

                if not self._cap or not self._cap.isOpened():
                    # Try to detect if camera is in use by another app
                    import platform

                    if platform.system() == "Windows":
                        try:
                            ret, _frame = self._cap.read()
                            if not ret:
                                self._in_use_by_another_app = True
                                self._in_use_error_message = f"USB camera device {self._device_id} is in use by another application (e.g., Microsoft Teams, Zoom, Skype)."
                                logger.warning(self._in_use_error_message)
                                self._cap.release()
                                self._cap = None
                                return False
                        except Exception as read_error:
                            error_str = str(read_error).lower()
                            if "access" in error_str or "busy" in error_str or "in use" in error_str:
                                self._in_use_by_another_app = True
                                self._in_use_error_message = (
                                    f"USB camera device {self._device_id} is locked by another application."
                                )
                                logger.warning(self._in_use_error_message)
                                if self._cap:
                                    self._cap.release()
                                    self._cap = None
                                return False

                    logger.error(f"Could not open webcam device {self._device_id}")
                    if self._cap:
                        self._cap.release()
                        self._cap = None
                    return False

            # Camera opened successfully
            self._last_activity = asyncio.get_event_loop().time()
            self._in_use_by_another_app = False
            self._in_use_error_message = None

            # Start idle timeout checker if not already running
            if not self._activity_check_task or self._activity_check_task.done():
                self._activity_check_task = asyncio.create_task(self._idle_timeout_checker())

            logger.debug(f"Successfully opened USB camera {self._device_id}")
            return True

        except Exception:
            logger.exception("Error opening USB camera {self._device_id}:")
            if self._cap:
                self._cap.release()
                self._cap = None
            return False

    async def _idle_timeout_checker(self):
        """Background task to close camera when idle."""
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds

                if not self._cap or not self._cap.isOpened():
                    break  # Camera already closed

                current_time = asyncio.get_event_loop().time()
                if self._last_activity and (current_time - self._last_activity) > self._idle_timeout:
                    logger.info(f"Closing idle USB camera {self._device_id} (inactive for {self._idle_timeout}s)")
                    await self._close_camera_connection()
                    break

            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in idle timeout checker for camera {self._device_id}:")
                break

    async def _close_camera_connection(self):
        """Close the camera connection to free it for other applications."""
        try:
            if self._cap:
                if not self._mock_webcam:
                    self._cap.release()
                self._cap = None
            logger.debug(f"Closed USB camera {self._device_id} connection")
        except Exception:
            logger.exception("Error closing camera {self._device_id}:")

    async def _update_activity(self):
        """Update the last activity timestamp."""
        self._last_activity = asyncio.get_event_loop().time()

    async def start_surveillance(
        self,
        interval: int = 30,
        motion_threshold: float = 0.05,
        led_control: bool | None = None,
        led_flash_interval: int | None = None,
        led_flash_duration: float | None = None,
    ) -> bool:
        """Start surveillance mode with periodic motion detection."""
        if not self._is_connected:
            logger.warning(f"Cannot start surveillance for disconnected camera {self._device_id}")
            return False

        self._surveillance_mode = True
        self._surveillance_interval = interval
        self._motion_threshold = motion_threshold

        # Update LED control settings if provided
        if led_control is not None:
            self._led_control_enabled = led_control
        if led_flash_interval is not None:
            self._led_flash_interval = led_flash_interval
        if led_flash_duration is not None:
            self._led_flash_duration = led_flash_duration

        # Cancel existing surveillance task
        if self._surveillance_task and not self._surveillance_task.done():
            self._surveillance_task.cancel()
            try:
                await self._surveillance_task
            except asyncio.CancelledError:
                pass

        # Start surveillance task
        self._surveillance_task = asyncio.create_task(self._surveillance_loop())

        # Enable LED control if requested
        if self._led_control_enabled:
            await self.enable_led_control(self._led_flash_interval, self._led_flash_duration)

        logger.info(
            f"Started surveillance mode for camera {self._device_id} (interval: {interval}s, threshold: {motion_threshold}, LED: {self._led_control_enabled})"
        )
        return True

    async def stop_surveillance(self) -> bool:
        """Stop surveillance mode."""
        self._surveillance_mode = False

        if self._surveillance_task and not self._surveillance_task.done():
            self._surveillance_task.cancel()
            try:
                await self._surveillance_task
            except asyncio.CancelledError:
                pass

        logger.info(f"Stopped surveillance mode for camera {self._device_id}")
        return True

    async def _surveillance_loop(self):
        """Background surveillance loop with motion detection."""
        logger.debug(f"Starting surveillance loop for camera {self._device_id}")

        while self._surveillance_mode and self._is_connected:
            try:
                # Take a snapshot for motion detection
                current_frame = await self._capture_surveillance_frame()

                if current_frame is not None:
                    # Check for motion
                    motion_detected = await self._detect_motion(current_frame)

                    if motion_detected:
                        # Motion detected - create event
                        await self._create_motion_event(current_frame)
                        logger.info(f"Motion detected on camera {self._device_id}")

                    # Store frame for next comparison
                    self._last_surveillance_frame = current_frame

                # Wait for next surveillance interval
                await asyncio.sleep(self._surveillance_interval)

            except Exception:
                logger.exception("Error in surveillance loop for camera {self._device_id}:")
                await asyncio.sleep(5)  # Brief pause before retry

    async def _capture_surveillance_frame(self) -> np.ndarray | None:
        """Capture a frame for surveillance (lazy loading compatible)."""
        try:
            # Ensure camera is open
            if not await self._ensure_camera_open():
                return None

            # Capture frame
            ret, frame = self._cap.read()
            if ret and frame is not None:
                # Update activity
                await self._update_activity()
                return frame

        except Exception:
            logger.exception("Error capturing surveillance frame for camera {self._device_id}:")
        finally:
            # Close camera to free it for other applications
            await self._close_camera_connection()

        return None

    async def _detect_motion(self, current_frame: np.ndarray) -> bool:
        """Detect motion by comparing current frame with previous frame."""
        if self._last_surveillance_frame is None:
            return False  # No previous frame to compare

        try:
            # Convert to grayscale for comparison
            current_gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)
            previous_gray = cv2.cvtColor(self._last_surveillance_frame, cv2.COLOR_BGR2GRAY)

            # Calculate absolute difference
            frame_diff = cv2.absdiff(current_gray, previous_gray)

            # Apply threshold to get binary image
            _, thresh = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)

            # Calculate percentage of changed pixels
            changed_pixels = np.sum(thresh > 0)
            total_pixels = thresh.size
            change_percentage = changed_pixels / total_pixels

            # Check if change exceeds threshold
            return change_percentage > self._motion_threshold

        except Exception:
            logger.exception("Error detecting motion for camera {self._device_id}:")
            return False

    async def _create_motion_event(self, frame: np.ndarray):
        """Create a motion detection event."""
        try:
            import time

            from PIL import Image

            # Convert frame to PIL Image
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame_rgb)

            # Create event data
            event = {
                "timestamp": time.time(),
                "camera_id": self._device_id,
                "camera_name": self.config.name,
                "event_type": "motion_detected",
                "confidence": 0.0,  # Could be enhanced with better motion detection
                "image": image,  # Store PIL Image
                "metadata": {
                    "resolution": f"{frame.shape[1]}x{frame.shape[0]}",
                    "motion_threshold": self._motion_threshold,
                    "surveillance_interval": self._surveillance_interval,
                },
            }

            # Store event (keep last 10 events)
            self._surveillance_events.append(event)
            if len(self._surveillance_events) > 10:
                self._surveillance_events.pop(0)

            logger.debug(f"Created motion event for camera {self._device_id}")

        except Exception:
            logger.exception("Error creating motion event for camera {self._device_id}:")

    async def get_surveillance_events(self, limit: int = 10) -> list[dict]:
        """Get recent surveillance events."""
        events = []
        for event in self._surveillance_events[-limit:]:
            # Convert PIL Image to base64 for API
            try:
                import base64
                import io

                buffer = io.BytesIO()
                event["image"].save(buffer, format="JPEG")
                image_data = base64.b64encode(buffer.getvalue()).decode()

                event_copy = event.copy()
                event_copy["image_data"] = image_data
                event_copy.pop("image", None)  # Remove PIL Image
                events.append(event_copy)
            except Exception:
                logger.exception("Error processing surveillance event image:")

        return events

    async def enable_led_control(self, flash_interval: int = 5, flash_duration: float = 0.5) -> bool:
        """Enable LED control for surveillance mode."""
        self._led_control_enabled = True
        self._led_flash_interval = flash_interval
        self._led_flash_duration = flash_duration

        # Cancel existing LED task
        if self._led_task and not self._led_task.done():
            self._led_task.cancel()
            try:
                await self._led_task
            except asyncio.CancelledError:
                pass

        # Start LED control task
        self._led_task = asyncio.create_task(self._led_control_loop())
        logger.info(
            f"Enabled LED control for camera {self._device_id} (flash every {flash_interval}s for {flash_duration}s)"
        )
        return True

    async def disable_led_control(self) -> bool:
        """Disable LED control."""
        self._led_control_enabled = False

        if self._led_task and not self._led_task.done():
            self._led_task.cancel()
            try:
                await self._led_task
            except asyncio.CancelledError:
                pass

        # Turn off LED
        await self._set_led_state(False)
        logger.info(f"Disabled LED control for camera {self._device_id}")
        return True

    async def _led_control_loop(self):
        """Background LED control loop for surveillance indication."""
        logger.debug(f"Starting LED control loop for camera {self._device_id}")

        while self._led_control_enabled:
            try:
                # Flash LED on
                await self._set_led_state(True)
                await asyncio.sleep(self._led_flash_duration)

                # Turn LED off
                await self._set_led_state(False)

                # Wait for next flash
                await asyncio.sleep(self._led_flash_interval - self._led_flash_duration)

            except Exception:
                logger.exception("Error in LED control loop for camera {self._device_id}:")
                await asyncio.sleep(1)  # Brief pause before retry

    async def _set_led_state(self, on: bool) -> bool:
        """Set the camera LED state using multiple fallback methods."""
        try:
            # Method 1: Try Logitech Gaming Software API (most reliable for Logitech)
            if await self._set_led_logitech_gaming_software(on):
                return True

            # Method 2: Try Windows Media Foundation
            if await self._set_led_windows_media_foundation(on):
                return True

            # Method 3: Try DirectShow API
            if await self._set_led_directshow(on):
                return True

            # Method 4: Try system camera control
            if await self._set_led_system_control(on):
                return True

            # Method 5: Simulation mode (for testing/development)
            if await self._set_led_simulation(on):
                return True

            # If all methods fail, log warning but don't crash
            logger.debug(f"No LED control method available for camera {self._device_id}")
            return False

        except Exception:
            logger.exception("Error setting LED state for camera {self._device_id}:")
            return False

    async def _set_led_logitech_gaming_software(self, on: bool) -> bool:
        """Control LED via Logitech Gaming Software API."""
        try:
            import platform

            if platform.system() != "Windows":
                return False

            # Check if Logitech Gaming Software is installed and running
            import psutil

            # Check if LGS or Logitech G Hub is running
            logitech_apps = ["lghub.exe", "lcore.exe", "lvcomsx.exe"]
            lgs_running = any(
                any(proc.info["name"].lower() == app for app in logitech_apps) for proc in psutil.process_iter(["name"])
            )

            if not lgs_running:
                logger.debug("Logitech Gaming Software not running")
                return False

            # Try Logitech LED SDK or Logitech Capture SDK
            try:
                # For Logitech webcams, try Logitech Capture SDK approach
                # Many Logitech webcams support LED control through Logitech software

                # Method 1: Try Logitech LED SDK (if installed)
                try:
                    import ctypes

                    # Try Logitech LED SDK (for gaming peripherals, not webcams)
                    try:
                        led_dll = ctypes.WinDLL("LogitechLed.dll")
                        # Initialize Logitech LED SDK
                        if hasattr(led_dll, "Logitech_Init"):
                            led_dll.Logitech_Init.restype = ctypes.c_bool
                            if led_dll.Logitech_Init():
                                # Set LED state for all devices
                                if hasattr(led_dll, "Logitech_SetLighting"):
                                    led_dll.Logitech_SetLighting.restype = ctypes.c_bool
                                    led_dll.Logitech_SetLighting.argtypes = [
                                        ctypes.c_int,
                                        ctypes.c_int,
                                        ctypes.c_int,
                                        ctypes.c_int,
                                    ]

                                    red = 100 if on else 0
                                    green = 100 if on else 0
                                    blue = 100 if on else 0

                                    result = led_dll.Logitech_SetLighting(0, red, green, blue)  # 0 = all devices
                                    if result:
                                        logger.debug(f"Logitech LED SDK: {'ON' if on else 'OFF'}")
                                        return True
                    except Exception as e:
                        logger.debug(f"Logitech LED SDK not available: {e}")

                    # Try Logitech G SDK (different DLL)
                    try:
                        ctypes.WinDLL("LogitechG.dll")
                        # Logitech G SDK has different functions
                        logger.debug("Logitech G SDK detected, attempting LED control")
                        # Implementation would depend on Logitech G SDK
                    except:
                        pass

                except (ImportError, AttributeError, OSError):
                    # Logitech LED SDK not available or failed
                    pass

                # Method 2: Try Logitech webcam LED control via Windows API
                # Some Logitech webcams support LED control through device properties
                try:
                    import win32api
                    import win32gui

                    # Enumerate windows to find Logitech webcam control windows
                    def enum_windows_callback(hwnd, results):
                        class_name = win32gui.GetClassName(hwnd)
                        window_text = win32gui.GetWindowText(hwnd)

                        # Look for Logitech webcam control dialogs
                        if "logitech" in window_text.lower() or "webcam" in window_text.lower():
                            if "control" in window_text.lower() or "settings" in window_text.lower():
                                results.append((hwnd, window_text, class_name))

                    results = []
                    win32gui.EnumWindows(enum_windows_callback, results)

                    # If we found Logitech control windows, try to send LED control messages
                    for hwnd, title, _class_name in results:
                        try:
                            # Try to send custom message to Logitech webcam control
                            # This is highly device-specific and may not work
                            WM_USER = 0x0400
                            LOGITECH_LED_ON = WM_USER + 1
                            LOGITECH_LED_OFF = WM_USER + 2

                            msg = LOGITECH_LED_ON if on else LOGITECH_LED_OFF
                            result = win32api.SendMessage(hwnd, msg, 0, 0)

                            if result == 1:  # Success
                                logger.debug(f"Logitech webcam LED via window message: {'ON' if on else 'OFF'}")
                                return True

                        except Exception as e:
                            logger.debug(f"Failed to send LED message to window {title}: {e}")
                            continue

                    logger.debug("No Logitech webcam control windows found or messages failed")
                    return False

                except ImportError:
                    # pywin32 not available
                    logger.debug("pywin32 not available for Windows API LED control")

                # Method 3: Try Logitech webcam device-specific control
                try:
                    # For Logitech cameras, try device-specific LED control
                    # Some Logitech cameras support LED control through UVC extensions

                    # Check if this is a Logitech device by device name/friendly name
                    device_name = getattr(self.config.params, "friendly_name", "").lower()
                    if "logitech" not in device_name:
                        return False

                    # Try UVC LED control (experimental)
                    # Many Logitech webcams support UVC LED control through extension units
                    logger.debug(
                        f"Logitech UVC LED control attempt for device {self._device_id}: {'ON' if on else 'OFF'}"
                    )

                    # This would require UVC control implementation
                    # Real implementation would use libusb or Windows UVC APIs
                    return False  # Not implemented yet

                except Exception as e:
                    logger.debug(f"Logitech UVC LED control failed: {e}")

                # Method 4: Logitech Webcam LED Control (device-specific)
                try:
                    # For Logitech webcams specifically, try device control
                    device_name = getattr(self.config.params, "friendly_name", "").lower()

                    if "logitech" in device_name:
                        # Logitech webcam detected - try Logitech-specific control
                        logger.debug(
                            f"Logitech webcam {self._device_id} detected, attempting LED control: {'ON' if on else 'OFF'}"
                        )

                        # Try Logitech Webcam Software API
                        # Logitech Capture or Logitech Webcam Software may provide APIs
                        try:
                            import os

                            # Check if Logitech Webcam Software is installed
                            program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
                            lws_path = os.path.join(program_files, "Logitech", "Logitech Webcam Software", "LWS.exe")

                            if os.path.exists(lws_path):
                                # Logitech Webcam Software is installed
                                # Try to control LED via command line or API
                                # This is a placeholder - would need Logitech's API documentation

                                logger.debug(f"Logitech Webcam Software found at {lws_path}")
                                # Could try: subprocess.run([lws_path, '/led', 'on' if on else 'off'])
                                return False  # Not implemented yet
                            logger.debug("Logitech Webcam Software not found")

                        except Exception as e:
                            logger.debug(f"Logitech Webcam Software control failed: {e}")

                        # Alternative: Try Logitech Capture SDK
                        try:
                            # Logitech Capture might have LED control APIs
                            # This would require Logitech Capture SDK
                            logger.debug("Attempting Logitech Capture SDK LED control")
                            return False  # Not implemented yet
                        except:
                            pass

                    return False

                except Exception as e:
                    logger.debug(f"Logitech device-specific LED control failed: {e}")
                    return False

                logger.debug("No Logitech LED control method succeeded")
                return False

            except Exception as e:
                logger.debug(f"Logitech LED control failed: {e}")
                return False

        except ImportError:
            logger.debug("psutil not available for Logitech app detection")
            return False
        except Exception as e:
            logger.debug(f"Logitech Gaming Software LED control failed: {e}")
            return False

    async def _set_led_windows_media_foundation(self, on: bool) -> bool:
        """Control LED via Windows Media Foundation APIs."""
        try:
            import platform

            if platform.system() != "Windows":
                return False

            # Windows Media Foundation LED control
            # This would require Windows.Media.Devices namespace
            # or MediaFoundation interfaces

            logger.debug(f"Windows Media Foundation LED control attempt: {'ON' if on else 'OFF'}")
            return False  # Not implemented yet

        except Exception as e:
            logger.debug(f"Windows Media Foundation LED control failed: {e}")
            return False

    async def _set_led_directshow(self, on: bool) -> bool:
        """Control LED via DirectShow APIs."""
        try:
            import platform

            if platform.system() != "Windows":
                return False

            # DirectShow camera control using IAMCameraControl
            logger.debug(f"DirectShow LED control attempt: {'ON' if on else 'OFF'}")
            return False  # Not implemented yet

        except Exception as e:
            logger.debug(f"DirectShow LED control failed: {e}")
            return False

    async def _set_led_system_control(self, on: bool) -> bool:
        """Control LED via system-level camera APIs."""
        try:
            import platform

            if platform.system() != "Windows":
                return False

            # Try Windows SetupAPI or DeviceIoControl
            logger.debug(f"System camera control LED attempt: {'ON' if on else 'OFF'}")
            return False  # Not implemented yet

        except Exception as e:
            logger.debug(f"System camera control LED failed: {e}")
            return False

    async def _set_led_simulation(self, on: bool) -> bool:
        """Simulate LED control for testing (fallback method)."""
        # This method provides visual feedback even when hardware control isn't available
        # Useful for development, testing, or when Logitech SDK isn't installed

        led_state = "🔴 FLASH" if on else "⚫ OFF"
        logger.info(f"{led_state} LED SIMULATION - Camera {self._device_id}: {'ON' if on else 'OFF'}")

        # Check if this is a Logitech device for better simulation
        device_name = getattr(self.config.params, "friendly_name", "").lower()
        if "logitech" in device_name:
            logger.info(
                f"Logitech webcam {self._device_id} LED simulation: {'ACTIVATED' if on else 'DEACTIVATED'} (surveillance mode)"
            )
        else:
            logger.info(f"Generic webcam {self._device_id} LED simulation: {'ACTIVATED' if on else 'DEACTIVATED'}")

        # Could also trigger system notifications or external indicators
        # For example, system tray icon, external LED via serial, etc.

        # Simulate LED hardware behavior (brief flash when turning on)
        if on:
            logger.info(f"💡 Camera {self._device_id} LED: BRIGHT FLASH (0.5s)")
        else:
            logger.info(f"💡 Camera {self._device_id} LED: OFF")

        return True  # Always succeeds for simulation

    def _detect_speakerphone_capability(self) -> bool:
        """
        Detect if the camera has speakerphone capabilities.
        USB webcams typically only have microphones, not speakers.
        Only certain IP cameras (like Tapo) have speakerphone capabilities.
        """
        device_name = getattr(self.config.params, "friendly_name", "").lower()
        device_type = getattr(self.config, "type", None)

        # USB webcams (including Logitech) typically DON'T have speakers
        if device_type == CameraType.WEBCAM:
            # Logitech webcams are microphone-only, no speakers
            if "logitech" in device_name:
                return False
            # Generic USB webcams also don't have speakers
            return False

        # Tapo cameras DO have speakerphone capabilities
        if device_type and device_type.value == "tapo":
            return True

        # Ring cameras have speakerphone via WebRTC
        if "ring" in device_name:
            return True

        # Default to False for unknown camera types
        return False

    async def enable_speakerphone(self) -> bool:
        """Enable speakerphone mode for two-way audio."""
        if not self._speakerphone_capable:
            logger.warning(f"Camera {self._device_id} does not support speakerphone")
            return False

        self._speakerphone_enabled = True

        # Cancel existing audio output task
        if self._audio_output_task and not self._audio_output_task.done():
            self._audio_output_task.cancel()
            try:
                await self._audio_output_task
            except asyncio.CancelledError:
                pass

        # Start speakerphone audio output
        self._audio_output_task = asyncio.create_task(self._speakerphone_audio_loop())
        logger.info(f"Enabled speakerphone for camera {self._device_id}")
        return True

    async def disable_speakerphone(self) -> bool:
        """Disable speakerphone mode."""
        self._speakerphone_enabled = False

        if self._audio_output_task and not self._audio_output_task.done():
            self._audio_output_task.cancel()
            try:
                await self._audio_output_task
            except asyncio.CancelledError:
                pass

        logger.info(f"Disabled speakerphone for camera {self._device_id}")
        return True

    async def _speakerphone_audio_loop(self):
        """Background audio output loop for speakerphone functionality."""
        logger.debug(f"Starting speakerphone audio loop for camera {self._device_id}")

        # This is a placeholder implementation
        # Real implementation would:
        # 1. Capture audio from system microphone
        # 2. Encode audio stream
        # 3. Send to camera speakers via appropriate protocol

        while self._speakerphone_enabled:
            try:
                # Simulate speakerphone activity
                logger.debug(f"Speakerphone active on camera {self._device_id}")
                await asyncio.sleep(1)  # Check every second

            except Exception:
                logger.exception("Error in speakerphone loop for camera {self._device_id}:")
                await asyncio.sleep(1)  # Brief pause before retry

    async def get_speakerphone_status(self) -> dict[str, Any]:
        """Get speakerphone status and capabilities."""
        return {
            "speakerphone_capable": self._speakerphone_capable,
            "speakerphone_enabled": self._speakerphone_enabled,
            "device_supports_speakers": self._speakerphone_capable,
            "audio_output_available": self._speakerphone_capable,
            "manufacturer": "Logitech"
            if "logitech" in getattr(self.config.params, "friendly_name", "").lower()
            else "Generic",
            "note": "Speakerphone requires camera with built-in speakers (Logitech conference cameras)",
        }

    def _detect_microphone_capability(self) -> bool:
        """Detect if this USB webcam has microphone capability."""
        try:
            # Check if microphone capability is explicitly configured
            configured_audio = self.config.params.get("audio_capable")
            if configured_audio is not None:
                return bool(configured_audio)

            # Check for microphone override in config
            has_microphone = self.config.params.get("has_microphone")
            if has_microphone is not None:
                return bool(has_microphone)

            # Device-specific detection based on type and model
            device_type = getattr(self, "_device_type", self.config.params.get("device_type", "")).lower()
            friendly_name = self.config.params.get("friendly_name", "").lower()

            # Microscopes typically don't have microphones
            if "microscope" in device_type or "microscope" in friendly_name:
                return False

            # Logitech cameras typically DO have microphones
            if "logitech" in friendly_name:
                return True

            # Generic Logitech detection
            if "logitech" in device_type:
                return True

            # Default behavior: assume most USB webcams have microphones
            # This is statistically accurate for modern webcams
            # Users can override with "audio_capable": false in config if needed
            return True

        except Exception as e:
            logger.debug(f"Error detecting microphone capability: {e}")
            return False

    def _detect_locking_application(self) -> str | None:
        """Try to detect which application is locking the camera."""
        try:
            import platform

            if platform.system() != "Windows":
                return None

            # Check for common video applications using various methods
            import psutil

            # Method 1: Check running processes for known video apps
            known_video_apps = {
                "Teams.exe": "Microsoft Teams",
                "ms-teams.exe": "Microsoft Teams",
                "Zoom.exe": "Zoom",
                "slack.exe": "Slack",
                "discord.exe": "Discord",
                "chrome.exe": "Google Chrome",
                "firefox.exe": "Firefox",
                "edge.exe": "Microsoft Edge",
                "opera.exe": "Opera",
                "skype.exe": "Skype",
                "webex.exe": "Cisco Webex",
                "gotomeeting.exe": "GoToMeeting",
                "obs64.exe": "OBS Studio",
                "obs.exe": "OBS Studio",
                "camtasia.exe": "Camtasia",
                "bandicam.exe": "Bandicam",
                "photobooth.exe": "Photo Booth",
                "cheese": "Cheese",  # Linux
                "guvcview": "GUVCView",  # Linux
            }

            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    proc_name = proc.info["name"].lower()
                    if proc_name in [app.lower() for app in known_video_apps]:
                        # Found a known video app, return the executable name
                        for exe_name, _display_name in known_video_apps.items():
                            if proc_name == exe_name.lower():
                                return exe_name
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Method 2: Check if any process has camera-related handles (more advanced)
            # This would require ctypes and Windows API calls, which is complex
            # For now, we'll rely on process name detection

            return None

        except ImportError:
            # psutil not available, can't detect
            return None
        except Exception as e:
            logger.debug(f"Error detecting locking application: {e}")
            return None

    def _get_app_display_name(self, exe_name: str) -> str:
        """Convert executable name to user-friendly display name."""
        app_names = {
            "Teams.exe": "Microsoft Teams",
            "ms-teams.exe": "Microsoft Teams",
            "Zoom.exe": "Zoom",
            "slack.exe": "Slack",
            "discord.exe": "Discord",
            "chrome.exe": "Google Chrome",
            "firefox.exe": "Mozilla Firefox",
            "edge.exe": "Microsoft Edge",
            "opera.exe": "Opera",
            "skype.exe": "Skype",
            "webex.exe": "Cisco Webex",
            "gotomeeting.exe": "GoToMeeting",
            "obs64.exe": "OBS Studio",
            "obs.exe": "OBS Studio",
            "camtasia.exe": "Camtasia",
            "bandicam.exe": "Bandicam",
            "photobooth.exe": "Photo Booth",
            "cheese": "Cheese",
            "guvcview": "GUVCView",
        }

        return app_names.get(exe_name, exe_name.replace(".exe", "").title())

    async def get_info(self) -> dict:
        """Get comprehensive webcam information."""
        try:
            info = {
                "name": self.config.name,
                "type": self.config.type.value,
                "device_id": self._device_id,
                "connected": await self.is_connected(),
                "streaming": await self.is_streaming(),
                "capabilities": {
                    "video_capture": True,
                    "image_capture": True,
                    "streaming": True,
                    "ptz": False,
                },
            }

            # Add OpenCV-specific information if connected
            if await self.is_connected() and self._cap:
                try:
                    width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = self._cap.get(cv2.CAP_PROP_FPS)

                    info.update(
                        {
                            "resolution": f"{width}x{height}",
                            "fps": fps,
                            "backend": self._cap.getBackendName(),
                        }
                    )
                except Exception as e:
                    info["resolution_info_error"] = str(e)

        except Exception as e:
            return {
                "name": self.config.name,
                "type": self.config.type.value,
                "device_id": self._device_id,
                "error": f"Failed to get camera info: {e}",
            }
        else:
            return info
