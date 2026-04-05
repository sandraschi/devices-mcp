"""Test Tapo camera connection."""

import logging
import sys

from pytapo import Tapo

logger = logging.getLogger(__name__)


def test_connection(ip, username, password, max_attempts=1):
    """Test connection to Tapo camera.

    Args:
        ip: Camera IP address
        username: Local admin username
        password: Local admin password
        max_attempts: Maximum login attempts (default 1 to prevent lockouts)

    Returns:
        bool: True if connection successful, False otherwise
    """
    # Only attempt once to prevent lockouts
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        try:
            logger.info(f"Testing connection to {ip}... (attempt {attempts}/{max_attempts})")
            camera = Tapo(ip, username, password)
            info = camera.getBasicInfo()

            device_info = info.get("device_info", {})
            logger.info("\n[SUCCESS] Connection successful!")
            logger.info(f"Model: {device_info.get('device_model', 'Unknown')}")
            logger.info(f"Firmware: {device_info.get('firmware_version', 'Unknown')}")
            logger.info(f"Serial: {device_info.get('serial_number', 'Unknown')}")
            logger.info(f"MAC: {device_info.get('mac', 'Unknown')}")
            logger.info(f"Hostname: {device_info.get('device_alias', 'Unknown')}")
            return True
        except Exception as e:
            error_msg = str(e)

            # Check for lockout - stop immediately if detected
            if "Temporary Suspension" in error_msg or "1800 seconds" in error_msg:
                logger.info(f"\n[LOCKOUT] Camera at {ip} is temporarily locked out!")
                logger.info("Reason: Too many failed login attempts")
                logger.info("Action: Wait 30 minutes (1800 seconds) before trying again")
                logger.info("Prevention: This script only attempts once to avoid lockouts")
                return False

            # Check for authentication errors - don't retry
            if "Invalid authentication" in error_msg or "Invalid auth" in error_msg:
                logger.info(f"\n[ERROR] Authentication failed for {ip}")
                logger.info("Possible causes:")
                logger.info("  1. Wrong username/password (use LOCAL admin, not cloud account)")
                logger.info("  2. Camera requires different credentials")
                logger.info("  3. Camera security settings changed")
                logger.info(
                    "\nNote: Tapo cameras require LOCAL admin credentials set in the Tapo app."
                )
                logger.info(
                    "Go to: Tapo app -> Camera -> Device Settings -> Advanced -> Local Device Settings"
                )
                return False

            # Other errors - might retry if allowed
            if attempts < max_attempts:
                logger.info(f"[WARNING] Attempt {attempts} failed: {error_msg}")
                logger.info(f"Retrying... (max {max_attempts} attempts)")
            else:
                logger.info(f"\n[ERROR] Connection failed after {attempts} attempt(s): {error_msg}")
                return False

    return False


if __name__ == "__main__":
    import os
    import sys

    import yaml

    # Try to load credentials from config.yaml
    ip = "192.168.0.164"  # Kitchen camera
    username = "admin"
    password = "admin"

    config_path = "config.yaml"
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # Get kitchen camera credentials from config
            kitchen_cfg = config.get("cameras", {}).get("tapo_kitchen", {}).get("params", {})
            config_username = kitchen_cfg.get("username", "")
            config_password = kitchen_cfg.get("password", "")

            if config_username and config_password:
                username = config_username
                password = config_password
                logger.info("Using credentials from config.yaml")
        except Exception as e:
            logger.info(f"[WARNING] Could not load config.yaml: {e}")
            logger.info("Using default credentials (update config.yaml)")

    logger.info("Testing Tapo camera credentials...")
    logger.info(f"Camera IP: {ip}")
    logger.info(f"Username: {username}")
    logger.info(f"Password: {'*' * len(password)}")
    logger.info()

    success = test_connection(ip, username, password)

    if not success:
        logger.info("\n" + "=" * 60)
        logger.info("Connection failed. Check:")
        logger.info("=" * 60)
        logger.info("1. Credentials in config.yaml (cameras.tapo_kitchen.params)")
        logger.info("2. Camera Account settings in Tapo app")
        logger.info("3. Camera is online and accessible on network")
        logger.info("=" * 60)

    sys.exit(0 if success else 1)
