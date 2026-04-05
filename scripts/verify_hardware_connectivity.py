#!/usr/bin/env python3
"""
Hardware Connectivity Verification Script

Tests connectivity to ALL hardware devices:
- Tapo cameras (USB and IP)
- Hue lighting system
- Tapo smart plugs
- Netatmo weather station
- Ring doorbell/camera

This script verifies that the webapp will be functional by ensuring
all hardware devices can connect successfully.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def test_tapo_cameras():
    """Test Tapo camera connectivity."""
    logger.info("Testing Tapo Cameras...")
    try:
        from devices_mcp.camera.manager import CameraManager
        from devices_mcp.core.hardware_init import HardwareInitializer

        camera_manager = CameraManager()
        initializer = HardwareInitializer(camera_manager=camera_manager)

        result = await initializer._init_cameras()

        if result["success"]:
            count = result.get("count", 0)
            logger.info(f"OK - {count} Tapo cameras connected")
            return True
        error = result.get("error", "Unknown error")
        logger.info(f"FAIL - Tapo cameras: {error}")
        return False

    except Exception as e:
        logger.info(f"FAIL - Tapo cameras exception: {e}")
        return False


async def test_hue_lighting():
    """Test Philips Hue connectivity."""
    logger.info("Testing Philips Hue Lighting...")
    try:
        from devices_mcp.camera.manager import CameraManager
        from devices_mcp.core.hardware_init import HardwareInitializer

        camera_manager = CameraManager()
        initializer = HardwareInitializer(camera_manager=camera_manager)

        result = await initializer._init_hue_bridge()

        if result["success"]:
            lights = result.get("lights_count", 0)
            groups = result.get("groups_count", 0)
            scenes = result.get("scenes_count", 0)
            logger.info(f"OK - Hue: {lights} lights, {groups} groups, {scenes} scenes")
            return True
        error = result.get("error", "Unknown error")
        if "not configured" in error.lower():
            logger.info("SKIP - Philips Hue not configured")
            return True  # Not a failure, just not configured
        logger.info(f"FAIL - Philips Hue: {error}")
        return False

    except Exception as e:
        logger.info(f"FAIL - Philips Hue exception: {e}")
        return False


async def test_tapo_lighting():
    """Test Tapo smart lighting connectivity."""
    logger.info("Testing Tapo Smart Lighting...")
    try:
        from devices_mcp.camera.manager import CameraManager
        from devices_mcp.core.hardware_init import HardwareInitializer

        camera_manager = CameraManager()
        initializer = HardwareInitializer(camera_manager=camera_manager)

        result = await initializer._init_tapo_lighting()

        if result["success"]:
            devices = result.get("devices_count", 0)
            logger.info(f"OK - {devices} Tapo lights connected")
            return True
        error = result.get("error", "Unknown error")
        if "not configured" in error.lower():
            logger.info("SKIP - Tapo lighting not configured")
            return True  # Not a failure, just not configured
        logger.info(f"FAIL - Tapo lighting: {error}")
        return False

    except Exception as e:
        logger.info(f"FAIL - Tapo lighting exception: {e}")
        return False


async def test_tapo_plugs():
    """Test Tapo smart plug connectivity."""
    logger.info("Testing Tapo Smart Plugs...")
    try:
        from devices_mcp.camera.manager import CameraManager
        from devices_mcp.core.hardware_init import HardwareInitializer

        camera_manager = CameraManager()
        initializer = HardwareInitializer(camera_manager=camera_manager)

        result = await initializer._init_tapo_plugs()

        if result["success"]:
            devices = result.get("devices_count", 0)
            logger.info(f"OK - {devices} Tapo plugs connected")
            return True
        error = result.get("error", "Unknown error")
        if "not configured" in error.lower():
            logger.info("SKIP - Tapo plugs not configured")
            return True  # Not a failure, just not configured
        logger.info(f"FAIL - Tapo plugs: {error}")
        return False

    except Exception as e:
        logger.info(f"FAIL - Tapo plugs exception: {e}")
        return False


async def test_netatmo_weather():
    """Test Netatmo weather station connectivity."""
    logger.info("Testing Netatmo Weather Station...")
    try:
        from devices_mcp.camera.manager import CameraManager
        from devices_mcp.core.hardware_init import HardwareInitializer

        camera_manager = CameraManager()
        initializer = HardwareInitializer(camera_manager=camera_manager)

        result = await initializer._init_netatmo()

        if result["success"]:
            stations = result.get("stations_count", 0)
            modules = result.get("modules_count", 0)
            logger.info(f"OK - Netatmo: {stations} stations, {modules} modules")
            return True
        error = result.get("error", "Unknown error")
        if "not configured" in error.lower() or "not enabled" in error.lower():
            logger.info("SKIP - Netatmo not configured/enabled")
            return True  # Not a failure, just not configured
        logger.info(f"FAIL - Netatmo: {error}")
        return False

    except Exception as e:
        logger.info(f"FAIL - Netatmo exception: {e}")
        return False


async def test_ring_doorbell():
    """Test Ring doorbell/camera connectivity."""
    logger.info("Testing Ring Doorbell...")
    try:
        from devices_mcp.camera.manager import CameraManager
        from devices_mcp.core.hardware_init import HardwareInitializer

        camera_manager = CameraManager()
        initializer = HardwareInitializer(camera_manager=camera_manager)

        result = await initializer._init_ring()

        if result["success"]:
            doorbells = result.get("doorbells_count", 0)
            cameras = result.get("cameras_count", 0)
            logger.info(f"OK - Ring: {doorbells} doorbells, {cameras} cameras")
            return True
        error = result.get("error", "Unknown error")
        if "not configured" in error.lower() or "not enabled" in error.lower():
            logger.info("SKIP - Ring not configured/enabled")
            return True  # Not a failure, just not configured
        logger.info(f"FAIL - Ring: {error}")
        return False

    except Exception as e:
        logger.info(f"FAIL - Ring exception: {e}")
        return False


def test_usb_camera_server():
    """Test USB camera server connectivity."""
    logger.info("Testing USB Camera Server...")
    try:
        import platform
        import socket

        if platform.system() != "Windows":
            logger.info("SKIP - USB camera server (Windows only)")
            return True

        # Check if camera server is running
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", 10715))
        sock.close()

        if result == 0:
            logger.info("OK - USB camera server running on port 10715")
            return True
        logger.info("FAIL - USB camera server not running on port 10715")
        logger.info("      Run: python windows_camera_server.py")
        return False

    except Exception as e:
        logger.info(f"FAIL - USB camera server test exception: {e}")
        return False


def test_configuration():
    """Test hardware configuration validity."""
    logger.info("Testing Hardware Configuration...")
    try:
        from devices_mcp.config import get_config

        config = get_config()

        # Check cameras
        cameras = config.get("cameras", {})
        camera_count = len(cameras)
        logger.info(f"OK - Configuration loaded: {camera_count} cameras configured")

        # Check optional systems
        lighting = config.get("lighting", {})
        hue_configured = bool(lighting.get("philips_hue", {}).get("bridge_ip"))
        tapo_lights = len(lighting.get("tapo_lighting", {}).get("devices", []))
        logger.info(
            f"OK - Lighting: Hue {'configured' if hue_configured else 'not configured'}, {tapo_lights} Tapo lights"
        )

        energy = config.get("energy", {})
        tapo_plugs = len(energy.get("tapo_p115", {}).get("devices", []))
        logger.info(f"OK - Energy: {tapo_plugs} Tapo plugs configured")

        weather = config.get("weather", {})
        netatmo_enabled = weather.get("integrations", {}).get("netatmo", {}).get("enabled", False)
        logger.info(f"OK - Weather: Netatmo {'enabled' if netatmo_enabled else 'disabled'}")

        ring_enabled = config.get("ring", {}).get("enabled", False)
        logger.info(f"OK - Ring: {'enabled' if ring_enabled else 'disabled'}")

        return True

    except Exception as e:
        logger.info(f"FAIL - Configuration test exception: {e}")
        return False


async def main():
    """Run all hardware connectivity tests."""
    logger.info("=" * 60)
    logger.info("HARDWARE CONNECTIVITY VERIFICATION")
    logger.info("=" * 60)
    logger.info("Testing connectivity to ALL hardware devices...")
    logger.info("This ensures the webapp will be functional.\n")

    # Run tests
    tests = [
        ("Configuration", test_configuration),
        ("USB Camera Server", test_usb_camera_server),
        ("Tapo Cameras", test_tapo_cameras),
        ("Philips Hue", test_hue_lighting),
        ("Tapo Lighting", test_tapo_lighting),
        ("Tapo Plugs", test_tapo_plugs),
        ("Netatmo Weather", test_netatmo_weather),
        ("Ring Doorbell", test_ring_doorbell),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.info(f"FAIL - {test_name} test crashed: {e}")
            results.append((test_name, False))

    logger.info("\n" + "=" * 60)
    logger.info("HARDWARE CONNECTIVITY RESULTS")
    logger.info("=" * 60)

    # Count results
    passed = sum(1 for _, result in results if result)
    total = len(results)

    # Critical systems (must work)
    critical_systems = ["Configuration", "USB Camera Server", "Tapo Cameras"]
    critical_passed = sum(1 for name, result in results if name in critical_systems and result)
    critical_total = len(critical_systems)

    # Optional systems
    optional_systems = [
        "Philips Hue",
        "Tapo Lighting",
        "Tapo Plugs",
        "Netatmo Weather",
        "Ring Doorbell",
    ]
    optional_passed = sum(1 for name, result in results if name in optional_systems and result)
    optional_total = len(optional_systems)

    # Print results
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        marker = "PASS" if result else "FAIL"
        criticality = "(CRITICAL)" if test_name in critical_systems else "(OPTIONAL)"
        logger.info(f"{marker} {test_name:20} {status:4} {criticality}")

    logger.info("\nSUMMARY:")
    logger.info(f"- Critical Systems: {critical_passed}/{critical_total} working")
    logger.info(f"- Optional Systems: {optional_passed}/{optional_total} working")
    logger.info(f"- Total Systems:    {passed}/{total} working")

    # Determine overall status
    logger.info("\n" + "=" * 60)
    if critical_passed == critical_total:
        if passed == total:
            logger.info("SUCCESS: ALL SYSTEMS OPERATIONAL")
            logger.info("   Webapp will be fully functional.")
            return 0
        logger.info("WARNING: CORE SYSTEMS WORKING - LIMITED FUNCTIONALITY")
        logger.info("   Webapp will work but some features unavailable.")
        return 0
    logger.info("FAILURE: CRITICAL SYSTEMS FAILURE")
    logger.info("   Webapp will NOT be functional - fix critical issues first.")
    logger.info("\nCritical failures:")
    for name, result in results:
        if name in critical_systems and not result:
            logger.info(f"   - {name} failed")
    return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.info(f"\nTest suite crashed: {e}")
        sys.exit(1)
