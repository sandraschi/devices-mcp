"""
Data models for devices-mcp.
"""

from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, IPvAnyAddress, field_validator


class CameraModel(str, Enum):
    """Supported Tapo camera models."""

    C100 = "Tapo C100"
    C110 = "Tapo C110"
    C200 = "Tapo C200"
    C210 = "Tapo C210"
    C310 = "Tapo C310"


class StreamType(str, Enum):
    """Supported stream types."""

    RTSP = "rtsp"
    RTMP = "rtmp"
    HLS = "hls"
    DASH = "dash"


class VideoQuality(str, Enum):
    """Video quality presets."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PTZDirection(str, Enum):
    """PTZ movement directions."""

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    STOP = "stop"


class MotionDetectionSensitivity(str, Enum):
    """Motion detection sensitivity levels."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OFF = "off"


class CameraStatus(BaseModel):
    """Current status of the camera."""

    online: bool = Field(..., description="Whether the camera is online")
    recording: bool = Field(False, description="Whether the camera is currently recording")
    motion_detected: bool = Field(False, description="Whether motion is currently detected")
    audio_detected: bool = Field(False, description="Whether audio is currently detected")
    privacy_mode: bool = Field(False, description="Whether privacy mode is enabled")
    led_enabled: bool = Field(True, description="Whether the status LED is enabled")
    firmware_version: str = Field(..., description="Camera firmware version")
    uptime: int = Field(0, description="Uptime in seconds")
    storage: dict[str, int | str] = Field(default_factory=dict, description="Storage information")


class CameraConfig(BaseModel):
    """Configuration for a Tapo camera."""

    # Connection settings - now optional with defaults
    host: str | None = Field(None, description="Camera IP address or hostname")
    port: int = Field(443, description="Camera port (usually 443 for HTTPS)")
    username: str | None = Field(None, description="Camera username (usually admin)")
    password: str | None = Field(None, description="Camera password")
    use_https: bool = Field(True, description="Use HTTPS for API calls")
    verify_ssl: bool = Field(True, description="Verify SSL certificate")
    timeout: int = Field(10, description="Request timeout in seconds")

    # Stream settings
    stream_type: StreamType = Field(StreamType.RTSP, description="Default stream type")
    stream_quality: VideoQuality = Field(VideoQuality.HIGH, description="Default stream quality")
    stream_audio: bool = Field(True, description="Enable audio in stream")

    # Storage settings
    storage_path: str = Field("recordings", description="Local path for storing recordings")
    max_storage_gb: int = Field(10, description="Maximum storage in GB for recordings")

    # Motion detection
    motion_detection_enabled: bool = Field(True, description="Enable motion detection")
    motion_sensitivity: MotionDetectionSensitivity = Field(
        MotionDetectionSensitivity.MEDIUM, description="Motion detection sensitivity"
    )
    motion_zones: list[dict] = Field(default_factory=list, description="Motion detection zones")

    # Privacy settings
    privacy_mode: bool = Field(False, description="Enable privacy mode")
    led_enabled: bool = Field(True, description="Enable status LED")

    # Advanced settings
    rtsp_port: int = Field(554, description="RTSP port (usually 554)")
    onvif_port: int = Field(2020, description="ONVIF port (usually 2020)")

    @field_validator("host")
    @classmethod
    def validate_host(cls, v):
        """Validate the host is not empty if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Host cannot be empty")
        return v.strip() if v else v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate the username is not empty if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Username cannot be empty")
        return v.strip() if v else v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        """Validate the password is not empty if provided."""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Password cannot be empty")
        return v.strip() if v else v


class PTZPosition(BaseModel):
    """PTZ position coordinates."""

    pan: float = Field(0.0, ge=-1.0, le=1.0, description="Pan position (-1.0 to 1.0)")
    tilt: float = Field(0.0, ge=-1.0, le=1.0, description="Tilt position (-1.0 to 1.0)")
    zoom: float = Field(0.0, ge=0.0, le=1.0, description="Zoom level (0.0 to 1.0)")


class MotionEvent(BaseModel):
    """Motion detection event."""

    timestamp: float = Field(..., description="Event timestamp")
    confidence: float = Field(..., description="Detection confidence (0.0 to 1.0)")
    zones: list[dict] = Field(default_factory=list, description="Triggered zones")
    snapshot_url: HttpUrl | None = Field(None, description="URL to snapshot of the event")
    video_clip_url: HttpUrl | None = Field(None, description="URL to video clip of the event")


class RecordingConfig(BaseModel):
    """Recording configuration."""

    enabled: bool = Field(True, description="Enable/disable recording")
    mode: str = Field("motion", description="Recording mode: 'motion', 'continuous', or 'manual'")
    pre_buffer: int = Field(5, description="Pre-motion buffer in seconds")
    post_buffer: int = Field(10, description="Post-motion buffer in seconds")
    max_clip_length: int = Field(300, description="Maximum clip length in seconds")
    storage_path: str = Field("recordings", description="Path to store recordings")
    max_storage_gb: int = Field(10, description="Maximum storage in GB")


class CameraInfo(BaseModel):
    """Camera device information."""

    model: CameraModel
    serial_number: str
    mac_address: str
    firmware_version: str
    hardware_version: str
    uptime: int
    ip_address: IPvAnyAddress
    wifi_signal: int = Field(ge=0, le=100, description="WiFi signal strength (0-100)")
    wifi_ssid: str | None = Field(None, description="Connected WiFi SSID")
