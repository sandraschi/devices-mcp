"""
Custom exceptions for the Nest Protect MCP server.
"""


class NestProtectError(Exception):
    """Base exception for all Nest Protect MCP errors."""


class NestAuthError(NestProtectError):
    """Raised when there's an authentication or authorization error with the Nest API."""


class NestConnectionError(NestProtectError):
    """Raised when there's a connection error with the Nest API or devices."""


class NestDeviceNotFoundError(NestProtectError):
    """Raised when a requested device is not found."""


class NestDeviceOfflineError(NestProtectError):
    """Raised when trying to communicate with an offline device."""


class NestInvalidCommandError(NestProtectError):
    """Raised when an invalid command is sent to a device."""


class NestRateLimitExceededError(NestProtectError):
    """Raised when the rate limit for the Nest API is exceeded."""


class NestConfigError(NestProtectError):
    """Raised when there's an error in the configuration."""


class NestMQTTError(NestProtectError):
    """Raised when there's an error with MQTT communication."""


class NestUpdateError(NestProtectError):
    """Raised when there's an error updating device state."""


class NestTestError(NestProtectError):
    """Raised when there's an error during a device test."""


class NestHushError(NestProtectError):
    """Raised when there's an error hushing an alarm."""
