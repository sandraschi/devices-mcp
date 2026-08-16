"""Camera manager for handling multiple camera types and groups."""

import logging
from pathlib import Path
from typing import Any

from .base import CameraConfig, CameraFactory
from .groups import CameraGroupManager

logger = logging.getLogger(__name__)

# DirectShow friendly-name markers for virtual/synthetic cameras that enumerate as
# fake capture devices (NVIDIA Broadcast, OBS, Immersed, NDI, ...). Auto-discovery
# must skip them, otherwise the webapp shows phantom cameras that never deliver frames.
_VIRTUAL_CAMERA_MARKERS = (
    "virtual",
    "broadcast",
    "immersed",
    "obs",
    "spout",
    "ndi",
    "remote desktop",
    "mirror",
    "unitycapture",
    "streamlabs",
    "splitcam",
    "manycam",
    "ecamm",
    "webcamoid",
    "camtwist",
    "epoccam",
    "droidcam",
    "vcam",
)


def _get_dshow_device_names() -> dict[int, str]:
    """Map DirectShow index -> friendly name (best effort; {} when pygrabber is missing)."""
    try:
        from pygrabber.dshow_graph import FilterGraph

        return {i: name for i, name in enumerate(FilterGraph().get_input_devices())}
    except Exception:
        return {}


def _is_virtual_camera_device(device_index: int, device_names: dict[int, str]) -> bool:
    """True if the DirectShow device at device_index looks like a virtual/synthetic camera."""
    name = (device_names.get(device_index) or "").lower()
    return any(marker in name for marker in _VIRTUAL_CAMERA_MARKERS)


class CameraManager:
    """Manages multiple camera instances and groups."""

    def __init__(self):
        self.cameras: dict[str, Any] = {}
        self._initialized = False
        self.groups = CameraGroupManager()

    async def initialize(self, configs: list[dict] | None = None, auto_discover_usb: bool = True) -> None:
        """Initialize camera manager with configuration and optional USB camera discovery.

        Args:
            configs: List of camera configurations
            auto_discover_usb: Whether to automatically discover and add USB cameras
        """
        if self._initialized:
            return

        if configs:
            for cfg in configs:
                await self.add_camera(cfg)

        # Auto-discover USB cameras if requested
        if auto_discover_usb:
            await self._auto_discover_usb_cameras()

        self._initialized = True

    async def _auto_discover_usb_cameras(self) -> None:
        """Automatically discover and add USB cameras."""
        try:
            # Suppress OpenCV warnings
            import os
            import platform

            import cv2

            os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
            cv2.setLogLevel(0)

            logger.info("Auto-discovering USB cameras...")

            discovered_cameras = []
            max_devices = 10

            # Scan for available cameras (Windows: CAP_DSHOW matches streaming.py / most UVC drivers)
            for device_id in range(max_devices):
                try:
                    if platform.system() == "Windows":
                        cap = cv2.VideoCapture(device_id, cv2.CAP_DSHOW)
                    else:
                        cap = cv2.VideoCapture(device_id, cv2.CAP_ANY)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                            discovered_cameras.append(
                                {
                                    "device_id": device_id,
                                    "resolution": f"{width}x{height}",
                                    "backend": cap.getBackendName(),
                                }
                            )

                            logger.info(f"Auto-discovered USB camera at device {device_id}: {width}x{height}")
                        cap.release()
                except Exception as e:
                    logger.debug(f"Error checking camera device {device_id}: {e}")
                    continue

            # Collect device IDs already configured (from config.yaml configs)
            configured_device_ids: set[int] = set()
            for _, cinst in self.cameras.items():
                try:
                    params = getattr(cinst, "config", None)
                    if params is None:
                        continue
                    params = params.params if hasattr(params, "params") else {}
                    did = int(params.get("device_id", -1))
                    if did >= 0:
                        configured_device_ids.add(did)
                except (ValueError, TypeError, AttributeError):
                    pass

            common_names = [
                "Built-in Camera",
                "USB Webcam",
                "External Camera",
                "Document Camera",
                "Microscope Camera",
            ]

            # Map DSHOW indices to friendly names once, so virtual cameras (NVIDIA
            # Broadcast, OBS, Immersed, ...) can be skipped below.
            device_names = _get_dshow_device_names()

            for i, camera_info in enumerate(discovered_cameras):
                device_id = camera_info["device_id"]

                # Skip device IDs already configured in config.yaml
                if device_id in configured_device_ids:
                    logger.debug(f"USB camera device {device_id} already configured, skipping auto-discovery")
                    continue

                camera_name = f"usb_camera_{device_id}"

                # Skip if already configured by name
                if camera_name in self.cameras:
                    logger.debug(f"USB camera {camera_name} already configured, skipping")
                    continue

                # Skip virtual cameras - they are not real hardware and only produce
                # phantom entries that show connection errors in the webapp.
                if _is_virtual_camera_device(device_id, device_names):
                    logger.info(
                        "Skipping virtual camera at device %s: %s",
                        device_id,
                        device_names.get(device_id, "?"),
                    )
                    continue

                # Classify device type based on resolution and capabilities
                resolution = camera_info["resolution"]
                fps = camera_info.get("fps", 30)
                device_type = self._classify_camera_device_type(resolution, fps, device_id)

                # Determine microphone capability
                has_microphone = self._detect_camera_microphone(device_type, resolution, device_id)

                # Create configuration
                config = {
                    "name": camera_name,
                    "type": "webcam",
                    "params": {
                        "device_id": device_id,
                        "resolution": camera_info["resolution"],
                        "device_type": device_type,
                        "auto_discovered": True,
                        "friendly_name": common_names[min(i, len(common_names) - 1)],
                        "audio_capable": has_microphone,
                    },
                    "enabled": True,
                }

                # Add the camera
                success = await self.add_camera(config)
                if success:
                    logger.info(f"Auto-added USB camera: {camera_name} (device {device_id})")
                else:
                    logger.warning(f"Failed to auto-add USB camera: {camera_name}")

            if discovered_cameras:
                logger.info(f"Auto-discovery complete: found {len(discovered_cameras)} USB camera(s)")
            else:
                logger.info("Auto-discovery complete: no USB cameras found")

        except ImportError:
            logger.warning("OpenCV not available, skipping USB camera auto-discovery")
        except Exception:
            logger.exception("Error during USB camera auto-discovery")

    def _classify_camera_device_type(self, resolution: str, fps: float, device_id: int) -> str:
        """Classify camera device type based on resolution and capabilities."""
        try:
            if "Unknown" in resolution:
                return "webcam"  # Default fallback

            # Parse resolution
            width, height = map(int, resolution.split("x"))

            # Microscope cameras often have higher resolutions and lower FPS
            if width >= 1280 and height >= 720 and fps <= 15:
                return "microscope"
            if width >= 1920 and height >= 1080:
                return "webcam_hd"
            if width <= 640 and height <= 480:
                return "webcam_sd"
            return "webcam"

        except (ValueError, AttributeError):
            return "webcam"  # Default fallback

    def _detect_camera_microphone(self, device_type: str, resolution: str, device_id: int) -> bool:
        """Detect if a camera likely has a microphone based on type and characteristics."""
        device_type_lower = device_type.lower()

        # Microscopes typically don't have microphones
        if "microscope" in device_type_lower:
            return False

        # Logitech cameras (we can detect by trying to get device name later)
        # For now, assume most webcams have microphones unless they're microscopes
        return True

    async def start_camera_surveillance(
        self,
        camera_name: str,
        interval: int = 30,
        motion_threshold: float = 0.05,
        led_control: bool | None = None,
        led_flash_interval: int | None = None,
        led_flash_duration: float | None = None,
    ) -> bool:
        """Start surveillance mode for a camera."""
        camera = await self.get_camera(camera_name)
        if not camera:
            logger.error(f"Camera {camera_name} not found for surveillance")
            return False

        # Check if camera supports surveillance (USB webcams do)
        if not hasattr(camera, "start_surveillance"):
            logger.error(f"Camera {camera_name} does not support surveillance mode")
            return False

        return await camera.start_surveillance(
            interval, motion_threshold, led_control, led_flash_interval, led_flash_duration
        )

    async def enable_camera_led_control(
        self, camera_name: str, flash_interval: int = 5, flash_duration: float = 0.5
    ) -> bool:
        """Enable LED control for a camera."""
        camera = await self.get_camera(camera_name)
        if not camera:
            logger.error(f"Camera {camera_name} not found for LED control")
            return False

        if not hasattr(camera, "enable_led_control"):
            logger.error(f"Camera {camera_name} does not support LED control")
            return False

        return await camera.enable_led_control(flash_interval, flash_duration)

    async def disable_camera_led_control(self, camera_name: str) -> bool:
        """Disable LED control for a camera."""
        camera = await self.get_camera(camera_name)
        if not camera:
            logger.error(f"Camera {camera_name} not found for LED control disable")
            return False

        if not hasattr(camera, "disable_led_control"):
            logger.warning(f"Camera {camera_name} does not have LED control to disable")
            return False

        return await camera.disable_led_control()

    async def enable_camera_speakerphone(self, camera_name: str) -> bool:
        """Enable speakerphone for a camera."""
        camera = await self.get_camera(camera_name)
        if not camera:
            logger.error(f"Camera {camera_name} not found for speakerphone")
            return False

        if not hasattr(camera, "enable_speakerphone"):
            logger.error(f"Camera {camera_name} does not support speakerphone")
            return False

        return await camera.enable_speakerphone()

    async def disable_camera_speakerphone(self, camera_name: str) -> bool:
        """Disable speakerphone for a camera."""
        camera = await self.get_camera(camera_name)
        if not camera:
            logger.error(f"Camera {camera_name} not found for speakerphone disable")
            return False

        if not hasattr(camera, "disable_speakerphone"):
            logger.warning(f"Camera {camera_name} does not have speakerphone to disable")
            return False

        return await camera.disable_speakerphone()

    async def get_camera_speakerphone_status(self, camera_name: str) -> dict[str, Any]:
        """Get speakerphone status for a camera."""
        camera = await self.get_camera(camera_name)
        if not camera:
            logger.error(f"Camera {camera_name} not found for speakerphone status")
            return {"speakerphone_capable": False, "error": "Camera not found"}

        if not hasattr(camera, "get_speakerphone_status"):
            return {"speakerphone_capable": False, "error": "Speakerphone not supported"}

        return await camera.get_speakerphone_status()

    async def stop_camera_surveillance(self, camera_name: str) -> bool:
        """Stop surveillance mode for a camera."""
        camera = await self.get_camera(camera_name)
        if not camera:
            logger.error(f"Camera {camera_name} not found for surveillance stop")
            return False

        if not hasattr(camera, "stop_surveillance"):
            logger.warning(f"Camera {camera_name} does not have surveillance to stop")
            return False

        return await camera.stop_surveillance()

    async def get_camera_surveillance_events(self, camera_name: str, limit: int = 10) -> list[dict]:
        """Get surveillance events for a camera."""
        camera = await self.get_camera(camera_name)
        if not camera:
            logger.error(f"Camera {camera_name} not found for surveillance events")
            return []

        if not hasattr(camera, "get_surveillance_events"):
            logger.warning(f"Camera {camera_name} does not support surveillance events")
            return []

        return await camera.get_surveillance_events(limit)

    async def add_camera(self, config: dict | CameraConfig) -> bool:
        """Add a new camera.

        Args:
            config: Camera configuration

        Returns:
            bool: True if camera was added successfully
        """
        try:
            if isinstance(config, dict):
                config = CameraConfig(**config)

            if config.name in self.cameras:
                logger.warning(f"Camera '{config.name}' already exists")
                return False

            # Create camera - add it even if connection fails initially
            # Connection will be retried when accessing stream/snapshot
            import asyncio

            camera = CameraFactory.create(config)

            # Try to connect, but don't fail if it times out
            try:
                # Reduced timeout to prevents server startup hang from slow cameras
                connected = await asyncio.wait_for(camera.connect(), timeout=2.0)
                logger.info(f"Camera {config.name} connected: {connected}")
            except TimeoutError:
                logger.warning(f"Camera {config.name} connection timed out (2s) - will retry on stream access")
                connected = False
                # Keep the (slow, e.g. ONVIF) connect running in the background. A
                # cancelled wait_for kills the coroutine before it can set the
                # connected state, and every later status check would restart the
                # cold handshake and get cancelled again - camera stays offline
                # forever. A detached connect task completes on its own.
                try:
                    asyncio.get_running_loop().create_task(camera.connect())
                except Exception:
                    logger.debug(f"Could not spawn background connect for {config.name}")
            except Exception as e:
                logger.warning(f"Camera {config.name} connection failed: {e} - will retry on stream access")
                connected = False

            # Add camera even if connection failed - it will retry when needed
            self.cameras[config.name] = camera
            logger.info(f"Added camera: {config.name} ({config.type}) - connected: {connected}")
            return True
        except Exception:
            logger.exception("Failed to add camera")
            return False

    async def remove_camera(self, name: str) -> bool:
        """Remove a camera.

        Args:
            name: Name of the camera to remove

        Returns:
            bool: True if camera was removed successfully
        """
        if name not in self.cameras:
            return False

        try:
            # Remove from all groups first
            self.groups.remove_camera(name)

            # Disconnect and remove camera
            await self.cameras[name].disconnect()
            del self.cameras[name]
        except Exception:
            logger.exception("Error removing camera")
            return False
        else:
            logger.info(f"Removed camera: {name}")
            return True

    async def get_camera(self, name: str):
        """Get a camera instance by name."""
        return self.cameras.get(name)

    async def list_cameras(self, group: str | None = None) -> list[dict]:
        """List all cameras and their status, optionally filtered by group.

        Args:
            group: Optional group name to filter cameras

        Returns:
            List of camera information dictionaries
        """
        camera_names = self.groups.get_group_cameras(group) if group else list(self.cameras.keys())

        import asyncio

        async def get_camera_info(name):
            if name not in self.cameras:
                return None

            camera = self.cameras[name]
            try:
                # Add timeout to prevent hanging on camera status checks
                status = await asyncio.wait_for(camera.get_status(), timeout=3.0)
                return {
                    "name": name,
                    "type": camera.config.type.value
                    if hasattr(camera.config.type, "value")
                    else str(camera.config.type),
                    "status": status,
                    "groups": self.groups.get_camera_groups(name),
                }
            except TimeoutError:
                logger.warning(f"Camera {name} status check timed out")
                return {
                    "name": name,
                    "type": camera.config.type.value
                    if hasattr(camera.config.type, "value")
                    else str(camera.config.type),
                    "status": {"connected": False, "error": "Status check timed out"},
                    "groups": self.groups.get_camera_groups(name),
                }
            except Exception as e:
                logger.exception("Error getting status for")
                return {
                    "name": name,
                    "error": str(e),
                    "groups": self.groups.get_camera_groups(name),
                }

        # Run checks in parallel
        results = await asyncio.gather(*[get_camera_info(name) for name in camera_names], return_exceptions=True)

        # Filter out None results and handle exceptions in results
        final_results = []
        for r in results:
            if isinstance(r, Exception):
                logger.error(f"Error in camera status check task: {r}")
                continue
            if r:
                final_results.append(r)

        return final_results

    async def capture_still(self, camera_name: str, save_path: str | Path | None = None) -> dict:
        """Capture a still image from a camera."""
        if camera_name not in self.cameras:
            return {"status": "error", "message": f"Camera not found: {camera_name}"}

        try:
            image = await self.cameras[camera_name].capture_still(save_path)
            return {
                "status": "success",
                "camera": camera_name,
                "image": image if not save_path else str(save_path),
            }
        except Exception as e:
            return {"status": "error", "camera": camera_name, "message": str(e)}

    # Group management methods
    async def add_camera_to_group(self, camera_name: str, group_name: str) -> bool:
        """Add a camera to a group.

        Args:
            camera_name: Name of the camera
            group_name: Name of the group

        Returns:
            bool: True if camera was added to group
        """
        if camera_name not in self.cameras:
            logger.warning(f"Camera {camera_name} not found")
            return False

        return self.groups.add_camera_to_group(camera_name, group_name)

    async def remove_camera_from_group(self, camera_name: str, group_name: str) -> bool:
        """Remove a camera from a group.

        Args:
            camera_name: Name of the camera
            group_name: Name of the group

        Returns:
            bool: True if camera was removed from group
        """
        return self.groups.remove_camera_from_group(camera_name, group_name)

    async def create_group(self, group_name: str) -> bool:
        """Create a new camera group.

        Args:
            group_name: Name of the group to create

        Returns:
            bool: True if group was created
        """
        return self.groups.create_group(group_name)

    async def delete_group(self, group_name: str) -> bool:
        """Delete a camera group.

        Args:
            group_name: Name of the group to delete

        Returns:
            bool: True if group was deleted
        """
        return self.groups.delete_group(group_name)

    async def list_groups(self) -> list[dict[str, Any]]:
        """List all camera groups with their cameras.

        Returns:
            List of group information dictionaries
        """
        groups = []
        for group_name in self.groups.list_groups():
            cameras = self.groups.get_group_cameras(group_name)
            groups.append({"name": group_name, "cameras": cameras, "camera_count": len(cameras)})
        return groups

    async def close(self):
        """Close all camera connections and clean up."""
        for name in list(self.cameras.keys()):
            await self.remove_camera(name)
        self._initialized = False


# Global instance
camera_manager = CameraManager()
