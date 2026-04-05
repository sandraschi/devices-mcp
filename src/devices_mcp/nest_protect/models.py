"""
Data models for the Nest Protect MCP server.

This module defines the data structures used throughout the Nest Protect MCP server,
including configuration, state, and command models.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProtectAlarmState(str, Enum):
    """Possible alarm states for Nest Protect."""

    OK = "ok"
    WARNING = "warning"
    EMERGENCY = "emergency"
    TESTING = "testing"
    OFF = "off"


class ProtectAlarmType(str, Enum):
    """Types of alarms that Nest Protect can detect."""

    SMOKE = "smoke"
    CO = "carbon_monoxide"
    HEAT = "heat"
    BATTERY = "battery"
    POWER = "power"
    WIFI = "wifi"
    TEST = "test"


class ProtectBatteryState(str, Enum):
    """Battery state of the Nest Protect."""

    OK = "ok"
    REPLACE = "replace_soon"
    CRITICAL = "replace_now"
    MISSING = "missing"
    INVALID = "invalid"


class ProtectHushState(str, Enum):
    """Hush state of the Nest Protect."""

    NONE = "none"
    HUSH = "hush"
    HUSHED = "hushed"


class ProtectConfig(BaseModel):
    """Configuration for the Nest Protect MCP server."""

    # Connection settings
    project_id: str = Field("", description="Google Cloud Project ID")
    client_id: str = Field("", description="OAuth 2.0 Client ID")
    client_secret: str = Field("", description="OAuth 2.0 Client Secret")
    refresh_token: str = Field("", description="OAuth 2.0 Refresh Token")

    # Device settings
    update_interval: int = Field(60, description="Update interval in seconds")

    # MQTT settings (optional)
    mqtt_enabled: bool = Field(False, description="Enable MQTT integration")
    mqtt_host: str = Field("localhost", description="MQTT broker host")
    mqtt_port: int = Field(1883, description="MQTT broker port")
    mqtt_username: Optional[str] = Field(None, description="MQTT username")
    mqtt_password: Optional[str] = Field(None, description="MQTT password")
    mqtt_topic_prefix: str = Field("nest/protect/", description="MQTT topic prefix")

    # Home Assistant settings (optional)
    homeassistant_discovery: bool = Field(False, description="Enable Home Assistant MQTT discovery")
    homeassistant_prefix: str = Field(
        "homeassistant", description="Home Assistant MQTT discovery prefix"
    )

    # Logging
    log_level: str = Field("INFO", description="Logging level")
    log_file: Optional[str] = Field(None, description="Path to log file")

    model_config = ConfigDict(
        env_prefix="NEST_PROTECT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class ProtectDeviceState(BaseModel):
    """Current state of a Nest Protect device."""

    device_id: str = Field(..., description="Unique device identifier")
    name: str = Field(..., description="Device name")
    model: str = Field(..., description="Device model")
    serial_number: str = Field(..., description="Device serial number")

    # Status
    online: bool = Field(False, description="Whether the device is online")
    battery_health: ProtectBatteryState = Field(..., description="Battery health status")
    co_alarm_state: ProtectAlarmState = Field(..., description="CO alarm state")
    smoke_alarm_state: ProtectAlarmState = Field(..., description="Smoke alarm state")
    heat_alarm_state: ProtectAlarmState = Field(..., description="Heat alarm state")

    # Sensors
    battery_level: Optional[int] = Field(None, description="Battery level (0-100)", ge=0, le=100)
    co_ppm: Optional[float] = Field(None, description="CO level in PPM", ge=0)
    temperature: Optional[float] = Field(None, description="Temperature in °C")
    humidity: Optional[float] = Field(None, description="Humidity percentage", ge=0, le=100)

    # Timestamps
    last_connection: Optional[datetime] = Field(None, description="Last connection time")
    last_manual_test: Optional[datetime] = Field(None, description="Last manual test time")

    # Additional info
    software_version: Optional[str] = Field(None, description="Firmware version")
    wifi_ip: Optional[str] = Field(None, description="IP address on WiFi network")
    wifi_ssid: Optional[str] = Field(None, description="Connected WiFi SSID")

    model_config = ConfigDict()


class ProtectCommand(BaseModel):
    """Command to send to a Nest Protect device."""

    command: str = Field(..., description="Command to execute")
    device_id: Optional[str] = Field(
        None, description="Target device ID (if not specified, applies to all)"
    )
    params: Dict[str, Any] = Field(default_factory=dict, description="Command parameters")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v):
        """Validate the command type."""
        valid_commands = ["hush", "test", "locate", "update"]
        if v not in valid_commands:
            raise ValueError(f"Invalid command. Must be one of: {', '.join(valid_commands)}")
        return v


class ProtectEvent(BaseModel):
    """Event from a Nest Protect device."""

    event_id: str = Field(..., description="Unique event identifier")
    device_id: str = Field(..., description="Source device ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")
    event_type: str = Field(..., description="Type of event")
    event_data: Dict[str, Any] = Field(default_factory=dict, description="Event data")

    model_config = ConfigDict()
