"""Focused settings APIs (logging path, local LLM) without editing full config.yaml."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from devices_mcp.config.log_paths import (
    configure_root_file_logging,
    default_log_file_path,
    resolve_log_file_path,
    touch_log_file,
)
from devices_mcp.config.yaml_patch import load_config_dict, save_config_dict
from devices_mcp.llm.manager import PROVIDER_CATALOG, get_llm_manager
from devices_mcp.llm.providers import ProviderType

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Settings"])


class LoggingSettingsBody(BaseModel):
    file: str | None = Field(None, description="Absolute or default-relative log file path")


class LlmSettingsBody(BaseModel):
    ollama_url: str | None = Field(None, description="Ollama base URL")
    lm_studio_url: str | None = Field(None, description="LM Studio base URL (OpenAI-compatible)")
    preferred_provider: str | None = Field(None, description="ollama or lm_studio")
    reconnect: bool = Field(
        True,
        description="Re-register providers after save",
    )


@router.get("/api/settings/logging")
async def get_logging_settings() -> dict[str, Any]:
    """Current and default log file paths."""
    try:
        from devices_mcp.config import get_config

        config = get_config() or {}
        resolved = resolve_log_file_path(config)
        touch_log_file(resolved)
        return {
            "success": True,
            "file": str(resolved),
            "default_file": str(default_log_file_path()),
            "configured_file": (config.get("logging") or {}).get("file"),
            "path_exists": resolved.exists(),
            "hint": "Change path below; default works without editing config.yaml.",
        }
    except Exception as e:
        logger.exception("Failed to read logging settings")
        return {"success": False, "error": str(e)}


@router.put("/api/settings/logging")
async def update_logging_settings(body: LoggingSettingsBody) -> dict[str, Any]:
    """Persist logging.file and reattach the rotating file handler."""
    try:
        path, data = load_config_dict()
        logging_section = data.setdefault("logging", {})
        if body.file and body.file.strip():
            target = resolve_log_file_path({**data, "logging": {**logging_section, "file": body.file.strip()}})
            logging_section["file"] = str(target)
        else:
            target = default_log_file_path()
            logging_section["file"] = str(target)

        save_config_dict(path, data)
        touch_log_file(target)
        configure_root_file_logging(data)

        return {
            "success": True,
            "file": str(target),
            "message": "Log path saved. New log lines use this file.",
        }
    except Exception as e:
        logger.exception("Failed to update logging settings")
        return {"success": False, "error": str(e)}


@router.get("/api/settings/llm")
async def get_llm_settings() -> dict[str, Any]:
    """Local LLM URLs and provider catalog status."""
    try:
        from devices_mcp.config import get_config

        config = get_config() or {}
        llm = config.get("llm") or {}
        manager = get_llm_manager()
        manager.ensure_catalog_registered(config)
        providers = await manager.list_providers()
        return {
            "success": True,
            "ollama_url": llm.get("ollama_url", "http://127.0.0.1:11434"),
            "lm_studio_url": llm.get("lm_studio_url", "http://127.0.0.1:1234"),
            "preferred_provider": llm.get("preferred_provider", "ollama"),
            "providers": providers,
            "catalog": [
                {"type": pt.value, "label": label, "default_base_url": url} for pt, label, url in PROVIDER_CATALOG
            ],
        }
    except Exception as e:
        logger.exception("Failed to read LLM settings")
        return {"success": False, "error": str(e)}


@router.put("/api/settings/llm")
async def update_llm_settings(body: LlmSettingsBody) -> dict[str, Any]:
    """Save LLM URLs to config.yaml and register providers."""
    try:
        path, data = load_config_dict()
        llm = data.setdefault("llm", {})
        if body.ollama_url is not None:
            llm["ollama_url"] = body.ollama_url.strip()
        if body.lm_studio_url is not None:
            llm["lm_studio_url"] = body.lm_studio_url.strip()
        if body.preferred_provider is not None:
            llm["preferred_provider"] = body.preferred_provider.strip()

        save_config_dict(path, data)

        manager = get_llm_manager()
        manager.providers.clear()
        manager.ensure_catalog_registered(data)

        if body.reconnect:
            await manager.glom_local_providers_if_up()

        providers = await manager.list_providers()
        preferred = llm.get("preferred_provider", "ollama")
        if preferred in {p["type"] for p in providers}:
            try:
                manager.current_provider = ProviderType(preferred)
            except ValueError:
                pass

        return {
            "success": True,
            "message": "Local LLM settings saved.",
            "providers": providers,
        }
    except Exception as e:
        logger.exception("Failed to update LLM settings")
        return {"success": False, "error": str(e)}
