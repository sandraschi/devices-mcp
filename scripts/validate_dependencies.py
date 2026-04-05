#!/usr/bin/env python3
"""
Dependency Validator - Checks all required libraries before server starts.

Prevents the frustrating "it worked yesterday" scenario by validating
all dependencies on startup and providing clear error messages.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check all required dependencies and provide actionable errors."""
    logger.info("=" * 70)
    logger.info("VALIDATION: DEPENDENCY VALIDATION - Smart Home Dashboard")
    logger.info("=" * 70)

    missing = []
    issues = []

    # Core dependencies
    checks = [
        ("fastmcp", "FastMCP (MCP server)", "pip install fastmcp"),
        ("pydantic", "Pydantic (data validation)", "pip install pydantic"),
        ("fastapi", "FastAPI (web framework)", "pip install fastapi"),
        ("uvicorn", "Uvicorn (ASGI server)", "pip install uvicorn"),
        ("jinja2", "Jinja2 (templates)", "pip install jinja2"),
    ]

    # Hardware-specific dependencies
    hardware_checks = [
        ("pytapo", "PyTapo (Tapo C200 cameras)", "pip install pytapo", "Tapo Cameras"),
        ("tapo", "Tapo Library (P115 plugs)", "pip install tapo", "Tapo P115 Smart Plugs"),
        ("cv2", "OpenCV (USB webcams)", "pip install opencv-python", "USB Webcams"),
        ("phue", "phue (Philips Hue)", "pip install phue", "Philips Hue Lights"),
        ("pyatmo", "pyatmo (Netatmo weather)", "pip install pyatmo", "Netatmo Weather"),
        (
            "ring_doorbell",
            "Ring Library (Ring doorbell)",
            "pip install ring-doorbell",
            "Ring Doorbell",
        ),
        ("onvif", "ONVIF (camera protocol)", "pip install onvif-zeep", "ONVIF Cameras"),
    ]

    # System dependencies
    system_checks = [
        ("psycopg2", "psycopg2 (database)", "pip install psycopg2-binary", "Database"),
        ("psutil", "psutil (system monitoring)", "pip install psutil", "System Monitoring"),
        ("aiohttp", "aiohttp (async HTTP)", "pip install aiohttp", "HTTP Client"),
        ("PIL", "Pillow (image processing)", "pip install pillow", "Image Processing"),
    ]

    logger.info("CORE: CORE DEPENDENCIES:")
    logger.info("-" * 70)
    for module, name, install_cmd in checks:
        try:
            __import__(module)
            logger.info(f"   SUCCESS: {name}")
        except ImportError:
            logger.exception(f"   ERROR: {name} - MISSING!")
            missing.append((name, install_cmd))

    logger.info("HARDWARE: HARDWARE DEPENDENCIES:")
    logger.info("-" * 70)
    for module, name, install_cmd, hardware in hardware_checks:
        try:
            __import__(module)
            logger.info(f"   SUCCESS: {name} ({hardware})")
        except ImportError:
            logger.warning(f"   WARNING: {name} - MISSING (affects: {hardware})")
            issues.append((name, install_cmd, hardware))

    logger.info("SYSTEM DEPENDENCIES:")
    logger.info("-" * 70)
    for module, name, install_cmd, feature in system_checks:
        try:
            __import__(module)
            logger.info(f"   SUCCESS: {name}")
        except ImportError:
            logger.exception(f"   ERROR: {name} - MISSING!")
            missing.append((name, install_cmd))

    logger.info("=" * 70)

    if missing:
        logger.error("CRITICAL MISSING DEPENDENCIES:")
        logger.error("-" * 70)
        for name, install_cmd in missing:
            logger.error(f"   {name}")
            logger.error(f"      Fix: {install_cmd}")
        logger.error("CRITICAL: Server may not start! Install critical dependencies first.")
        return False

    if issues:
        logger.warning("OPTIONAL HARDWARE DEPENDENCIES MISSING:")
        logger.warning("-" * 70)
        for name, install_cmd, hardware in issues:
            logger.warning(f"   {name} - {hardware} won't work")
            logger.warning(f"      Fix: {install_cmd}")
        logger.info("Server will start, but some hardware won't be available.")
        logger.info("   Install missing dependencies to enable full functionality.")
        return True  # Can still start

    logger.info("SUCCESS: ALL DEPENDENCIES SATISFIFIED!")
    logger.info("   Server is ready for full operation.")
    logger.info("=" * 70)
    return True


if __name__ == "__main__":
    success = check_dependencies()
    sys.exit(0 if success else 1)
