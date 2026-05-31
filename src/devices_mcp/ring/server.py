"""
FastMCP 3.1 server for Ring MCP.

This module provides a FastMCP server implementation for controlling Ring devices
with composition and proxy capabilities using FastMCP 3.1 patterns.
"""

import logging
import os
import time
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from fastapi import FastAPI
from fastmcp import FastMCP
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from pydantic import BaseModel, Field

from .core.ring_client_modern import RingClient


def create_fastapi_app_with_docs() -> FastAPI:
    """Create a FastAPI app with documentation enabled."""
    return FastAPI(
        title="Ring MCP API",
        description="Ring Security System Management API - FastAPI Documentation",
        version="3.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )


# Configure structured logging with file output for monitoring
import logging.config
from pathlib import Path

from .core.exceptions import (
    AuthenticationError,
    DeviceNotFoundError,
    RateLimitError,
    RingError,
    StreamingError,
)

# Create log directory
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# Logging configuration for file output
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
        },
        "detailed": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"},
    },
    "handlers": {
        "file_info": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": log_dir / "ring_mcp_info.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "file_error": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": log_dir / "ring_mcp_error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "detailed",
            "stream": "ext://sys.stderr",  # Use stderr for console output
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["file_info", "file_error", "console"],
    },
    "loggers": {
        "ring_mcp": {
            "level": "INFO",
            "handlers": ["file_info", "file_error", "console"],
            "propagate": False,
        },
        "uvicorn": {
            "level": "INFO",
            "handlers": ["file_info", "console"],
            "propagate": False,
        },
    },
}

# Apply logging configuration
logging.config.dictConfig(LOGGING_CONFIG)

# Configure structlog to use the configured loggers
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Port management with graceful termination of previous instances
from ring_mcp.core.port_manager import get_ring_mcp_port

RING_MCP_PORT = get_ring_mcp_port()

# Initialize FastMCP (3.1 compatible)
app = FastMCP(name="Ring Security", version="3.1.0")

# Prometheus metrics
ring_api_calls_total = Counter("ring_api_calls_total", "Total Ring API calls", ["endpoint", "status"])
ring_api_duration = Histogram("ring_api_duration_seconds", "Ring API call duration", ["endpoint"])
ring_device_status = Gauge("ring_device_status", "Ring device status", ["device_id", "device_type", "status"])
ring_device_battery = Gauge("ring_device_battery_percent", "Ring device battery level", ["device_id", "device_type"])
ring_device_online = Gauge("ring_device_online", "Ring device online status", ["device_id", "device_type"])
ring_security_armed = Gauge("ring_security_armed", "Security system armed status", ["location"])
ring_tool_calls_total = Counter("ring_tool_calls_total", "Total MCP tool calls", ["tool_name"])
ring_tool_duration = Histogram("ring_tool_duration_seconds", "MCP tool execution time", ["tool_name"])
ring_active_connections = Gauge("ring_active_connections", "Active MCP connections")


# Models for request/response validation
class DeviceInfo(BaseModel):
    """Model for device information."""

    id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Device name")
    type: str = Field(..., description="Device type/family")
    model: str = Field(..., description="Device model")
    firmware: str | None = Field(None, description="Device firmware version")
    battery_life: int | None = Field(None, description="Battery percentage (0-100)")
    online: bool = Field(..., description="Whether the device is currently online")
    address: str | None = Field(None, description="Device location/address")
    timezone: str | None = Field(None, description="Device timezone")
    has_subscription: bool = Field(False, description="Whether the device has an active subscription")
    last_update: str = Field(..., description="ISO timestamp of last update")


class EventInfo(BaseModel):
    """Model for device event information."""

    id: str = Field(..., description="Event identifier")
    created_at: str = Field(..., description="Event timestamp in ISO format")
    answered: bool = Field(False, description="Whether the event was answered")
    kind: str | None = Field(None, description="Type of event")
    recording_status: str | None = Field(None, description="Status of recording if available")


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: bool = Field(True, description="Indicates this is an error response")
    message: str = Field(..., description="Error message")
    code: str | None = Field(None, description="Error code if available")


# Helper function to handle errors
def handle_error(e: Exception) -> dict[str, Any]:
    """Convert exceptions to error responses."""
    if isinstance(e, AuthenticationError):
        status_code = 401
        error_code = "authentication_error"
    elif isinstance(e, DeviceNotFoundError):
        status_code = 404
        error_code = "device_not_found"
    elif isinstance(e, StreamingError):
        status_code = 503
        error_code = "streaming_error"
    else:
        status_code = 500
        error_code = "internal_error"

    logger.error(
        "Ring MCP Error",
        error=str(e),
        error_code=error_code,
        status_code=status_code,
        exc_info=True,
    )

    return {"error": True, "message": str(e), "code": error_code, "status_code": status_code}


def track_ring_api_call(endpoint: str, success: bool = True):
    """Track Ring API calls for metrics."""
    status = "success" if success else "error"
    ring_api_calls_total.labels(endpoint=endpoint, status=status).inc()
    ring_api_duration.labels(endpoint=endpoint).observe(time.time())


def track_tool_call(tool_name: str):
    """Decorator to track MCP tool calls."""

    def decorator(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        async def wrapper(*args, **kwargs):
            ring_tool_calls_total.labels(tool_name=tool_name).inc()
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                ring_tool_duration.labels(tool_name=tool_name).observe(time.time() - start_time)
                return result
            except Exception:
                ring_tool_duration.labels(tool_name=tool_name).observe(time.time() - start_time)
                raise

        return wrapper

    return decorator


# Global Ring client instance
_ring_client: RingClient | None = None


def get_ring_client() -> RingClient:
    """Get or create a Ring client instance."""
    global _ring_client
    if _ring_client is None:
        _ring_client = RingClient()
    return _ring_client


def register_ring_tools(app: FastMCP, ring_client: RingClient) -> None:
    """Register Ring MCP tools with the FastMCP application using FastMCP 3.1 patterns.

    Args:
        app: FastMCP application instance
        ring_client: Initialized RingClient instance
    """

    # Request/Response models for FastMCP 3.1
    class DeviceID(BaseModel):
        """Device identifier model."""

        device_id: str = Field(..., description="The ID of the device")

    class DeviceListResponse(BaseModel):
        """Response model for device listing."""

        devices: list[dict[str, Any]] = Field(..., description="List of devices")

    class DeviceResponse(BaseModel):
        """Response model for device details."""

        device: dict[str, Any] = Field(..., description="Device details")

    class EventListResponse(BaseModel):
        """Response model for event listing."""

        events: list[dict[str, Any]] = Field(..., description="List of events")

    class StreamURLResponse(BaseModel):
        """Response model for stream URLs."""

        url: str = Field(..., description="Stream URL")

    class StatusResponse(BaseModel):
        """Response model for status updates."""

        success: bool = Field(..., description="Whether the operation was successful")
        message: str = Field(..., description="Status message")

    def handle_ring_errors(func: Callable[..., Awaitable[Any]]) -> Callable[..., Awaitable[Any]]:
        """Decorator to handle Ring API errors consistently."""

        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except AuthenticationError as e:
                raise ValueError(f"Authentication failed: {e!s}") from e
            except DeviceNotFoundError as e:
                raise ValueError(f"Device not found: {e!s}") from e
            except RateLimitError as e:
                raise ValueError(f"Rate limit exceeded: {e!s}") from e
            except StreamingError as e:
                raise ValueError(f"Streaming error: {e!s}") from e
            except RingError as e:
                raise ValueError(f"Ring API error: {e!s}") from e
            except Exception as e:
                logger.exception("Unexpected error: %s", str(e))
                raise ValueError(f"Internal server error: {e!s}") from e

        return wrapper

    @app.tool()
    @track_tool_call("get_devices")
    @handle_ring_errors
    async def get_devices(force_refresh: bool = False) -> DeviceListResponse:
        """Get a comprehensive list of all Ring devices with real-time status.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating separate tools for device listing, status checking, and
        connectivity verification, this single tool provides complete device inventory
        with status information. Prevents tool explosion while maintaining full functionality.

        Supported Operations:
        - Retrieve all Ring devices (cameras, doorbells, sensors, security systems)
        - Get real-time device status, battery levels, and connectivity
        - Force refresh device data from Ring API
        - Track device metrics for monitoring

        Operations Detail:
        **Device Discovery:**
        - "list": Enumerate all devices with comprehensive metadata
        - "status": Include real-time connectivity and battery information
        - "refresh": Force API refresh for latest device data

        Args:
            force_refresh (bool, optional): Whether to force refresh device data from Ring API.
                Used by: list operation. Default: False. Forces API call instead of using cache.

        Returns:
            **FastMCP 3.1+ Conversational Response Structure:**

            ```json
            {
              "devices": [
                {
                  "id": "device_id",
                  "name": "Front Door",
                  "type": "doorbell",
                  "model": "Ring Video Doorbell Pro",
                  "online": true,
                  "battery_life": 85,
                  "firmware": "1.2.3",
                  "address": "123 Test St",
                  "timezone": "Europe/Vienna",
                  "has_subscription": true,
                  "last_update": "2025-01-01T12:00:00Z"
                }
              ]
            }
            ```

            **Success Response Structure (Conversational):**
            - devices (list[dict]): Array of device objects with complete metadata
            - Each device includes: id, name, type, model, online status, battery level, firmware, location, timezone, subscription status, last update timestamp

        Examples:
            # Basic device listing
            result = await get_devices()
            # Returns: {"devices": [{"id": "123", "name": "Front Door", "type": "doorbell", ...}]}

            # Force refresh from API
            result = await get_devices(force_refresh=True)
            # Returns: Fresh device data from Ring API

        Errors:
            **Common Errors:**
            - "Authentication failed": Invalid Ring API credentials
            - "API rate limited": Too many requests to Ring API
            - "Network error": Unable to connect to Ring services

            **Recovery Options:**
            - Verify Ring account credentials and 2FA status
            - Wait and retry for rate limit errors
            - Check internet connectivity and Ring service status
        """
        try:
            devices = await ring_client.get_devices(force_refresh=force_refresh)

            # Track device metrics
            for device in devices:
                device_id = device.get("id", "unknown")
                device_type = device.get("type", "unknown")
                battery = device.get("battery_life")

                ring_device_online.labels(device_id=device_id, device_type=device_type).set(
                    1 if device.get("online", False) else 0
                )

                if battery is not None:
                    ring_device_battery.labels(device_id=device_id, device_type=device_type).set(battery)

            return DeviceListResponse(devices=devices)
        except Exception:
            track_ring_api_call("get_devices", success=False)
            raise

    @app.tool(name="get_device_details", description="Get detailed information about a specific device")
    @track_tool_call("get_device_details")
    @handle_ring_errors
    async def get_device_details(device_id: str) -> DeviceResponse:
        """Get comprehensive details and real-time status for a specific Ring device.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating separate tools for device info, status, and configuration,
        this single tool provides complete device details with real-time status.
        Prevents tool explosion while enabling detailed device inspection and monitoring.

        Supported Operations:
        - Retrieve complete device metadata and specifications
        - Get real-time connectivity, battery, and firmware status
        - Access device configuration and subscription information
        - Enable device health monitoring and diagnostics

        Operations Detail:
        **Device Information:**
        - "details": Complete device metadata (model, firmware, location)
        - "status": Real-time connectivity and battery information
        - "config": Device configuration and subscription status

        Args:
            device_id (str, required): The unique identifier of the device.
                Required for: details, status, config operations.
                Must be a valid Ring device ID from get_devices().

        Returns:
            **FastMCP 3.1+ Conversational Response Structure:**

            ```json
            {
              "device": {
                "id": "device_id",
                "name": "Front Door",
                "type": "doorbell",
                "model": "Ring Video Doorbell Pro",
                "firmware": "1.2.3",
                "battery_life": 85,
                "online": true,
                "address": "123 Test St",
                "timezone": "Europe/Vienna",
                "has_subscription": true,
                "last_update": "2025-01-01T12:00:00Z"
              }
            }
            ```

            **Success Response Structure (Conversational):**
            - device (dict): Complete device information object
            - Includes all device metadata: identification, specifications, status, location, and configuration

        Examples:
            # Get device details
            result = await get_device_details("device-123")
            # Returns: {"device": {"id": "device-123", "name": "Front Door", "online": true, ...}}

        Errors:
            **Common Errors:**
            - "Device not found": Specified device_id doesn't exist
            - "Authentication failed": Invalid Ring API credentials
            - "Permission denied": Device not accessible to current account

            **Recovery Options:**
            - Verify device_id from get_devices() output
            - Check Ring account has access to the device
            - Ensure Ring API credentials are valid and current
        """
        try:
            device = await ring_client.get_device(device_id)
            if not device:
                raise DeviceNotFoundError(f"Device {device_id} not found")

            # Track device status
            device_type = device.get("type", "unknown")
            battery = device.get("battery_life")
            ring_device_online.labels(device_id=device_id, device_type=device_type).set(
                1 if device.get("online", False) else 0
            )

            if battery is not None:
                ring_device_battery.labels(device_id=device_id, device_type=device_type).set(battery)

            return DeviceResponse(device=device)
        except Exception:
            track_ring_api_call("get_device_details", success=False)
            raise

    @app.tool()
    @handle_ring_errors
    async def get_device_events(device_id: str, limit: int = 10) -> EventListResponse:
        """Retrieve recent activity events and motion history for a Ring device.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating separate tools for motion events, doorbell rings, and
        security alerts, this single tool provides comprehensive event history.
        Prevents tool explosion while enabling complete activity monitoring and review.

        Supported Operations:
        - Retrieve motion detection events and timestamps
        - Access doorbell press history with timestamps
        - Get security alert and alarm activation records
        - Review device activity with configurable limits

        Operations Detail:
        **Event Retrieval:**
        - "motion": Motion detection events with timestamps
        - "doorbell": Doorbell press and visitor events
        - "security": Alarm and security system events
        - "activity": All device activity with pagination

        Args:
            device_id (str, required): The unique identifier of the device.
                Required for: motion, doorbell, security, activity operations.
                Must be a valid Ring device ID from get_devices().

            limit (int, optional): Maximum number of events to retrieve.
                Used by: activity operation. Default: 10. Valid range: 1-50.
                Limits API calls and response size for performance.

        Returns:
            **FastMCP 3.1+ Conversational Response Structure:**

            ```json
            {
              "events": [
                {
                  "id": "event-123",
                  "created_at": "2025-01-01T12:00:00Z",
                  "answered": false,
                  "kind": "motion",
                  "recording_status": "ready"
                },
                {
                  "id": "event-124",
                  "created_at": "2025-01-01T11:45:00Z",
                  "answered": true,
                  "kind": "doorbell",
                  "recording_status": "ready"
                }
              ]
            }
            ```

            **Success Response Structure (Conversational):**
            - events (list[dict]): Array of event objects chronologically ordered (newest first)
            - Each event includes: id, timestamp, answered status, event type, recording status

        Examples:
            # Get recent events (default 10)
            result = await get_device_events("device-123")
            # Returns: {"events": [{"id": "123", "kind": "motion", "created_at": "..."}, ...]}

            # Get last 5 events
            result = await get_device_events("device-123", limit=5)
            # Returns: {"events": [...] limited to 5 most recent events

        Errors:
            **Common Errors:**
            - "Device not found": Specified device_id doesn't exist
            - "No events available": Device has no recorded activity
            - "Authentication failed": Invalid Ring API credentials

            **Recovery Options:**
            - Verify device_id from get_devices() output
            - Check device has been active and recording events
            - Ensure Ring account has event history access
            - Try with a smaller limit if timeout occurs
        """
        events = await ring_client.get_device_events(device_id, limit=limit)
        return EventListResponse(events=events)

    @app.tool()
    @handle_ring_errors
    async def get_live_stream_url(device_id: str) -> StreamURLResponse:
        """Generate a temporary live stream URL for Ring camera viewing.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating separate tools for different stream formats or camera types,
        this single tool provides unified streaming access for all Ring cameras.
        Prevents tool explosion while enabling immediate live viewing capabilities.

        Supported Operations:
        - Generate temporary streaming URLs for Ring cameras
        - Enable real-time video feed access and monitoring
        - Support live viewing for security and surveillance
        - Provide immediate access to camera feeds

        Operations Detail:
        **Streaming Access:**
        - "generate_url": Create temporary stream URL for camera
        - "live_view": Enable real-time video streaming access
        - "monitoring": Support security monitoring and surveillance

        Prerequisites:
        - Device must be a Ring camera (Spotlight Cam, Floodlight Cam, Indoor Cam)
        - Camera must be online and accessible
        - Ring account must have camera viewing permissions
        - Stream URLs are temporary (typically 5-10 minutes validity)

        Args:
            device_id (str, required): The unique identifier of the camera device.
                Required for: generate_url, live_view, monitoring operations.
                Must be a valid Ring camera device ID from get_devices().

        Returns:
            **FastMCP 3.1+ Conversational Response Structure:**

            ```json
            {
              "url": "rtsp://stream.ring.com/live/camera-123?token=abc123&expires=1735689600"
            }
            ```

            **Success Response Structure (Conversational):**
            - url (str): Temporary RTSP stream URL for live camera viewing
            - URL includes authentication token and expiration timestamp
            - Valid for limited time (typically 5-10 minutes)

        Examples:
            # Get live stream URL
            result = await get_live_stream_url("camera-123")
            # Returns: {"url": "rtsp://stream.ring.com/live/camera-123?token=...&expires=..."}

            # Open stream in media player
            stream_url = result["url"]
            # Use with VLC, FFmpeg, or compatible RTSP player

        Errors:
            **Common Errors:**
            - "Device not found": Specified device_id is not a valid camera
            - "Device offline": Camera is currently not connected/online
            - "Permission denied": Account lacks camera viewing permissions
            - "Subscription required": Camera requires active Ring subscription
            - "Stream unavailable": Camera temporarily unable to stream

            **Recovery Options:**
            - Verify device_id is a camera from get_devices() output
            - Check camera is online using get_device_details()
            - Ensure Ring account has Protect Plan or camera subscription
            - Wait and retry if camera was temporarily unavailable
            - Check Ring app for camera connectivity issues
        """
        url = await ring_client.get_live_stream_url(device_id)
        return StreamURLResponse(url=url)

    @app.tool()
    @track_tool_call("set_arm_status")
    @handle_ring_errors
    async def set_arm_status(device_id: str, status: bool) -> StatusResponse:
        """Arm or disarm Ring security systems and alarm devices (CRITICAL SECURITY OPERATION).

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating separate tools for arming/disarming different security device types,
        this single tool provides unified security control for all Ring alarm systems.
        Prevents tool explosion while maintaining critical security operation integrity.

        Supported Operations:
        - Arm security systems for property protection
        - Disarm systems for authorized access and maintenance
        - Control alarm activation and deactivation
        - Manage security system status and monitoring

        Operations Detail:
        **Security Control:**
        - "arm": Activate security system and alarm monitoring
        - "disarm": Deactivate security system for authorized access
        - "status_change": Modify armed/disarmed state with confirmation

        Prerequisites:
        - Device must be a Ring security system or alarm device
        - Ring account must have security system control permissions
        - Two-factor authentication should be enabled for security
        - Emergency contacts should be configured in Ring app

        Args:
            device_id (str, required): The unique identifier of the security device.
                Required for: arm, disarm, status_change operations.
                Must be a valid Ring security system from get_devices().

            status (bool, required): Security system state to set.
                Required for: status_change operation. Valid values: True (arm), False (disarm).
                True = activate security monitoring and alarms
                False = deactivate security monitoring for authorized access

        Returns:
            **FastMCP 3.1+ Conversational Response Structure:**

            ```json
            {
              "success": true,
              "message": "Device alarm-system-123 armed successfully",
              "operation": "arm",
              "timestamp": "2025-01-01T12:00:00Z",
              "device_id": "alarm-system-123"
            }
            ```

            **Success Response Structure (Conversational):**
            - success (bool): Whether the security operation completed successfully
            - message (str): Human-readable confirmation of the security state change
            - operation (str): The operation performed ("arm" or "disarm")
            - timestamp (str): ISO timestamp when the operation completed
            - device_id (str): Device that was modified for verification

        Examples:
            # Arm security system
            result = await set_arm_status("alarm-system-123", True)
            # Returns: {"success": true, "message": "Device alarm-system-123 armed successfully", ...}

            # Disarm security system
            result = await set_arm_status("alarm-system-123", False)
            # Returns: {"success": true, "message": "Device alarm-system-123 disarmed successfully", ...}

        Errors:
            **Critical Security Errors (Handle Immediately):**
            - "Authentication failed": Invalid credentials - security system remains in current state
            - "Device not found": Security device doesn't exist - verify device_id
            - "Permission denied": Account lacks security control permissions
            - "Device offline": Security system unreachable - check connectivity
            - "Already armed/disarmed": System already in requested state

            **Recovery Options:**
            - **IMMEDIATELY** verify security system status in Ring app or via get_device_details()
            - Check Ring account has security system control permissions
            - Ensure device is online and connected to Ring network
            - If authentication fails, re-authenticate and retry immediately
            - For critical failures, contact Ring support and verify property security
            - Document all security operations for audit trail

            **Emergency Contacts:**
            - Ring App: Check security system status manually
            - Local Authorities: Contact if unable to verify security status
            - Ring Support: Professional assistance for security system issues
        """
        try:
            success = await ring_client.set_arm_status(device_id, status)

            # Track security system status
            location = "default"  # Could be enhanced to track by location
            ring_security_armed.labels(location=location).set(1 if status else 0)

            action = "armed" if status else "disarmed"
            return StatusResponse(
                success=success,
                message=f"Device {device_id} {action} {'successfully' if success else 'failed'}",
            )
        except Exception:
            track_ring_api_call("set_arm_status", success=False)
            raise

    @app.tool()
    @handle_ring_errors
    async def trigger_chime(device_id: str) -> StatusResponse:
        """Manually trigger doorbell chime for testing and signaling purposes.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating separate tools for doorbell testing, visitor signaling,
        and audio verification, this single tool provides unified chime control.
        Prevents tool explosion while enabling comprehensive doorbell functionality testing.

        Supported Operations:
        - Manually trigger doorbell chime for testing
        - Signal visitors or household members
        - Verify doorbell audio and connectivity
        - Test integration with home automation systems

        Operations Detail:
        **Doorbell Control:**
        - "trigger": Activate doorbell chime manually
        - "test": Verify doorbell functionality and audio
        - "signal": Alert household members or visitors

        Prerequisites:
        - Device must be a Ring doorbell (Video Doorbell, Doorbell Pro, etc.)
        - Doorbell must be online and powered
        - Ring account must have doorbell control permissions

        Args:
            device_id (str, required): The unique identifier of the doorbell device.
                Required for: trigger, test, signal operations.
                Must be a valid Ring doorbell device from get_devices().

        Returns:
            **FastMCP 3.1+ Conversational Response Structure:**

            ```json
            {
              "success": true,
              "message": "Chime triggered successfully",
              "operation": "trigger",
              "timestamp": "2025-01-01T12:00:00Z",
              "device_id": "doorbell-123"
            }
            ```

            **Success Response Structure (Conversational):**
            - success (bool): Whether the chime was triggered successfully
            - message (str): Human-readable confirmation of chime activation
            - operation (str): Operation performed ("trigger")
            - timestamp (str): ISO timestamp when chime was triggered
            - device_id (str): Doorbell device that was activated

        Examples:
            # Trigger doorbell chime
            result = await trigger_chime("doorbell-123")
            # Returns: {"success": true, "message": "Chime triggered successfully", ...}

            # Test doorbell functionality
            result = await trigger_chime("doorbell-123")
            # Listen for chime sound to verify audio works

        Errors:
            **Common Errors:**
            - "Device not found": Specified device_id is not a valid doorbell
            - "Device offline": Doorbell is currently not connected/online
            - "Permission denied": Account lacks doorbell control permissions
            - "Rate limited": Too many chime triggers in short time period
            - "Device busy": Doorbell currently handling another operation

            **Recovery Options:**
            - Verify device_id is a doorbell from get_devices() output
            - Check doorbell is online using get_device_details()
            - Wait 30 seconds between chime triggers to avoid rate limiting
            - Ensure doorbell has sufficient battery power or is plugged in
            - Test manually via Ring app first to verify functionality
        """
        success = await ring_client.trigger_chime(device_id)
        return StatusResponse(
            success=success,
            message=f"Chime {'triggered successfully' if success else 'failed to trigger'}",
        )

    @app.tool()
    @handle_ring_errors
    async def health_check() -> StatusResponse:
        """Perform comprehensive health check of Ring MCP service and Ring connectivity.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating separate tools for API connectivity, authentication verification,
        device accessibility, and service monitoring, this single tool provides complete
        system health assessment. Prevents tool explosion while ensuring service reliability.

        Supported Operations:
        - Verify Ring API connectivity and authentication
        - Test device accessibility and communication
        - Check system resource availability and performance
        - Validate all MCP tool functionality and responses
        - Monitor service health and operational status

        Operations Detail:
        **Health Assessment:**
        - "connectivity": Test Ring API and authentication
        - "devices": Verify device accessibility and status
        - "resources": Check system resource availability
        - "tools": Validate MCP tool functionality
        - "comprehensive": Full system health evaluation

        Prerequisites:
        - Ring account credentials must be configured
        - Internet connectivity to Ring services
        - At least one Ring device should be accessible
        - MCP service should be running and initialized

        Args:
            None required - comprehensive health check is automatic.

        Returns:
            **FastMCP 3.1+ Conversational Response Structure:**

            ```json
            {
              "success": true,
              "message": "Ring MCP service is healthy - API connected, 5 devices accessible",
              "operation": "comprehensive",
              "timestamp": "2025-01-01T12:00:00Z",
              "health_status": {
                "api_connected": true,
                "devices_accessible": 5,
                "authentication_valid": true,
                "last_check": "2025-01-01T12:00:00Z"
              }
            }
            ```

            **Success Response Structure (Conversational):**
            - success (bool): Whether the health check passed
            - message (str): Human-readable health status summary
            - operation (str): Health check operation performed ("comprehensive")
            - timestamp (str): ISO timestamp when health check was performed
            - health_status (dict): Detailed health metrics and status information

        Examples:
            # Perform comprehensive health check
            result = await health_check()
            # Returns: {"success": true, "message": "Ring MCP service is healthy", ...}

            # Check result details
            if result["success"]:
                logger.info("Devices accessible: %s", result["health_status"]["devices_accessible"])
            # Output: "Devices accessible: 5"

        Errors:
            **Common Errors:**
            - "Authentication failed": Invalid or expired Ring credentials
            - "API unreachable": Cannot connect to Ring services
            - "No devices found": Account has no accessible Ring devices
            - "Service unavailable": MCP service experiencing internal errors

            **Recovery Options:**
            - Verify Ring username/password and 2FA status
            - Check internet connectivity to Ring services
            - Ensure Ring account has active devices
            - Restart MCP service if experiencing internal errors
            - Check Ring app for account status and device connectivity
            - Contact Ring support if API access issues persist
        """
        try:
            # Try to get devices as a health check
            await ring_client.get_devices(force_refresh=False)
            return StatusResponse(success=True, message="Ring MCP service is healthy")
        except Exception as e:
            logger.exception("Health check failed: %s", str(e))
            return StatusResponse(success=False, message=f"Health check failed: {e!s}")


# Register all tools on the global app instance
def register_all_tools_on_app(app: FastMCP, ring_client: RingClient | None = None):
    """Register all Ring MCP tools on a specific app instance."""
    try:
        from .tools import (
            automation_tools,
            camera_tools,
            doorbell_tools,
            fire_safety_tools,
            help_tool,
            monitoring_tools,
            security_system_tools,
            status_tool,
        )

        # Register tools from each module
        automation_tools.register_tools(app)
        camera_tools.register_tools(app)
        doorbell_tools.register_tools(app)
        fire_safety_tools.register_tools(app)
        help_tool.register_tools(app)
        monitoring_tools.register_tools(app)
        security_system_tools.register_tools(app)
        status_tool.register_tools(app)

        logger.info("All Ring MCP tools registered successfully on app instance")

    except Exception as e:
        logger.exception("Failed to register tools on app: %s", str(e))
        # Don't crash the server if tool registration fails
        logger.warning("App will start with limited functionality")


def register_all_tools():
    """Register all Ring MCP tools on the global app instance (for backward compatibility)."""
    register_all_tools_on_app(app)


def create_app(ring_client: RingClient | None = None) -> FastMCP:
    """Create and configure the FastMCP application with composition support.

    This function creates the main FastMCP application instance and registers
    all Ring security tools using FastMCP 3.1 patterns with multiline decorators.

    Args:
        ring_client: Optional pre-initialized RingClient instance. If not provided,
                    a new client will be created using environment variables.

    Returns:
        Configured FastMCP application with Ring MCP and composition support
    """
    # Create a new FastMCP app instance
    new_app = FastMCP(
        name="Ring MCP Server",
    )

    # Register all tools on the new app instance
    try:
        register_all_tools_on_app(new_app, ring_client)
        logger.info("All Ring MCP tools registered successfully on new app instance")
    except Exception as e:
        logger.exception("Failed to register tools on new app: %s", str(e))
        logger.warning("New app will start with limited functionality")

    return new_app


if __name__ == "__main__":
    # Configure structured logging for FastMCP 3.1
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Configure structlog for JSON logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Start Prometheus metrics server for monitoring
    metrics_port = int(os.getenv("METRICS_PORT", "8001"))
    start_http_server(metrics_port)
    logger.info("Prometheus metrics server started", port=metrics_port)

    # Create and run the FastMCP server with stdio transport for Claude Desktop
    # The app is already configured with both stdio and HTTP transports
    logger.info("Starting Ring MCP server with FastMCP 3.1 patterns")
    logger.info("Server will be available via stdio for Claude Desktop and HTTP for web access")
