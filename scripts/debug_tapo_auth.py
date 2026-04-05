"""Debug Tapo camera authentication to see exact error."""

import logging
import sys

from pytapo import Tapo

logger = logging.getLogger(__name__)


def debug_auth(ip, username, password):
    """Test authentication with detailed error info."""
    logger.info(f"Testing authentication to {ip}")
    logger.info(f"Username: {username}")
    logger.info(f"Password: {'*' * len(password)}")
    logger.info()

    try:
        logger.info("Creating Tapo instance...")
        camera = Tapo(ip, username, password)
        logger.info("✅ Tapo instance created")

        logger.info("\nCalling getBasicInfo()...")
        info = camera.getBasicInfo()
        logger.info("✅ getBasicInfo() successful!")

        device_info = info.get("device_info", {})
        logger.info("\n[SUCCESS] Camera connected!")
        logger.info(f"Model: {device_info.get('device_model', 'Unknown')}")
        logger.info(f"Firmware: {device_info.get('firmware_version', 'Unknown')}")
        logger.info(f"Serial: {device_info.get('serial_number', 'Unknown')}")
        logger.info(f"MAC: {device_info.get('mac', 'Unknown')}")
        logger.info(f"Hostname: {device_info.get('device_alias', 'Unknown')}")
        return True

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        logger.info(f"\n[ERROR] {error_type}: {error_msg}")
        logger.info("\nFull error details:")
        import traceback

        traceback.print_exc()

        # Check for specific error patterns
        if "Temporary Suspension" in error_msg or "1800 seconds" in error_msg:
            logger.info("\n❌ Camera is LOCKED OUT")
            logger.info("   Wait 30 minutes or power cycle camera")
        elif "Invalid authentication" in error_msg or "Invalid auth" in error_msg:
            logger.info("\n❌ Authentication failed")
            logger.info("   Possible issues:")
            logger.info("   1. Wrong username/password")
            logger.info("   2. Camera Account not enabled")
            logger.info("   3. Camera Account type mismatch")
            logger.info("   4. Camera needs to be re-authenticated in app")
        elif "Connection" in error_msg or "timeout" in error_msg.lower():
            logger.info("\n❌ Connection failed")
            logger.info("   Check camera is online and IP is correct")
        else:
            logger.info(f"\n❌ Unknown error: {error_type}")

        return False


if __name__ == "__main__":
    import os

    import yaml

    # Load credentials from config
    ip = "192.168.0.164"
    username = "sandraschi"
    password = "Sec1000kitchen"

    config_path = "config.yaml"
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            kitchen_cfg = config.get("cameras", {}).get("tapo_kitchen", {}).get("params", {})
            username = kitchen_cfg.get("username", username)
            password = kitchen_cfg.get("password", password)
        except Exception as e:
            logger.info(f"[WARNING] Could not load config: {e}")

    logger.info("=" * 60)
    logger.info("Tapo Camera Authentication Debug")
    logger.info("=" * 60)
    logger.info()

    success = debug_auth(ip, username, password)

    if not success:
        logger.info("\n" + "=" * 60)
        logger.info("Troubleshooting Steps:")
        logger.info("=" * 60)
        logger.info("1. Verify Camera Account is enabled in Tapo app")
        logger.info("2. Try changing Camera Account password in app")
        logger.info("3. Make sure you're using Camera Account (not cloud account)")
        logger.info("4. Some cameras require 'admin' as username for API access")
        logger.info("5. Check if Camera Account has API access enabled")
        logger.info("=" * 60)

    sys.exit(0 if success else 1)
