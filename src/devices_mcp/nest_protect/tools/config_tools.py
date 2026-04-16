"""Configuration tools for Nest Protect MCP."""

import json
from pathlib import Path
from typing import Any

import toml
from pydantic import BaseModel, Field


class ConfigSectionParams(BaseModel):
    """Parameters for getting config section."""

    section: str | None = Field(None, description="Specific section to retrieve (optional)")


class UpdateConfigParams(BaseModel):
    """Parameters for updating config."""

    updates: dict[str, Any] = Field(..., description="Dictionary of configuration updates")
    save_to_file: bool = Field(True, description="Whether to save changes to config file")


class ResetConfigParams(BaseModel):
    """Parameters for resetting config."""

    confirm: bool = Field(False, description="Must be set to True to confirm reset")


class ExportConfigParams(BaseModel):
    """Parameters for exporting config."""

    file_path: str = Field("config/exported_config.toml", description="Path to save the config file")
    format: str = Field("toml", description="Export format (toml, json)")


class ImportConfigParams(BaseModel):
    """Parameters for importing config."""

    file_path: str = Field(..., description="Path to the config file to import")
    merge: bool = Field(True, description="Merge with existing config (True) or replace (False)")


async def get_config(section: str | None = None) -> dict[str, Any]:
    """Get current configuration or a specific section."""
    from ..state_manager import get_app_state

    try:
        state = get_app_state()
        config = state.config.model_dump()
        if section:
            return {"status": "success", "config": {section: config.get(section, {})}}
        return {"status": "success", "config": config}
    except Exception as e:
        return {"status": "error", "message": f"Failed to get config: {e!s}"}


async def update_config(updates: dict[str, Any], save_to_file: bool = True) -> dict[str, Any]:
    """Update configuration values."""
    from ..state_manager import get_app_state

    try:
        state = get_app_state()
        # Get current config as dict
        current_config = state.config.model_dump()

        # Apply updates
        for section, values in updates.items():
            if section in current_config and isinstance(current_config[section], dict) and isinstance(values, dict):
                current_config[section].update(values)
            else:
                current_config[section] = values

        # Update config object
        for key, value in current_config.items():
            setattr(state.config, key, value)

        # Save to file if requested
        if save_to_file:
            config_path = Path("config/default.toml")
            if not config_path.exists():
                config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, "w") as f:
                toml.dump(current_config, f)

        return {
            "status": "success",
            "message": "Configuration updated",
            "saved_to_file": save_to_file,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to update config: {e!s}"}


async def reset_config(confirm: bool = False) -> dict[str, Any]:
    """Reset configuration to default values."""
    if not confirm:
        return {
            "status": "error",
            "message": "Confirmation required. Set confirm=True to reset configuration.",
        }

    try:
        from ..models import ProtectConfig
        from ..state_manager import get_app_state

        state = get_app_state()
        # Reset to defaults
        state.config = ProtectConfig()

        # Save to file
        config_path = Path("config/default.toml")
        if config_path.exists():
            config_path.unlink()

        return {"status": "success", "message": "Configuration reset to defaults"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to reset config: {e!s}"}


async def export_config(file_path: str = "config/exported_config.toml", format: str = "toml") -> dict[str, Any]:
    """Export current configuration to a file."""
    from ..state_manager import get_app_state

    try:
        state = get_app_state()
        config_data = state.config.model_dump()
        export_path = Path(file_path)
        export_path.parent.mkdir(parents=True, exist_ok=True)

        if format.lower() == "json":
            with open(export_path, "w") as f:
                json.dump(config_data, f, indent=2)
        else:  # Default to TOML
            with open(export_path, "w") as f:
                toml.dump(config_data, f)

        return {
            "status": "success",
            "message": f"Configuration exported to {file_path}",
            "format": format,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to export config: {e!s}"}


async def import_config(file_path: str, merge: bool = True) -> dict[str, Any]:
    """Import configuration from a file."""
    from ..models import ProtectConfig
    from ..state_manager import get_app_state

    try:
        import_path = Path(file_path)
        if not import_path.exists():
            return {"status": "error", "message": f"File not found: {file_path}"}

        # Load the imported config
        if file_path.lower().endswith(".json"):
            with open(import_path) as f:
                imported_config = json.load(f)
        else:  # Assume TOML for other extensions
            with open(import_path) as f:
                imported_config = toml.load(f)

        state = get_app_state()
        # Get current config
        current_config = state.config.model_dump()

        # Merge or replace
        if merge:
            # Deep merge dictionaries
            def deep_merge(d1, d2):
                for k, v in d2.items():
                    if k in d1 and isinstance(d1[k], dict) and isinstance(v, dict):
                        deep_merge(d1[k], v)
                    else:
                        d1[k] = v
                return d1

            updated_config = deep_merge(current_config, imported_config)
        else:
            updated_config = imported_config

        # Update config
        state.config = ProtectConfig(**updated_config)

        # Save to default config file
        config_path = Path("config/default.toml")
        with open(config_path, "w") as f:
            toml.dump(updated_config, f)

        return {
            "status": "success",
            "message": f"Configuration imported from {file_path}",
            "merged": merge,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to import config: {e!s}"}
