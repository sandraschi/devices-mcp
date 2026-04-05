"""Test if camera requires 'admin' as username for API access."""

import logging
import sys

from pytapo import Tapo

logger = logging.getLogger(__name__)


def test_with_admin(ip, password):
    """Test with 'admin' as username (common for Tapo API)."""
    logger.info("Testing with 'admin' as username (Camera Account password)...")
    logger.info(f"IP: {ip}")
    logger.info("Username: admin")
    logger.info(f"Password: {'*' * len(password)}")
    logger.info()

    try:
        camera = Tapo(ip, "admin", password)
        info = camera.getBasicInfo()

        device_info = info.get("device_info", {})
        logger.info("[SUCCESS] Connection successful with 'admin' username!")
        logger.info(f"Model: {device_info.get('device_model', 'Unknown')}")
        logger.info(f"Firmware: {device_info.get('firmware_version', 'Unknown')}")
        logger.info(f"Serial: {device_info.get('serial_number', 'Unknown')}")
        logger.info(f"MAC: {device_info.get('mac', 'Unknown')}")
        return True
    except Exception as e:
        error_msg = str(e)
        if "Invalid authentication" in error_msg:
            logger.info("[FAILED] 'admin' username didn't work")
            return False
        if "Temporary Suspension" in error_msg:
            logger.info("[LOCKOUT] Camera is locked out")
            return "locked"
        logger.info(f"[ERROR] {error_msg}")
        return False


if __name__ == "__main__":
    import yaml

    ip = "192.168.0.164"
    password = "Sec1000kitchen"  # Camera Account password

    # Load from config
    try:
        with open("config.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        kitchen_cfg = config.get("cameras", {}).get("tapo_kitchen", {}).get("params", {})
        password = kitchen_cfg.get("password", password)
    except:
        pass

    logger.info("=" * 60)
    logger.info("Testing Tapo Camera with 'admin' username")
    logger.info("=" * 60)
    logger.info("\nNote: Some Tapo cameras require 'admin' as username")
    logger.info("for API access, even if Camera Account has different username")
    logger.info()

    result = test_with_admin(ip, password)

    if result is True:
        logger.info("\n[SUCCESS] Use 'admin' as username for API access!")
        logger.info("Update config.yaml:")
        logger.info('  username: "admin"')
        logger.info(f'  password: "{password}"')
    elif result == "locked":
        logger.info("\n[LOCKOUT] Power cycle camera and try again")
    else:
        logger.info("\n[FAILED] Both 'sandraschi' and 'admin' usernames failed")
        logger.info("Check:")
        logger.info("1. Camera Account password is correct in app")
        logger.info("2. Camera Account is enabled for API access")
        logger.info("3. Camera firmware is up to date")

    sys.exit(0 if result is True else 1)
