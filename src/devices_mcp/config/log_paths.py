"""Default log directory and path resolution (web UI, MCP server, NSSM, Tauri)."""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_LOG_FILENAME = "devices-mcp.log"


def default_log_directory() -> Path:
    """User-writable log directory (created on demand)."""
    return Path.home() / ".local" / "share" / "devices-mcp"


def default_log_file_path() -> Path:
    return (default_log_directory() / DEFAULT_LOG_FILENAME).resolve()


def resolve_log_file_path(config: dict[str, Any] | None = None) -> Path:
    """Resolve logging.file for dev, PyInstaller sidecar, NSSM service, and Tauri install."""
    if config is None:
        try:
            from devices_mcp.config import get_config

            config = get_config() or {}
        except Exception:
            config = {}

    raw = (config.get("logging") or {}).get("file") or DEFAULT_LOG_FILENAME
    p = Path(str(raw)).expanduser()
    if p.is_absolute():
        return p.resolve()

    search_dirs: list[Path] = []
    try:
        from devices_mcp.config import _get_config_manager

        cfg_path = _get_config_manager().config_path
        if cfg_path.exists():
            search_dirs.append(cfg_path.parent)
    except Exception:
        pass

    search_dirs.extend(
        [
            Path.cwd(),
            default_log_directory(),
            Path.home() / ".config" / "devices-mcp",
        ]
    )
    if getattr(sys, "frozen", False):
        search_dirs.insert(0, Path(sys.executable).resolve().parent)
    if os.name == "nt":
        program_data = os.environ.get("PROGRAMDATA")
        if program_data:
            search_dirs.append(Path(program_data) / "devices-mcp")

    for directory in search_dirs:
        if not directory or not str(directory):
            continue
        candidate = (directory / p).resolve()
        if candidate.exists():
            return candidate

    default_dir = default_log_directory()
    default_dir.mkdir(parents=True, exist_ok=True)
    return (default_dir / p.name).resolve()


def touch_log_file(path: Path | None = None, config: dict[str, Any] | None = None) -> Path:
    """Ensure log file and parent directory exist."""
    target = path or resolve_log_file_path(config)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.touch()
    return target


def configure_root_file_logging(config: dict[str, Any] | None = None) -> Path:
    """Attach a rotating file handler to the root logger at the resolved log path."""
    log_path = touch_log_file(config=config)
    log_cfg = (config or {}).get("logging") or {}
    if config is None:
        try:
            from devices_mcp.config import get_config

            log_cfg = (get_config() or {}).get("logging") or {}
        except Exception:
            log_cfg = {}

    max_mb = int(log_cfg.get("max_size", log_cfg.get("max_size_mb", 10)))
    backup = int(log_cfg.get("backup_count", 5))
    resolved = str(log_path.resolve())

    root = logging.getLogger()
    for handler in root.handlers:
        if isinstance(handler, logging.handlers.RotatingFileHandler):
            if getattr(handler, "baseFilename", None) == resolved:
                return log_path

    formatter = logging.Formatter(log_cfg.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    file_handler = logging.handlers.RotatingFileHandler(
        resolved,
        maxBytes=max_mb * 1024 * 1024,
        backupCount=backup,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    root.info("File logging active: %s (%sMB x %s)", resolved, max_mb, backup)
    return log_path
