"""
Configuration module for Devices MCP.

This module provides configuration models and utilities for the Devices MCP server.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import Any, TypeVar

import yaml

logger = logging.getLogger(__name__)

from .models import (
    CameraConfig,
    LoggingSettings,
    SecuritySettings,
    ServerConfig,
    StorageSettings,
    WebUISettings,
)

T = TypeVar("T")


class ConfigManager:
    """Manages configuration loading and saving."""

    def __init__(self, config_path: str | Path | None = None):
        """Initialize the config manager.

        Args:
            config_path: Path to the configuration file. If None, looks for config in default locations.
        """
        self.config_path = self._find_config_file(config_path)
        self._config_cache: dict[str, Any] = {}

    def _find_config_file(self, config_path: str | Path | None = None) -> Path:
        """Find the configuration file.

        Args:
            config_path: Explicit config file path. If None, searches in default locations.

        Returns:
            Path to the configuration file.
        """
        if config_path and Path(config_path).exists():
            return Path(config_path)

        # Get the module directory to find the repo root config
        module_dir = Path(__file__).parent.parent.parent.parent  # Go up to repo root
        repo_config = module_dir / "config.yaml"

        # User-writable config directory
        user_config_dir = Path("~/.config/devices-mcp").expanduser()
        user_config_file = user_config_dir / "config.yaml"

        # Search paths in order of preference
        search_paths = [
            Path("/app/config.yaml"),  # Docker container path (highest priority in container)
            repo_config,  # Repo root config file (Highest priority in local dev)
            user_config_file,  # User config directory
            Path("config.yaml"),  # Current directory
            Path("config.yml"),
            Path("/etc/devices-mcp/config.yaml"),  # System config (Linux)
        ]

        for path in search_paths:
            if path.exists():
                logger.info(f"Found config file at: {path}")
                return path

        # Log all searched paths for debugging
        logger.warning("Config file not found. Searched paths:")
        for path in search_paths:
            logger.warning(f"  - {path} (exists: {path.exists()})")

        # If no config found, try to create one from the repo template
        if repo_config.exists():
            # Copy repo config to user directory
            user_config_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(repo_config, user_config_file)
                return user_config_file
            except Exception:
                # If copying fails, just use the repo config
                return repo_config

        # Last resort: create a minimal default config in user directory
        user_config_dir.mkdir(parents=True, exist_ok=True)
        self.save_default_config(user_config_file)
        return user_config_file

    def save_default_config(self, path: str | Path) -> None:
        """Save a default configuration file.

        Args:
            path: Path where to save the default configuration.
        """
        # Get user-writable directories
        user_data_dir = Path("~/.local/share/devices-mcp").expanduser()
        user_data_dir.mkdir(parents=True, exist_ok=True)

        from .vienna_defaults import get_vienna_default_config

        default_config = get_vienna_default_config()
        default_config.setdefault("logging", {})
        default_config["logging"].update(
            {
                "file": str(user_data_dir / "devices-mcp.log"),
                "max_size_mb": 10,
                "backup_count": 5,
            }
        )
        default_config.setdefault("storage", {})
        default_config["storage"].update(
            {
                "recordings_dir": str(user_data_dir / "recordings"),
                "snapshots_dir": str(user_data_dir / "snapshots"),
                "temp_dir": str(user_data_dir / "temp"),
            }
        )

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, "w") as f:
                yaml.safe_dump(default_config, f, default_flow_style=False, sort_keys=False)
        except PermissionError:
            # If we can't write to the specified path, create a warning but don't crash
            pass

    def load_config(self) -> dict[str, Any]:
        """Load configuration from file.

        Returns:
            Dictionary containing the configuration.
        """
        if self._config_cache:
            return self._config_cache

        if not self.config_path.exists():
            # Create a minimal in-memory config
            return {
                "host": "0.0.0.0",  # nosec B104
                "port": 8080,
                "debug": False,
                "cameras": [],
                "log_level": "INFO",
            }

        try:
            with open(self.config_path, encoding="utf-8") as f:
                if self.config_path.suffix.lower() in (".yaml", ".yml"):
                    config = yaml.safe_load(f)
                elif self.config_path.suffix.lower() == ".json":
                    config = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {self.config_path.suffix}")

            # Ensure config is a dictionary
            if not isinstance(config, dict):
                config = {}

            self._config_cache = config
            return config

        except Exception:
            # Return minimal config on error
            return {
                "host": "0.0.0.0",  # nosec B104
                "port": 8080,
                "debug": False,
                "cameras": [],
                "log_level": "INFO",
            }

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot notation key.

        Args:
            key: Dot notation key (e.g., 'web.port').
            default: Default value if key is not found.

        Returns:
            The configuration value or default if not found.
        """
        config = self.load_config()
        keys = key.split(".")
        value = config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def get_model(self, model_class: type[T]) -> T:
        """Get a configuration model instance.

        Args:
            model_class: The configuration model class.

        Returns:
            An instance of the model class populated with configuration values.
        """
        config = self.load_config()
        model_name = model_class.__name__.lower()

        if model_name == "serverconfig":
            # Special handling for ServerConfig since it contains nested models
            web_config = config.get("web", {})
            security_config = config.get("security", {})
            security_integrations = config.get("security_integrations", {})

            # Merge security_integrations into security_config
            if security_config and security_integrations:
                security_config = dict(security_config)
                security_config["integrations"] = security_integrations
            elif security_integrations:
                security_config = {"integrations": security_integrations}

            logging_config = config.get("logging", {})
            storage_config = config.get("storage", {})

            return ServerConfig(
                host=config.get("host", "0.0.0.0"),
                port=config.get("port", 8080),
                debug=config.get("debug", False),
                web=WebUISettings(**web_config) if web_config else WebUISettings(),
                security=(SecuritySettings(**security_config) if security_config else SecuritySettings()),
                logging=LoggingSettings(**logging_config) if logging_config else LoggingSettings(),
                storage=StorageSettings(**storage_config) if storage_config else StorageSettings(),
                camera_scan_interval=config.get("camera_scan_interval", 300),
                max_workers=config.get("max_workers", 4),
                request_timeout=config.get("request_timeout", 30),
                log_level=config.get("log_level", "INFO"),
                default_camera=config.get("default_camera"),
                cors_origins=config.get("cors_origins", ["*"]),
                data_dir=Path(config.get("data_dir", "data")),
                cache_dir=Path(config.get("cache_dir", "cache")),
                api_key=config.get("api_key"),
            )

        # Map model class names to config keys (some don't match exactly)
        model_key_map = {
            "weathersettings": "weather",
            "energysettings": "energy",
            "lightingsettings": "lighting",
        }
        config_key = model_key_map.get(model_name, model_name)

        if hasattr(model_class, "model_validate"):
            # Handle Pydantic v2 models
            model_config = config.get(config_key, {})
            return model_class.model_validate(model_config)
        if hasattr(model_class, "parse_obj"):
            # Handle Pydantic v1 models
            model_config = config.get(config_key, {})
            return model_class.parse_obj(model_config)
        # Handle dataclasses
        model_config = config.get(config_key, {})
        return model_class(**model_config)


# Lazy-loaded global configuration instance
_config_manager_instance: ConfigManager | None = None


def _get_config_manager() -> ConfigManager:
    """Get the global config manager instance (lazy initialization)."""
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()
    return _config_manager_instance


# Shortcut functions with lazy loading
def get_config() -> dict[str, Any]:
    return _get_config_manager().load_config()


def get_setting(key: str, default: Any = None) -> Any:
    return _get_config_manager().get(key, default)


def get_model[T](model_class: type[T]) -> T:
    return _get_config_manager().get_model(model_class)


# Export models and utilities
__all__ = [
    "CameraConfig",
    "ConfigManager",
    "LoggingSettings",
    "SecuritySettings",
    "ServerConfig",
    "StorageSettings",
    "WebUISettings",
    "config_manager",
    "get_config",
    "get_model",
    "get_setting",
]
