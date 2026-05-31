"""Entry point for USB camera helper (PyInstaller sidecar or dev)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


def _load_camera_main():
    import importlib.util

    repo = Path(__file__).resolve().parent
    if getattr(sys, "frozen", False):
        script = Path(sys._MEIPASS) / "scripts" / "windows_camera_server.py"
        sys.path.insert(0, str(Path(sys._MEIPASS)))
        sys.path.insert(0, str(Path(sys._MEIPASS) / "src"))
    else:
        script = repo / "scripts" / "windows_camera_server.py"
        sys.path.insert(0, str(repo))
        sys.path.insert(0, str(repo / "src"))

    os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
    spec = importlib.util.spec_from_file_location("windows_camera_server", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load camera server from {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main


def main() -> None:
    camera_main = _load_camera_main()
    asyncio.run(camera_main())


if __name__ == "__main__":
    main()
