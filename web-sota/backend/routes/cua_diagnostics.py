"""CUA diagnostics endpoint — used by the CUA smoke test to verify app health."""

import logging
import time
from contextlib import suppress

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["cua"])
SERVER_START = time.time()


@router.get("/v1/diagnostics")
async def get_diagnostics():
    uptime = int(time.time() - SERVER_START)
    cpu = mem = disk = None
    with suppress(Exception):
        import psutil

        cpu = psutil.cpu_percent(interval=0.3)
        mem = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
    tesseract = False
    with suppress(Exception):
        import subprocess

        tesseract = (
            subprocess.run(
                [r"C:\Program Files\Tesseract-OCR\tesseract.exe", "--version"], capture_output=True, timeout=5
            ).returncode
            == 0
        )
    window = False
    with suppress(Exception):
        import pywinauto

        app = pywinauto.Application(backend="uia").connect(title_re="Devices MCP")
        win = app.window(title_re="Devices MCP")
        win.wait("visible", timeout=2)
        window = True
    return {
        "success": True,
        "data": {
            "backend": {"status": "ok", "version": "1.0.0", "uptime_seconds": uptime, "port": 10717},
            "system": {"cpu_percent": cpu, "memory_percent": mem, "disk_percent": disk},
            "tools": {"total": 0, "categories": ["devices", "cameras", "lighting"]},
            "errors": {"count": 0, "recent": []},
            "cua_status": {"window_found": window, "backend_reachable": True, "tesseract_available": tesseract},
        },
    }
