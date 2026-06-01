"""Entry point for Devices MCP web dashboard (PyInstaller sidecar or dev)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _configure_paths() -> None:
    if getattr(sys, "frozen", False):
        root = Path(sys._MEIPASS)
        sys.path.insert(0, str(root))
        # Prefer install/portable dir for config.yaml; fall back to MEIPASS for bundled assets.
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "config.yaml").exists():
            os.chdir(exe_dir)
        else:
            os.chdir(root)
        os.environ.setdefault("TAPO_MCP_SKIP_HARDWARE_INIT", "true")
        os.environ.setdefault("TAPO_MCP_LAZY_INIT", "true")
        os.environ.setdefault("DEVICES_MCP_PACKAGED", "1")
    else:
        repo = Path(__file__).resolve().parent
        sys.path.insert(0, str(repo / "src"))
        sys.path.insert(0, str(repo / "web-sota"))
        os.chdir(repo / "web-sota")

    os.environ.setdefault("WINDOWS_CAMERA_SERVER_URL", "http://127.0.0.1:10715")


def main() -> None:
    _configure_paths()

    from backend.server import WebServer

    parser = argparse.ArgumentParser(description="Devices MCP web dashboard backend")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=10717)
    args = parser.parse_args()

    WebServer().run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
