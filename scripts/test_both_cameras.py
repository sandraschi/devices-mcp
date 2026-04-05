"""Test connection to both Tapo cameras."""

import logging
import os
import sys

logger = logging.getLogger(__name__)


# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.test_tapo_connection import test_connection


def test_all_cameras():
    """Test both cameras."""
    cameras = [
        {
            "name": "Kitchen Camera",
            "ip": "192.168.0.164",
            "username": "",  # Set in config.yaml
            "password": "",  # Set in config.yaml
        },
        {
            "name": "Living Room Camera",
            "ip": "192.168.0.206",
            "username": "",  # Set in config.yaml
            "password": "",  # Set in config.yaml
        },
    ]

    # Load credentials from config.yaml
    try:
        import yaml

        with open("config.yaml", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Get kitchen camera credentials
        kitchen_cfg = config.get("cameras", {}).get("tapo_kitchen", {}).get("params", {})
        cameras[0]["username"] = kitchen_cfg.get("username", "")
        cameras[0]["password"] = kitchen_cfg.get("password", "")

        # Get living room camera credentials
        living_room_cfg = config.get("cameras", {}).get("tapo_living_room", {}).get("params", {})
        cameras[1]["username"] = living_room_cfg.get("username", "")
        cameras[1]["password"] = living_room_cfg.get("password", "")
    except Exception as e:
        logger.info(f"[WARNING] Could not load config.yaml: {e}")
        logger.info("Please set credentials manually in config.yaml first")
        sys.exit(1)

    logger.info("Testing Both Tapo Cameras")
    logger.info("=" * 60)

    all_success = True

    for camera in cameras:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Testing: {camera['name']} ({camera['ip']})")
        logger.info(f"{'=' * 60}")

        if not camera["username"] or not camera["password"]:
            logger.info(f"[SKIP] {camera['name']} - No credentials set in config.yaml")
            logger.info(
                "Set username/password in config.yaml -> cameras -> tapo_kitchen/tapo_living_room"
            )
            all_success = False
            continue

        success = test_connection(
            camera["ip"], camera["username"], camera["password"], max_attempts=1
        )

        if not success:
            all_success = False

    logger.info("\n" + "=" * 60)
    if all_success:
        logger.info("[SUCCESS] All cameras connected successfully!")
        logger.info("\nBoth cameras are ready to use via API.")
    else:
        logger.info("[INCOMPLETE] Some cameras failed or need credentials")
        logger.info("\nNext steps:")
        logger.info("1. Get Camera Account credentials from Tapo app:")
        logger.info("   Camera -> Settings -> Advanced -> Camera Account")
        logger.info("2. Update config.yaml with username/password for each camera")
        logger.info("3. Run this script again to test")
    logger.info("=" * 60)

    return all_success


if __name__ == "__main__":
    success = test_all_cameras()
    sys.exit(0 if success else 1)
