"""Test camera connection after waiting for full initialization."""

import logging
import os
import sys
import time

logger = logging.getLogger(__name__)


# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml

from scripts.test_tapo_connection import test_connection


def test_after_wait(ip, username, password, wait_seconds=30):
    """Wait then test connection."""
    logger.info(f"Waiting {wait_seconds} seconds for camera to fully initialize after reboot...")
    logger.info("(Some cameras need time to fully initialize services after reboot)")

    for i in range(wait_seconds, 0, -5):
        logger.info(f"  {i} seconds remaining...")
        time.sleep(5)

    logger.info("\nTesting connection now...")
    return test_connection(ip, username, password, max_attempts=1)


if __name__ == "__main__":
    import os

    import yaml

    ip = "192.168.0.164"
    username = "sandraschi"
    password = "Sec1000kitchen"

    # Load from config
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
    logger.info("Testing Tapo Camera After Full Initialization")
    logger.info("=" * 60)
    logger.info(f"\nCamera IP: {ip}")
    logger.info(f"Username: {username}")
    logger.info(f"Password: {'*' * len(password)}")
    logger.info("\nNote: Camera may need time to fully initialize after reboot")
    logger.info()

    # Wait 30 seconds then test
    success = test_after_wait(ip, username, password, wait_seconds=30)

    if not success:
        logger.info("\n" + "=" * 60)
        logger.info("Still failing. Check:")
        logger.info("=" * 60)
        logger.info("1. Third-Party Compatibility is ON in Tapo app")
        logger.info("2. Camera Account username/password are correct")
        logger.info("3. Disable Two-Step Verification in Tapo app:")
        logger.info("   Me -> View Account -> Login Security -> Turn OFF Two-Step Verification")
        logger.info("4. Camera firmware is up to date")
        logger.info("5. Try waiting longer (some cameras need 2-3 minutes after reboot)")
        logger.info("=" * 60)

    sys.exit(0 if success else 1)
