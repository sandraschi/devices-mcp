"""
Core module for Ring MCP.

Contains the Ring API client, exception classes, and core utilities.
"""

from .exceptions import (
    ApiRateLimitError,
    AuthenticationError,
    DeviceNotFoundError,
    DeviceOfflineError,
    InvalidConfigurationError,
    RingError,
    StreamingError,
)
from .ring_client import RingClient

__all__ = [
    "ApiRateLimitError",
    "AuthenticationError",
    "DeviceNotFoundError",
    "DeviceOfflineError",
    "InvalidConfigurationError",
    "RingClient",
    "RingError",
    "StreamingError",
]
