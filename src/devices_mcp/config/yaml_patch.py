"""Small helpers to read/patch config.yaml from the web settings UI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from devices_mcp.config import ConfigManager


def load_config_dict() -> tuple[Path, dict[str, Any]]:
    manager = ConfigManager()
    path = manager.config_path
    if path.exists():
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        data = raw if isinstance(raw, dict) else {}
    else:
        data = {}
    return path, data


def save_config_dict(path: Path, data: dict[str, Any]) -> None:
    backup = path.with_suffix(".yaml.bak")
    if path.exists():
        try:
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        except OSError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False), encoding="utf-8")
    manager = ConfigManager()
    manager._config_cache = data
