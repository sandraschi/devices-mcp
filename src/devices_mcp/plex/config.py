"""
PlexMCP Configuration Management

Handles configuration from environment variables and JSON files
for Plex server connection settings.
"""

import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO", format_string: str | None = None) -> None:
    """
    Configure logging for the entire application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Custom format string for log messages
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Get or create root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove any existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Set specific loggers to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("plexapi").setLevel(logging.WARNING)


class PlexConfig(BaseModel):
    """Configuration for Plex server connection"""

    # Server connection
    server_url: str = Field(default="http://localhost:32400", description="Plex server URL")
    plex_token: str = Field(description="Plex authentication token")
    username: str | None = Field(default=None, description="Plex username (if using basic auth)")
    password: str | None = Field(default=None, description="Plex password (if using basic auth)")

    # Request settings
    timeout: int = Field(default=30, description="Request timeout in seconds")

    @field_validator("server_url")
    @classmethod
    def validate_server_url(cls, v):
        """Ensure server URL has proper format"""
        if not v.startswith(("http://", "https://")):
            return f"http://{v}"
        return v.rstrip("/")

    @field_validator("plex_token")
    @classmethod
    def validate_plex_token(cls, v):
        """Ensure Plex token is provided"""
        if not v or len(v.strip()) == 0:
            raise ValueError("PLEX_TOKEN is required")
        return v.strip()

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v):
        """Ensure timeout is reasonable"""
        return max(5, min(300, v))  # 5-300 seconds

    @classmethod
    def load_config(cls, config_file: str | None = None) -> "PlexConfig":
        """
        Load configuration from environment variables and optional JSON file.

        Priority order:
        1. Environment variables (highest priority)
        2. JSON configuration file
        3. Default values (lowest priority)

        Args:
            config_file: Optional path to JSON config file

        Returns:
            Initialized PlexConfig instance
        """
        # Load environment variables - try multiple possible paths
        possible_env_paths = [
            Path(__file__).parent.parent.parent / ".env",  # repo root
            Path.cwd() / ".env",  # current working directory
            Path(__file__).parent / ".env",  # same as config.py
            Path("D:/Dev/repos/plexmcp/.env"),  # absolute path as fallback
        ]

        env_loaded = False
        for env_path in possible_env_paths:
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
                env_loaded = True
                break

        if not env_loaded:
            # Fallback: try loading from any .env in current dir
            load_dotenv()

        # Start with default values
        config_data = {}

        # Load from JSON file if provided
        if config_file:
            config_path = Path(config_file)
            if config_path.exists():
                try:
                    with open(config_path, encoding="utf-8") as f:
                        file_data = json.load(f)
                        config_data.update(file_data)
                except (OSError, json.JSONDecodeError) as e:
                    print(f"Warning: Could not load config file {config_file}: {e}")

        # Override with environment variables
        env_mappings = {
            "PLEX_SERVER_URL": "server_url",
            "PLEX_TOKEN": "plex_token",
            "PLEX_USERNAME": "username",
            "PLEX_PASSWORD": "password",
            "PLEX_TIMEOUT": "timeout",
        }

        for env_var, config_key in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                # Convert to appropriate type
                if config_key == "timeout":
                    try:
                        config_data[config_key] = int(env_value)
                    except ValueError:
                        logger.warning("Invalid integer value for %s: %s", env_var, env_value)
                else:
                    config_data[config_key] = env_value

        return cls(**config_data)

    @property
    def has_basic_auth(self) -> bool:
        """Check if basic authentication is configured"""
        return bool(self.username and self.password)

    @property
    def base_url(self) -> str:
        """Get base URL for Plex server"""
        return self.server_url


def get_settings() -> PlexConfig:
    """Get the application settings.

    This function loads settings from environment variables and returns
    a PlexConfig instance with the current configuration.

    Returns:
        PlexConfig: The application configuration
    """
    return PlexConfig.load_config()
