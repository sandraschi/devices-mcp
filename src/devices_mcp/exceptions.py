"""
Exception classes for devices-mcp.
"""


class TapoCameraError(Exception):
    """Base exception for all Devices MCP errors."""


class AuthenticationError(TapoCameraError):
    """Raised when authentication with the camera fails."""


class ConnectionError(TapoCameraError):
    """Raised when there is a connection error with the camera."""


class CameraBusyError(TapoCameraError):
    """Raised when the camera is busy with another operation."""


class CameraNotSupportedError(TapoCameraError):
    """Raised when a feature is not supported by the camera."""


class StreamError(TapoCameraError):
    """Raised when there is an error with the video stream."""


class PTZError(TapoCameraError):
    """Raised when there is an error with PTZ operations."""


class StorageError(TapoCameraError):
    """Raised when there is an error accessing camera storage."""


class ConfigurationError(TapoCameraError):
    """Raised when there is an error with the camera configuration."""


class TimeoutError(TapoCameraError):
    """Raised when an operation times out."""


class FirmwareError(TapoCameraError):
    """Raised when there is a firmware-related error."""
