"""
Core functionality for the Devices MCP server.
"""

from .models import (
    CameraInfo,
    CameraModel,
    CameraStatus,
    MotionDetectionSensitivity,
    MotionEvent,
    PTZDirection,
    PTZPosition,
    StreamType,
    VideoQuality,
)
from .server import DevicesMCPServer, get_server

# For backward compatibility
TapoCameraServer = DevicesMCPServer

__all__ = [
    "CameraInfo",
    "CameraModel",
    "CameraStatus",
    "DevicesMCPServer",
    "MotionDetectionSensitivity",
    "MotionEvent",
    "PTZDirection",
    "PTZPosition",
    "StreamType",
    "TapoCameraServer",  # For backward compatibility
    "VideoQuality",
    "get_server",
]
