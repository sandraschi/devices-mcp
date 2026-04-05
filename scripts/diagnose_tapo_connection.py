"""Diagnose Tapo camera connection issues, including KLAP protocol detection."""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    import pytapo

    logger.info(f"✅ pytapo installed: version {pytapo.__version__}")
except ImportError:
    logger.info("❌ pytapo not installed")
    sys.exit(1)

# Check for KLAP support
logger.info("\n📋 Checking for KLAP protocol support...")
try:
    # Check if Tapo class has KLAP-related methods or attributes
    # Check Tapo class signature and methods
    import inspect

    from pytapo import Tapo

    tapo_methods = [m for m in dir(Tapo) if not m.startswith("_")]

    logger.info(f"   Tapo class methods: {len(tapo_methods)} found")

    # Look for KLAP-related methods
    klap_indicators = ["klap", "KLAP", "kasa", "Kasa", "local", "Local"]
    klap_methods = [m for m in tapo_methods if any(indicator in m for indicator in klap_indicators)]

    if klap_methods:
        logger.info(f"   ⚠️  Found potential KLAP-related methods: {klap_methods}")
    else:
        logger.info("   ⚠️  No obvious KLAP-related methods found")

    # Check Tapo.__init__ signature
    sig = inspect.signature(Tapo.__init__)
    logger.info(f"   Tapo.__init__ parameters: {list(sig.parameters.keys())}")

except Exception as e:
    logger.info(f"   ❌ Error checking Tapo class: {e}")

# Check for alternative libraries
logger.info("\n📋 Checking for alternative libraries...")
try:
    import kasa

    logger.info(f"   ✅ python-kasa installed: version {kasa.__version__}")
except ImportError:
    logger.info("   ⚠️  python-kasa not installed (alternative library)")

try:
    from onvif import ONVIFCamera

    logger.info("   ✅ python-onvif-zeep installed (ONVIF support)")
except ImportError:
    logger.info("   ⚠️  python-onvif-zeep not installed (ONVIF fallback)")

# Test connection with config
logger.info("\n📋 Testing connection with config.yaml...")
try:
    import yaml

    config_path = project_root / "config.yaml"

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        kitchen_cfg = config.get("cameras", {}).get("tapo_kitchen", {}).get("params", {})
        if kitchen_cfg:
            host = kitchen_cfg.get("host", "")
            username = kitchen_cfg.get("username", "")
            password = kitchen_cfg.get("password", "")

            if host and username and password:
                logger.info(f"   Testing connection to {host}...")
                logger.info(f"   Username: {username}")
                logger.info(f"   Password: {'*' * len(password)}")

                try:
                    camera = Tapo(host, username, password)
                    info = camera.getBasicInfo()
                    logger.info("   ✅ Connection successful!")

                    device_info = info.get("device_info", {})
                    logger.info(f"   Model: {device_info.get('device_model', 'Unknown')}")
                    logger.info(f"   Firmware: {device_info.get('firmware_version', 'Unknown')}")

                    # Check firmware version for KLAP indicators
                    firmware = device_info.get("firmware_version", "")
                    if firmware:
                        # Newer firmware versions may indicate KLAP support
                        logger.info(f"   ⚠️  Firmware version: {firmware}")
                        logger.info("   Note: Check if firmware requires KLAP protocol")

                except Exception as e:
                    error_msg = str(e)
                    logger.info(f"   ❌ Connection failed: {error_msg}")

                    # Check for KLAP-related errors
                    if "KLAP" in error_msg or "kasa" in error_msg.lower():
                        logger.info("   ⚠️  KLAP protocol may be required!")
                    elif "Invalid authentication" in error_msg or "Invalid auth" in error_msg:
                        logger.info("   ⚠️  Authentication failed - check credentials")
                    elif "Temporary Suspension" in error_msg:
                        logger.info("   ⚠️  Camera is locked out - wait 30 minutes")
            else:
                logger.info("   ⚠️  Missing credentials in config.yaml")
        else:
            logger.info("   ⚠️  No tapo_kitchen config found")
    else:
        logger.info("   ⚠️  config.yaml not found")

except Exception as e:
    logger.info(f"   ❌ Error reading config: {e}")

logger.info("\n📋 Recommendations:")
logger.info("   1. Check pytapo GitHub for KLAP support: https://github.com/JurajNyiri/pytapo")
logger.info("   2. Check camera firmware version in Tapo app")
logger.info("   3. Verify Third-Party Compatibility is enabled in Tapo app")
logger.info("   4. Consider testing python-kasa library as alternative")
logger.info("   5. Test ONVIF protocol as fallback")
