"""Test living room camera connection specifically."""

import logging
import os
import sys

import yaml

logger = logging.getLogger(__name__)


# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.test_tapo_connection import test_connection

if __name__ == "__main__":
    # Load living room camera credentials from config
    ip = "192.168.0.206"
    username = "sandraschi"
    password = "Sec1000living"

    config_path = "config.yaml"
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            living_room_cfg = (
                config.get("cameras", {}).get("tapo_living_room", {}).get("params", {})
            )
            username = living_room_cfg.get("username", username)
            password = living_room_cfg.get("password", password)
        except Exception as e:
            logger.info(f"[WARNING] Could not load config: {e}")

    logger.info("=" * 60)
    logger.info("Testing Living Room Camera")
    logger.info("=" * 60)
    logger.info(f"\nCamera IP: {ip} (static)")
    logger.info(f"Username: {username}")
    logger.info(f"Password: {'*' * len(password)}")
    logger.info("\nThis test will help us understand if the authentication")
    logger.info("issue is camera-specific (kitchen) or general.")
    logger.info()

    success = test_connection(ip, username, password, max_attempts=1)

    if success:
        logger.info("\n" + "=" * 60)
        logger.info("[SUCCESS] Living Room Camera Connected!")
        logger.info("=" * 60)
        logger.info("\nThis means:")
        logger.info("✅ Authentication method works correctly")
        logger.info("✅ Third-Party Compatibility is working")
        logger.info("✅ Issue is specific to Kitchen Camera")
        logger.info("\nNext: Investigate kitchen camera-specific issues")
    else:
        logger.info("\n" + "=" * 60)
        logger.info("[FAILED] Living Room Camera Also Failed")
        logger.info("=" * 60)
        logger.info("\nThis means:")
        logger.info("[ISSUE] Authentication issue is general (both cameras)")
        logger.info("[ISSUE] May be pytapo library issue or configuration")
        logger.info("[ISSUE] Need to investigate authentication method")
        logger.info("\nPossible causes:")
        logger.info("1. pytapo library incompatibility with C200")
        logger.info("2. Camera Account credentials format issue")
        logger.info("3. Third-Party Compatibility setting not fully working")
        logger.info("4. Need different authentication method")

    logger.info("=" * 60)
    sys.exit(0 if success else 1)
