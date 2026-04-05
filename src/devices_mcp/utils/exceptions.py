"""
Custom exceptions for the Devices MCP.
"""


class TapoCameraError(Exception):
    """Base exception for all Devices MCP errors."""


class CameraConnectionError(TapoCameraError):
    """Raised when there's an error connecting to or communicating with a camera."""


class CameraAuthError(TapoCameraError):
    """Raised when authentication with a camera fails."""


class CameraNotSupportedError(TapoCameraError):
    """Raised when a requested feature is not supported by the camera."""


class ConfigurationError(TapoCameraError):
    """Raised when there's an error in the configuration."""


class ValidationError(TapoCameraError):
    """Raised when input validation fails."""


class ResourceNotFoundError(TapoCameraError):
    """Raised when a requested resource is not found."""


class OperationNotPermittedError(TapoCameraError):
    """Raised when an operation is not permitted."""


class RateLimitExceededError(TapoCameraError):
    """Raised when API rate limits are exceeded."""


class TimeoutError(TapoCameraError):
    """Raised when an operation times out."""


class StorageError(TapoCameraError):
    """Raised when there's an error with storage operations."""


class StreamError(TapoCameraError):
    """Raised when there's an error with video streaming."""
