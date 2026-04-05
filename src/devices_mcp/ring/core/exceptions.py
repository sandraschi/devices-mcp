"""
Custom exceptions for Ring MCP operations.

This module provides specific exception types for different Ring API and operational errors.
"""

from typing import Optional


class RingError(Exception):
    """Base exception for Ring MCP operations."""

    def __init__(self, message: str = "An error occurred with Ring integration") -> None:
        self.message = message
        super().__init__(self.message)


class AuthenticationError(RingError):
    """Raised when Ring authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message)


class DeviceNotFoundError(RingError):
    """Raised when a Ring device cannot be found."""

    def __init__(self, device_id: Optional[str] = None) -> None:
        message = f"Device {device_id} not found" if device_id else "Device not found"
        super().__init__(message)


class StreamingError(RingError):
    """Raised when video/audio streaming operations fail."""

    def __init__(self, message: str = "Streaming operation failed") -> None:
        super().__init__(message)


class RateLimitError(RingError):
    """Raised when Ring API rate limits are exceeded.

    This is an alias for ApiRateLimitError for backward compatibility.
    """

    def __init__(self, message: str = "API rate limit exceeded") -> None:
        super().__init__(message)


class ApiRateLimitError(RateLimitError):
    """Raised when Ring API rate limits are exceeded."""


class DeviceOfflineError(RingError):
    """Raised when attempting to operate on offline devices."""

    def __init__(self, device_id: Optional[str] = None) -> None:
        message = f"Device {device_id} is offline" if device_id else "Device is offline"
        super().__init__(message)


class InvalidConfigurationError(RingError):
    """Raised when device configuration is invalid."""

    def __init__(self, message: str = "Invalid configuration") -> None:
        super().__init__(message)


class RingConnectionError(RingError):
    """Raised when there are connection issues with the Ring API."""

    def __init__(self, message: str = "Connection to Ring API failed") -> None:
        super().__init__(message)
