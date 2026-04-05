"""
Configuration models for the Devices MCP server.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class WebUISettings(BaseModel):
    """Web UI specific settings (reservoir port 10716 per WEBAPP_PORTS.md)."""

    enabled: bool = True
    host: str = "0.0.0.0"  # nosec B104
    port: int = 10716
    title: str = "Devices MCP"
    theme: Literal["light", "dark", "system"] = "dark"
    enable_swagger: bool = True
    enable_redoc: bool = False
    enable_cors: bool = True
    cors_origins: List[str] = Field(
        default_factory=lambda: ["*"], description="List of allowed CORS origins"
    )
    session_secret: str = "change-this-in-production"  # nosec B105
    session_lifetime: int = 86400  # 24 hours in seconds


class RingSettings(BaseModel):
    """Ring doorbell and alarm settings."""

    enabled: bool = False
    email: Optional[str] = None
    password: Optional[str] = None
    token_file: str = "ring_token.cache"
    cache_ttl: int = 60  # seconds


class NestSettings(BaseModel):
    """Nest Protect settings - uses Google account auth."""

    enabled: bool = False
    refresh_token: Optional[str] = None  # Google OAuth refresh token
    token_file: str = "nest_token.cache"
    cache_ttl: int = 60  # seconds


class HomeAssistantSettings(BaseModel):
    """Home Assistant integration settings."""

    enabled: bool = False
    url: str = "http://localhost:8123"
    access_token: Optional[str] = None  # Long-lived access token from HA
    cache_ttl: int = 30  # seconds


class SecurityIntegrations(BaseModel):
    """Settings for external security system integrations."""

    nest_protect: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": False,
            "server_url": "http://localhost:8123",
            "api_key": None,
        },
        description="Nest Protect MCP server integration settings (legacy REST)",
    )
    nest: NestSettings = Field(
        default_factory=NestSettings,
        description="Nest Protect via Google account auth (deprecated - use HA)",
    )
    homeassistant: HomeAssistantSettings = Field(
        default_factory=HomeAssistantSettings,
        description="Home Assistant for Nest Protect (recommended)",
    )
    ring_mcp: Dict[str, Any] = Field(
        default_factory=lambda: {
            "enabled": False,
            "server_path": "D:\\Dev\\repos\\ring-mcp",
            "proxy_port": 8124,
        },
        description="Ring MCP server integration settings",
    )
    ring: RingSettings = Field(default_factory=RingSettings)


class SecuritySettings(BaseModel):
    """Security related settings."""

    secret_key: str = "change-this-in-production"  # nosec B105
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    password_min_length: int = 8
    password_require_digit: bool = True
    password_require_uppercase: bool = True
    password_require_special_char: bool = True
    rate_limit: str = "100/minute"
    enable_rate_limiting: bool = True

    # Security system integrations
    integrations: SecurityIntegrations = Field(default_factory=SecurityIntegrations)


class WeatherSettings(BaseModel):
    """Weather and environment integrations."""

    integrations: Dict[str, Any] = Field(
        default_factory=lambda: {
            "netatmo": {
                "enabled": False,
                "client_id": None,
                "client_secret": None,
                # OAuth recommended:
                "redirect_uri": "https://localhost/callback",
                "refresh_token": None,
                # Browser OAuth (Weather page): must match Netatmo app redirect list exactly
                "oauth_callback_url": None,
                "oauth_success_redirect": "/app/weather?netatmo_oauth=ok",
                # Station selection (optional): make "primary" stable for dashboards/alerts
                "primary_station_id": None,
                "primary_station_name": None,
                # Legacy (optional, discouraged):
                "username": None,
                "password": None,
                "home_id": None,
            }
        },
        description="Weather integrations configuration",
    )


class LoggingSettings(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    file: Optional[Path] = None
    max_size_mb: int = 10
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"


class StorageSettings(BaseModel):
    """Storage configuration."""

    recordings_dir: Path = Path("recordings")
    snapshots_dir: Path = Path("snapshots")
    temp_dir: Path = Path("temp")
    max_storage_gb: int = 100
    retention_days: int = 30  # Legacy: kept for backward compatibility

    # Separate retention policies
    retention_policies: dict[str, int] = {
        "video_recordings": 30,  # Days to keep video recordings
        "snapshots": 90,  # Days to keep snapshots
        "environment_data": 365,  # Days to keep weather/energy time series data
    }


@dataclass
class ServerConfig:
    """Server configuration class."""

    # Server settings
    host: str = "0.0.0.0"  # nosec B104
    port: int = 8080
    debug: bool = False

    # Web UI settings
    web: WebUISettings = field(default_factory=WebUISettings)

    # Security settings
    security: SecuritySettings = field(default_factory=SecuritySettings)

    # Logging settings
    logging: LoggingSettings = field(default_factory=LoggingSettings)

    # Storage settings
    storage: StorageSettings = field(default_factory=StorageSettings)

    # Camera settings
    default_camera: Optional[Dict[str, Any]] = None
    camera_scan_interval: int = 300  # 5 minutes

    # Performance settings
    max_workers: int = 4
    request_timeout: int = 30
    log_level: str = "INFO"
    log_file: Optional[Path] = None

    # Security settings
    api_key: Optional[str] = None
    cors_origins: List[str] = field(default_factory=lambda: ["*"])

    # Storage settings
    data_dir: Path = Path("data")
    cache_dir: Path = Path("cache")

    def __post_init__(self):
        """Post-initialization processing."""
        # Ensure paths are Path objects
        if isinstance(self.data_dir, str):
            self.data_dir = Path(self.data_dir)
        if isinstance(self.cache_dir, str):
            self.cache_dir = Path(self.cache_dir)
        if self.log_file and isinstance(self.log_file, str):
            self.log_file = Path(self.log_file)


@dataclass
class CameraConfig:
    """Camera configuration class."""

    host: str
    username: str
    password: str
    stream_quality: str = "hd"
    verify_ssl: bool = True
    rtsp_port: int = 554
    onvif_port: int = 2020

    # Motion detection settings
    motion_detection: bool = True
    motion_sensitivity: str = "medium"  # low, medium, high
    motion_zones: List[Dict] = field(default_factory=list)

    # Recording settings
    recording: bool = False
    recording_mode: str = "motion"  # motion, continuous
    storage_path: str = "recordings"
    max_storage_gb: int = 10

    # Privacy settings
    privacy_mode: bool = False
    led_enabled: bool = True

    # Advanced settings
    timeout: int = 10
    max_retries: int = 3
