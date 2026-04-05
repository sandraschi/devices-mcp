"""
Configuration loading and saving utilities.
"""

import json
from pathlib import Path
from typing import Any, Type, TypeVar

import yaml

from ..config import CameraConfig, ServerConfig

T = TypeVar("T")


def load_config(config_file: str = "config.yaml", config_class: Type[T] = ServerConfig) -> T:
    """
    Load configuration from a YAML or JSON file.

    Args:
        config_file: Path to the configuration file
        config_class: Configuration class to instantiate

    Returns:
        An instance of the specified configuration class

    Raises:
        FileNotFoundError: If the config file doesn't exist
        ValueError: If the config file has an unsupported extension
    """
    config_path = Path(config_file)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    with open(config_path, encoding="utf-8") as f:
        if config_path.suffix.lower() in (".yaml", ".yml"):
            config_data = yaml.safe_load(f)
        elif config_path.suffix.lower() == ".json":
            config_data = json.load(f)
        else:
            raise ValueError(f"Unsupported config file format: {config_path.suffix}")

    return config_class(**config_data)


def save_config(config: Any, config_file: str = "config.yaml", format: str = "yaml") -> None:
    """
    Save configuration to a file.

    Args:
        config: Configuration object to save
        config_file: Path to the output file
        format: Output format ('yaml' or 'json')

    Raises:
        ValueError: If an unsupported format is specified
    """
    config_path = Path(config_file)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert dataclass to dict, handling nested dataclasses
    def to_dict(obj):
        if hasattr(obj, "__dataclass_fields__"):
            return {k: to_dict(v) for k, v in obj.__dict__.items()}
        if isinstance(obj, (list, tuple)):
            return [to_dict(x) for x in obj]
        if isinstance(obj, dict):
            return {k: to_dict(v) for k, v in obj.items()}
        return obj

    config_dict = to_dict(config)

    with open(config_path, "w", encoding="utf-8") as f:
        if format.lower() == "yaml":
            yaml.dump(
                config_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
        elif format.lower() == "json":
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"Unsupported format: {format}")


def get_default_config() -> ServerConfig:
    """
    Get the default server configuration.

    Returns:
        Default ServerConfig instance
    """
    return ServerConfig()


def get_default_camera_config() -> CameraConfig:
    """
    Get the default camera configuration.

    Returns:
        Default CameraConfig instance
    """
    return CameraConfig(host="", username="", password="")
