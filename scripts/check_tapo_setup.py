"""Check if Tapo camera needs initial setup.

Newer Tapo cameras often require initial setup through the Tapo app
before local API access works. This script checks if the camera
is set up and accessible.
"""

import logging
import sys

from pytapo import Tapo

logger = logging.getLogger(__name__)


def check_camera_status(ip, username, password):
    """Check if camera is accessible with given credentials."""
    try:
        logger.info(f"Checking camera at {ip}...")
        logger.info(f"Username: {username}")
        logger.info(f"Password: {'*' * len(password) if password else '(empty)'}")

        camera = Tapo(ip, username, password)
        info = camera.getBasicInfo()

        device_info = info.get("device_info", {})
        logger.info("\n[SUCCESS] Camera is accessible!")
        logger.info(f"Model: {device_info.get('device_model', 'Unknown')}")
        logger.info(f"Firmware: {device_info.get('firmware_version', 'Unknown')}")
        logger.info(f"Serial: {device_info.get('serial_number', 'Unknown')}")
        logger.info(f"MAC: {device_info.get('mac', 'Unknown')}")
        logger.info(f"Hostname: {device_info.get('device_alias', 'Unknown')}")

        # Check if camera is in setup mode or fully configured
        is_configured = (
            device_info.get("device_alias") and device_info.get("device_alias") != "TapoCamera"
        )
        if not is_configured:
            logger.info("\n[INFO] Camera appears to be in setup mode (default hostname)")
            logger.info("You may need to complete setup in the Tapo app first.")

        return True

    except Exception as e:
        error_msg = str(e)

        if "Temporary Suspension" in error_msg or "1800 seconds" in error_msg:
            logger.info("\n[LOCKOUT] Camera is temporarily locked out.")
            logger.info("Wait 30 minutes or power cycle the camera.")
            return "locked"

        if "Invalid authentication" in error_msg or "Invalid auth" in error_msg:
            logger.info(f"\n[FAILED] Authentication failed: {error_msg}")
            return False

        logger.info(f"\n[ERROR] Connection failed: {error_msg}")
        return False


def try_setup_combinations(ip):
    """Try common credentials after factory reset."""
    logger.info("\n" + "=" * 60)
    logger.info("Trying common credential combinations after factory reset...")
    logger.info("=" * 60)
    logger.info("\nWARNING: Too many attempts will lock the camera!")
    logger.info("Only trying safe combinations.\n")

    # Common combinations to try (in order of likelihood)
    combinations = [
        # After reset, some cameras accept cloud credentials if previously linked
        ("sandraschipal@hotmail.com", "Sec0860ta#"),
        # Default admin (common but we know it didn't work)
        ("admin", "admin"),
        # Empty password
        ("admin", ""),
        # Some cameras use serial number or MAC-based passwords
        # (can't try without knowing the actual values)
    ]

    for username, password in combinations:
        logger.info(f"\nTrying: {username} / {password}")
        result = check_camera_status(ip, username, password)

        if result is True:
            logger.info("\n[SUCCESS] Working credentials found!")
            logger.info(f"Username: {username}")
            logger.info(f"Password: {password}")
            return (username, password)

        if result == "locked":
            logger.info("\n[STOPPED] Camera locked out. Cannot continue testing.")
            return None

    return None


if __name__ == "__main__":
    ip = "192.168.0.164"  # Kitchen camera

    logger.info("Tapo Camera Setup Check")
    logger.info("=" * 60)
    logger.info(f"\nChecking camera at {ip}...")
    logger.info("\nNote: Newer Tapo cameras may require:")
    logger.info("1. Initial setup through Tapo app")
    logger.info("2. Camera linked to cloud account")
    logger.info("3. Local credentials set in app")
    logger.info()

    # Try cloud credentials first (most likely after reset if previously linked)
    logger.info("Trying cloud account credentials (if camera was previously linked)...")
    result = check_camera_status(ip, "sandraschipal@hotmail.com", "Sec0860ta#")

    if result is True:
        logger.info("\n[SUCCESS] Cloud credentials work!")
        logger.info("Your camera is set up and accessible.")
        sys.exit(0)

    if result == "locked":
        logger.info("\n[LOCKOUT] Camera is locked out.")
        logger.info("Options:")
        logger.info("1. Wait 30 minutes for lockout to expire")
        logger.info("2. Power cycle the camera (unplug/replug)")
        logger.info("3. After unlock, try setting up camera in Tapo app first")
        sys.exit(1)

    # If cloud didn't work, try other combinations
    logger.info("\nCloud credentials didn't work. Trying other combinations...")
    result = try_setup_combinations(ip)

    if result:
        logger.info(f"\nWorking credentials: {result[0]}/{result[1]}")
        sys.exit(0)
    else:
        logger.info("\n" + "=" * 60)
        logger.info("[ACTION REQUIRED] Camera needs setup")
        logger.info("=" * 60)
        logger.info("\nSteps:")
        logger.info("1. Open Tapo app on your phone")
        logger.info("2. Add camera (scan QR code or enter serial number)")
        logger.info("3. Complete initial setup in the app")
        logger.info("4. After setup, check: Camera -> Advanced -> Local Device Settings")
        logger.info("5. Set or view local admin credentials")
        logger.info("\nOR:")
        logger.info("1. Power cycle the camera")
        logger.info("2. Wait 30 minutes for any lockouts to clear")
        logger.info("3. Try cloud credentials again")
        logger.info("=" * 60)
        sys.exit(1)
