"""
devices-mcp - A FastMCP 3.1+ server for controlling home security devices.

This package provides a FastMCP 3.1+ compliant server for interacting with
home security devices, including TP-Link Tapo cameras, Ring doorbells,
and Nest Protect sensors/smoke detectors.
"""

__version__ = "1.18.0"
__author__ = "Devices MCP Team <devices-mcp@example.com>"
__license__ = "MIT"

# Import compatibility shims FIRST, before any pytapo imports
from . import (
    compat,  # noqa: F401
    presets,
)

# Import core components
from .core import (
    CameraInfo,
    CameraModel,
    CameraStatus,
    DevicesMCPServer,
    MotionDetectionSensitivity,
    MotionEvent,
    PTZDirection,
    PTZPosition,
    StreamType,
    VideoQuality,
    get_server,
)
from .core.server import DevicesMCPServer as TapoCameraMCP

# For backward compatibility
from .core.server import DevicesMCPServer as TapoCameraServer
from .exceptions import TapoCameraError

__all__ = [
    "CameraInfo",
    # Models
    "CameraModel",
    "CameraStatus",
    # Core components
    "DevicesMCPServer",
    "MotionDetectionSensitivity",
    "MotionEvent",
    "PTZDirection",
    "PTZPosition",
    "StreamType",
    "TapoCameraError",
    "TapoCameraMCP",  # For backward compatibility
    "TapoCameraServer",  # For backward compatibility
    "TapoWebServer",
    "VideoQuality",
    "get_server",
    "presets",
]
