"""Generate llms.txt and llms-full.txt from the fleet documentation hub."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DEFAULT_BASE_URL = "https://github.com/sandraschi/devices-mcp"

# Sources for llms-full.txt (repo-relative paths)
FULL_DOC_SOURCES: list[str] = [
    "README.md",
    "INSTALL.md",
    "docs/README.md",
    "docs/ARCHITECTURE.md",
    "docs/DESKTOP.md",
    "docs/CONFIGURATION.md",
    "docs/TOOLS.md",
    "docs/DEVELOPMENT.md",
    "docs/TROUBLESHOOTING.md",
    "AGENTS.md",
]


def _repo_version() -> str:
    try:
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
        if match:
            return match.group(1)
    except OSError:
        pass
    return "beta"


def _strip_html_blocks(markdown: str) -> str:
    """Remove HTML badge blocks from README for plain-text LLM consumption."""
    lines = markdown.splitlines()
    out: list[str] = []
    in_html = False
    for line in lines:
        if line.strip().startswith("<"):
            in_html = True
            continue
        if in_html and not line.strip():
            in_html = False
            continue
        if not in_html:
            out.append(line)
    return "\n".join(out).strip() + "\n"


def _read_doc(rel_path: str) -> str:
    path = REPO_ROOT / rel_path
    if not path.exists():
        logger.warning("llms-full source missing: %s", rel_path)
        return f"<!-- missing: {rel_path} -->\n"
    text = path.read_text(encoding="utf-8")
    if rel_path == "README.md":
        text = _strip_html_blocks(text)
    return text


def generate_navigation(base_url: str = DEFAULT_BASE_URL) -> str:
    """Concise llms.txt index (llmstxt.org style)."""
    version = _repo_version()
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    base = base_url.rstrip("/")
    return f"""# devices-mcp
> Beta home IoT: MCP tools (FastMCP 3.2) + FastAPI/React dashboard + optional Windows Tauri installer.
> Version: {version} · Generated: {ts}
> Repo: {base} · Default branch: **main** (do not use legacy `master`)

## Status
- Beta — not production-hardened; requires `config.yaml` for LAN devices.
- Three delivery legs: MCP · webapp · desktop (see Architecture).

## Core docs
- [README]({base}/blob/main/README.md): Overview, TOC, quick install, ports.
- [INSTALL]({base}/blob/main/INSTALL.md): Desktop NSIS, MCPB, clone, NSSM.
- [docs index]({base}/blob/main/docs/README.md): Documentation map.
- [Architecture]({base}/blob/main/docs/ARCHITECTURE.md): Three legs, sidecars, single backend :10717.
- [Desktop]({base}/blob/main/docs/DESKTOP.md): Tauri installer, splash, NSSM coexistence.
- [Configuration]({base}/blob/main/docs/CONFIGURATION.md): config.yaml, Vienna preset, logging default path, local LLM URLs.
- [Tools]({base}/blob/main/docs/TOOLS.md): MCP portmanteau families + stdio snippet.
- [Development]({base}/blob/main/docs/DEVELOPMENT.md): uv, just, PyInstaller, Tauri build.
- [Troubleshooting]({base}/blob/main/docs/TROUBLESHOOTING.md): White screen, logs, firewall.
- [AGENTS]({base}/blob/main/AGENTS.md): Agent startup, ports, repo layout.
- [Full corpus]({base}/blob/main/llms-full.txt): Concatenated markdown above.

## Web dashboard (leg 2)
- URL: http://127.0.0.1:10717/app/
- Settings → Logging: default `%USERPROFILE%\\.local\\share\\devices-mcp\\devices-mcp.log`
- Settings → Local LLM: Ollama (11434), LM Studio (1234); Chat uses same catalog.

## Ports
| Port | Service |
|------|---------|
| 10717 | FastAPI backend + SPA `/app/` |
| 10716 | Vite dev only |
| 10715 | Camera sidecar (optional) |

## Releases ({base}/releases)
- `devices-mcp.mcpb` — MCP leg
- `Devices-MCP-*-x64-setup.exe` — desktop leg (~247 MB with sidecars)
- `Devices-MCP-*-windows-x64.zip` — portable

## MCP entry
- Module: `devices_mcp.server_v2` (stdio / HTTP)
- Package root: `src/devices_mcp/`
"""


def generate_full_documentation(base_url: str = DEFAULT_BASE_URL) -> str:
    """llms-full.txt: stitched fleet docs for LLM context."""
    version = _repo_version()
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    parts = [
        "# devices-mcp — full documentation corpus",
        "",
        f"Generated: {ts} · Version: {version} · Source: {base_url}",
        "",
        "This file is auto-generated. Prefer linked markdown on `main` for edits.",
        "",
    ]
    for rel in FULL_DOC_SOURCES:
        body = _read_doc(rel)
        parts.append(f"\n\n---\n\n## Source: `{rel}`\n\n")
        parts.append(body)
    return "\n".join(parts)


class LLMsTxtGenerator:
    """Backward-compatible wrapper for CLI."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        self.base_url = base_url.rstrip("/")

    def generate_navigation(self) -> str:
        return generate_navigation(self.base_url)

    def generate_full_documentation(self) -> str:
        return generate_full_documentation(self.base_url)

    def write_files(self, output_dir: str | Path) -> None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        (output_path / "llms.txt").write_text(self.generate_navigation(), encoding="utf-8")
        (output_path / "llms-full.txt").write_text(self.generate_full_documentation(), encoding="utf-8")


def generate_llms_txt(output_dir: str | Path, base_url: str | None = None) -> None:
    if base_url is None:
        base_url = DEFAULT_BASE_URL
    LLMsTxtGenerator(base_url=base_url).write_files(output_dir)


if __name__ == "__main__":
    generate_llms_txt(REPO_ROOT)
