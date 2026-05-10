"""
Config file read/write API for the Settings page.

Provides endpoints to view and edit the raw config.yaml from the web UI.
"""

import logging
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Body

from devices_mcp.config import ConfigManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Config"])


def _resolve_config_path() -> Path:
    manager = ConfigManager()
    return manager.config_path


@router.get("/api/config")
async def get_config() -> dict[str, Any]:
    """Return the full config.yaml contents as raw YAML text and parsed JSON.

    ## Return Format
    {"success": bool, "path": str, "yaml": str, "json": dict}
    """
    try:
        path = _resolve_config_path()
        raw = path.read_text(encoding="utf-8")
        try:
            parsed = yaml.safe_load(raw)
            if not isinstance(parsed, dict):
                parsed = {}
        except yaml.YAMLError:
            parsed = {}

        return {
            "success": True,
            "path": str(path),
            "yaml": raw,
            "json": parsed,
        }
    except Exception as e:
        logger.exception("Failed to read config")
        return {"success": False, "error": str(e)}


@router.put("/api/config")
async def update_config(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Replace the config.yaml contents with the supplied YAML text.

    Body: {"yaml": "<full YAML string>"}

    ## Return Format
    {"success": bool, "message": str}
    """
    try:
        yaml_text = payload.get("yaml", "")
        if not yaml_text.strip():
            return {"success": False, "error": "Empty YAML body"}

        try:
            parsed = yaml.safe_load(yaml_text)
            if not isinstance(parsed, dict):
                return {"success": False, "error": "Config must be a YAML dictionary"}
        except yaml.YAMLError as e:
            return {"success": False, "error": f"Invalid YAML: {e}"}

        path = _resolve_config_path()

        backup_path = path.with_suffix(".yaml.bak")
        try:
            backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        except Exception:
            logger.debug("Failed to create backup, continuing without it", exc_info=True)

        path.write_text(yaml_text, encoding="utf-8")
        logger.info("Config updated via web UI: %s", path)

        return {"success": True, "message": f"Config saved to {path}"}

    except Exception as e:
        logger.exception("Failed to write config")
        return {"success": False, "error": str(e)}
