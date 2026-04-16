"""
Configuration utilities for PlexMCP.

This module provides functions for loading, saving, and validating
application configuration.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError, validator

# Default configuration
DEFAULT_CONFIG = {
    "server": {
        "host": "localhost",
        "port": 32400,
        "secure_connection": False,
        "verify_ssl": True,
        "timeout": 30,
    },
    "logging": {"level": "INFO", "file": None, "max_size_mb": 10, "backup_count": 5},
    "cache": {
        "enabled": True,
        "ttl": 300,  # 5 minutes
        "max_size": 1000,
    },
    "security": {"secret_key": None, "password_salt_rounds": 10},
    "features": {"enable_analytics": False, "enable_updates": True, "enable_telemetry": False},
}

# Configuration file paths
CONFIG_DIR = Path(os.getenv("PLEXMCP_CONFIG_DIR", Path.home() / ".config" / "plexmcp"))
CONFIG_FILE = CONFIG_DIR / "config.json"

# Ensure config directory exists
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


class ServerConfig(BaseModel):
    """Plex server connection configuration."""

    host: str = "localhost"
    port: int = 32400
    token: str | None = None
    secure_connection: bool = False
    verify_ssl: bool = True
    timeout: int = 30

    @validator("port")
    def validate_port(cls, v):
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    file: Path | None = None
    max_size_mb: int = 10
    backup_count: int = 5

    @validator("level")
    def validate_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @validator("file")
    def validate_file(cls, v):
        if v is not None:
            return Path(v).resolve()
        return None


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = True
    ttl: int = 300  # 5 minutes in seconds
    max_size: int = 1000

    @validator("ttl")
    def validate_ttl(cls, v):
        if v < 0:
            raise ValueError("TTL must be a positive number")
        return v


class SecurityConfig(BaseModel):
    """Security configuration."""

    secret_key: str | None = None
    password_salt_rounds: int = 10

    @validator("password_salt_rounds")
    def validate_salt_rounds(cls, v):
        if v < 4 or v > 31:
            raise ValueError("Password salt rounds must be between 4 and 31")
        return v


class FeaturesConfig(BaseModel):
    """Feature flags configuration."""

    enable_analytics: bool = False
    enable_updates: bool = True
    enable_telemetry: bool = False


class AppConfig(BaseModel):
    """Application configuration model."""

    server: ServerConfig = ServerConfig()
    logging: LoggingConfig = LoggingConfig()
    cache: CacheConfig = CacheConfig()
    security: SecurityConfig = SecurityConfig()
    features: FeaturesConfig = FeaturesConfig()

    class Config:
        json_encoders = {Path: str}


def load_config(config_file: str | Path = None) -> dict[str, Any]:
    """Load configuration from file.

    Args:
        config_file: Path to the configuration file. If None, uses default location.

    Returns:
        Dictionary containing the configuration.
    """
    config_path = Path(config_file) if config_file else CONFIG_FILE

    # Return default config if file doesn't exist
    if not config_path.exists():
        logger.warning(f"Config file {config_path} not found, using defaults")
        return DEFAULT_CONFIG

    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        # Merge with defaults to ensure all keys exist
        merged_config = {**DEFAULT_CONFIG, **config}

        # Validate the configuration
        validate_config(merged_config)

        return merged_config

    except json.JSONDecodeError:
        logger.exception("Invalid JSON in config file {config_path}:")
        return DEFAULT_CONFIG
    except Exception:
        logger.exception("Error loading config from {config_path}:")
        return DEFAULT_CONFIG


def save_config(config: dict[str, Any], config_file: str | Path = None) -> bool:
    """Save configuration to file.

    Args:
        config: Configuration dictionary to save.
        config_file: Path to save the configuration file. If None, uses default location.

    Returns:
        True if the configuration was saved successfully, False otherwise.
    """
    config_path = Path(config_file) if config_file else CONFIG_FILE

    try:
        # Ensure the directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Validate before saving
        validate_config(config)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        return True
    except Exception:
        logger.exception("Error saving config to {config_path}:")
        return False


def validate_config(config: dict[str, Any]) -> bool:
    """Validate configuration against the schema.

    Args:
        config: Configuration dictionary to validate.

    Returns:
        True if the configuration is valid, raises ValidationError otherwise.

    Raises:
        pydantic.ValidationError: If the configuration is invalid.
    """
    try:
        AppConfig(**config)
        return True
    except ValidationError:
        logger.exception("Configuration validation failed:")
        raise


def get_config_path() -> Path:
    """Get the path to the configuration file.

    Returns:
        Path to the configuration file.
    """
    return CONFIG_FILE


def get_config_dir() -> Path:
    """Get the configuration directory.

    Returns:
        Path to the configuration directory.
    """
    return CONFIG_DIR


def get_config_value(key: str, default: Any = None, config_file: str | Path = None) -> Any:
    """Get a specific configuration value.

    Args:
        key: Dot-notation key path (e.g., 'server.port').
        default: Default value if key not found.
        config_file: Path to configuration file.

    Returns:
        The configuration value or default.
    """
    config = load_config(config_file)

    # Navigate the nested dictionary using dot notation
    keys = key.split(".")
    value = config

    try:
        for k in keys:
            value = value[k]
        return value
    except (KeyError, TypeError):
        return default


def set_config_value(key: str, value: Any, config_file: str | Path = None) -> bool:
    """Set a specific configuration value.

    Args:
        key: Dot-notation key path (e.g., 'server.port').
        value: Value to set.
        config_file: Path to configuration file.

    Returns:
        True if successfully saved, False otherwise.
    """
    config = load_config(config_file)

    # Navigate and set the nested dictionary using dot notation
    keys = key.split(".")
    current = config

    # Navigate to the parent of the target key
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    # Set the final key
    current[keys[-1]] = value

    # Save the updated configuration
    return save_config(config, config_file)
