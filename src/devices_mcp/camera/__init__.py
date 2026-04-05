"""Camera module imports."""

import logging

logger = logging.getLogger(__name__)

from .laptop import LaptopCamera
from .onvif_camera import ONVIFBasedCamera
from .petcube import PetcubeCamera
from .public_webcam import PublicWebcam
from .tapo import TapoCamera

# Use Windows webcam proxy implementation for Docker containers
# This allows USB cameras on Windows host to be accessed from Linux Docker containers
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
