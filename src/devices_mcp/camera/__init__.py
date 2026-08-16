"""Camera module imports."""

import logging
import os

logger = logging.getLogger(__name__)

from .laptop import LaptopCamera
from .onvif_camera import ONVIFBasedCamera
from .petcube import PetcubeCamera
from .public_webcam import PublicWebcam
from .tapo import TapoCamera

# The Windows webcam proxy exists so Linux Docker containers can reach USB cameras on
# the Windows host (it requires scripts/windows_camera_server.py on port 10715). On
# native Windows without the helper running, proxy cameras would never connect - so
# only use the proxy when the helper URL is explicitly configured.
_USE_WINDOWS_CAMERA_PROXY = bool(os.environ.get("WINDOWS_CAMERA_SERVER_URL")) or os.environ.get(
    "DEVICES_MCP_WINDOWS_CAMERA_PROXY", ""
).lower() in ("1", "true", "yes")

if _USE_WINDOWS_CAMERA_PROXY:
    try:
        from .windows_webcam import (
            WindowsMicroscopeCamera as MicroscopeCamera,
        )
        from .windows_webcam import (
            WindowsWebCamera as WebCamera,
        )

        logger.info("Using Windows webcam proxy implementation")
    except ImportError as e:
        logger.warning(f"Failed to import Windows webcam proxy, falling back to standard: {e}")
        from .microscope import MicroscopeCamera
        from .webcam import WebCamera
else:
    logger.info("Using direct OpenCV webcam implementation (no WINDOWS_CAMERA_SERVER_URL set)")
    from .microscope import MicroscopeCamera
    from .webcam import WebCamera

logger = logging.getLogger(__name__)

# Import RingCamera with error handling
try:
    # Apply patch before importing ring module
    try:
        from .. import patch_ring_doorbell

        patch_ring_doorbell.patch_ring_doorbell()
    except Exception as e:
        logger.warning(f"Failed to apply ring_doorbell patch: {e}")

    from .ring import RingCamera

    RING_AVAILABLE = True
except Exception as e:
    logger.warning(f"Failed to import RingCamera: {e}")
    RING_AVAILABLE = False
    RingCamera = None  # type: ignore[assignment,misc]

__all__ = [
    "LaptopCamera",
    "MicroscopeCamera",
    "ONVIFBasedCamera",
    "PetcubeCamera",
    "PublicWebcam",
    "TapoCamera",
    "WebCamera",
]

# Only add RingCamera to __all__ if it's available
if RING_AVAILABLE:
    __all__.append("RingCamera")
