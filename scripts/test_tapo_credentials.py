"""Test different Tapo credential combinations to find working method."""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# Fix Windows console encoding
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

import yaml
from pytapo import Tapo

# Load config
config_path = project_root / "config.yaml"
with open(config_path, encoding="utf-8") as f:
    config = yaml.safe_load(f)

kitchen_cfg = config.get("cameras", {}).get("tapo_kitchen", {}).get("params", {})
host = kitchen_cfg.get("host", "192.168.0.164")
camera_username = kitchen_cfg.get("username", "")
camera_password = kitchen_cfg.get("password", "")

logger.info("=" * 70)
logger.info("Testing Tapo Camera Credentials - Multiple Combinations")
logger.info("=" * 70)
logger.info(f"Camera IP: {host}")
logger.info()

# Test different credential combinations
test_combinations = [
    {
        "name": "Camera Account (from config)",
        "username": camera_username,
        "password": camera_password,
    },
    {
        "name": "Admin (default)",
        "username": "admin",
        "password": camera_password,  # Try camera password with admin username
    },
    {
        "name": "Admin + Admin",
        "username": "admin",
        "password": "admin",
    },
    {
        "name": "Camera Account username + Admin password",
        "username": camera_username,
        "password": "admin",
    },
]

successful = None

for i, combo in enumerate(test_combinations, 1):
    if not combo["username"] or not combo["password"]:
        logger.info(f"[SKIP] Test {i}: {combo['name']} - Missing credentials")
        continue

    logger.info(f"[TEST {i}] {combo['name']}")
    logger.info(f"   Username: {combo['username']}")
    logger.info(f"   Password: {'*' * len(combo['password'])}")

    try:
        camera = Tapo(host, combo["username"], combo["password"])
        info = camera.getBasicInfo()

        device_info = info.get("device_info", {})
        logger.info("   [SUCCESS] Connection successful!")
        logger.info(f"   Model: {device_info.get('device_model', 'Unknown')}")
        logger.info(f"   Firmware: {device_info.get('firmware_version', 'Unknown')}")
        logger.info(f"   Serial: {device_info.get('serial_number', 'Unknown')}")

        successful = combo
        break

    except Exception as e:
        error_msg = str(e)
        logger.info(f"   [FAILED] {error_msg}")

        if "Temporary Suspension" in error_msg or "1800 seconds" in error_msg:
            logger.info("   [WARNING] Camera is locked out - wait 30 minutes")
            logger.info("   [STOP] Stopping tests to prevent further lockouts")
            break
        elif "Invalid authentication" in error_msg or "Invalid auth" in error_msg:
            logger.info("   [INFO] Authentication failed - trying next combination")
        else:
            logger.info("   [INFO] Connection error - trying next combination")

    logger.info()

logger.info()
logger.info("=" * 70)
logger.info("RESULTS")
logger.info("=" * 70)

if successful:
    logger.info("[SUCCESS] Working credentials found!")
    logger.info(f"   Method: {successful['name']}")
    logger.info(f"   Username: {successful['username']}")
    logger.info(f"   Password: {'*' * len(successful['password'])}")
    logger.info()
    logger.info("Update config.yaml with these credentials:")
    logger.info(f'   username: "{successful["username"]}"')
    logger.info(f'   password: "{successful["password"]}"')
else:
    logger.info("[FAILED] No working credentials found")
    logger.info()
    logger.info("Troubleshooting:")
    logger.info("  1. Verify Third-Party Compatibility is enabled:")
    logger.info("     Tapo App -> Me -> Tapo Lab -> Third-Party Compatibility -> On")
    logger.info()
    logger.info("  2. Verify Camera Account is set up:")
    logger.info("     Tapo App -> Camera -> Settings -> Advanced -> Camera Account")
    logger.info("     Create a username and password specifically for API access")
    logger.info()
    logger.info("  3. Check if camera is locked out:")
    logger.info("     Wait 30 minutes if you see 'Temporary Suspension' errors")
    logger.info()
    logger.info("  4. Verify camera firmware is up to date")
    logger.info("  5. Check network connectivity to camera")

logger.info()
logger.info("=" * 70)
