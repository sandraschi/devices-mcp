"""Test all Tapo camera connection methods: pytapo, python-kasa, and ONVIF."""

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# Fix Windows console encoding
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import yaml

# Load config
config_path = project_root / "config.yaml"
if not config_path.exists():
    logger.info("[ERROR] config.yaml not found")
    sys.exit(1)

with open(config_path, encoding="utf-8") as f:
    config = yaml.safe_load(f)

kitchen_cfg = config.get("cameras", {}).get("tapo_kitchen", {}).get("params", {})
if not kitchen_cfg:
    logger.info("[ERROR] No tapo_kitchen config found")
    sys.exit(1)

host = kitchen_cfg.get("host", "")
username = kitchen_cfg.get("username", "")
password = kitchen_cfg.get("password", "")

if not all([host, username, password]):
    logger.info("[ERROR] Missing credentials in config.yaml")
    sys.exit(1)

logger.info("=" * 70)
logger.info("Testing Tapo Camera Connection - All Methods")
logger.info("=" * 70)
logger.info(f"Camera IP: {host}")
logger.info(f"Username: {username}")
logger.info(f"Password: {'*' * len(password)}")
logger.info()

results = {}

# Method 1: pytapo
logger.info("=" * 70)
logger.info("METHOD 1: pytapo (Current Method)")
logger.info("=" * 70)
try:
    from pytapo import Tapo

    logger.info("[OK] pytapo imported successfully")
    try:
        # Try to get version
        import pytapo

        version = getattr(pytapo, "__version__", "unknown")
        logger.info(f"   Version: {version}")
    except:
        logger.info("   Version: unknown")

    logger.info("   Attempting connection...")
    camera = Tapo(host, username, password)
    info = camera.getBasicInfo()

    device_info = info.get("device_info", {})
    logger.info("   [SUCCESS] CONNECTION SUCCESSFUL!")
    logger.info(f"   Model: {device_info.get('device_model', 'Unknown')}")
    logger.info(f"   Firmware: {device_info.get('firmware_version', 'Unknown')}")
    logger.info(f"   Serial: {device_info.get('serial_number', 'Unknown')}")

    results["pytapo"] = {
        "success": True,
        "model": device_info.get("device_model", "Unknown"),
        "firmware": device_info.get("firmware_version", "Unknown"),
    }

except Exception as e:
    error_msg = str(e)
    logger.info(f"   [FAILED] CONNECTION FAILED: {error_msg}")

    if "KLAP" in error_msg or "kasa" in error_msg.lower():
        logger.info("   [WARNING] KLAP protocol may be required")
    elif "Invalid authentication" in error_msg or "Invalid auth" in error_msg:
        logger.info("   [WARNING] Authentication failed - check credentials")
    elif "Temporary Suspension" in error_msg:
        logger.info("   [WARNING] Camera is locked out - wait 30 minutes")

    results["pytapo"] = {"success": False, "error": error_msg}

# Method 2: python-kasa
logger.info()
logger.info("=" * 70)
logger.info("METHOD 2: python-kasa (Alternative)")
logger.info("=" * 70)
try:
    from kasa import SmartDevice  # Discover used implicitly for enumeration

    logger.info("[OK] python-kasa imported successfully")
    try:
        import kasa

        version = getattr(kasa, "__version__", "unknown")
        logger.info(f"   Version: {version}")
    except:
        logger.info("   Version: unknown")

    logger.info("   Attempting connection...")
    # python-kasa uses different approach - try to discover or connect directly
    # Note: python-kasa is primarily for Kasa devices, but may work with Tapo
    device = SmartDevice(host)
    device.set_alias(username)  # May not be needed
    asyncio.run(device.update())

    logger.info("   [SUCCESS] CONNECTION SUCCESSFUL!")
    logger.info(f"   Model: {device.model}")
    logger.info(f"   Alias: {device.alias}")

    results["python-kasa"] = {"success": True, "model": device.model, "alias": device.alias}

except ImportError:
    logger.info("   [WARNING] python-kasa not installed or incompatible")
    results["python-kasa"] = {"success": False, "error": "Not installed"}
except Exception as e:
    error_msg = str(e)
    logger.info(f"   [FAILED] CONNECTION FAILED: {error_msg}")
    results["python-kasa"] = {"success": False, "error": error_msg}

# Method 3: ONVIF
logger.info()
logger.info("=" * 70)
logger.info("METHOD 3: ONVIF (Fallback)")
logger.info("=" * 70)
try:
    from onvif import ONVIFCamera

    logger.info("[OK] python-onvif-zeep imported successfully")
    logger.info("   Attempting connection...")

    # ONVIF typically uses port 80 or 8080, but Tapo may use different port
    # Try common ports
    ports = [80, 8080, 554, 443]
    onvif_success = False

    for port in ports:
        try:
            logger.info(f"   Trying port {port}...")
            camera = ONVIFCamera(host, port, username, password)

            # Get device information
            media_service = camera.create_media_service()
            profiles = media_service.GetProfiles()

            logger.info(f"   ✅ CONNECTION SUCCESSFUL on port {port}!")
            logger.info(f"   Profiles found: {len(profiles)}")

            results["onvif"] = {"success": True, "port": port, "profiles": len(profiles)}
            onvif_success = True
            break

        except Exception as port_error:
            if port == ports[-1]:  # Last port
                raise port_error
            continue

    if not onvif_success:
        raise Exception("Failed on all ports")

except ImportError:
    logger.info("   [WARNING] python-onvif-zeep not installed")
    results["onvif"] = {"success": False, "error": "Not installed"}
except Exception as e:
    error_msg = str(e)
    logger.info(f"   [FAILED] CONNECTION FAILED: {error_msg}")
    results["onvif"] = {"success": False, "error": error_msg}

# Summary
logger.info()
logger.info("=" * 70)
logger.info("SUMMARY")
logger.info("=" * 70)

working_methods = [method for method, result in results.items() if result.get("success")]
failed_methods = [method for method, result in results.items() if not result.get("success")]

if working_methods:
    logger.info(f"[SUCCESS] Working methods: {', '.join(working_methods)}")
    logger.info(f"   Recommended: Use {working_methods[0]}")
else:
    logger.info("[FAILED] All methods failed")
    logger.info(f"   Failed methods: {', '.join(failed_methods)}")
    logger.info()
    logger.info("Troubleshooting steps:")
    logger.info("  1. Verify Third-Party Compatibility is enabled in Tapo app")
    logger.info("  2. Check Camera Account credentials in Tapo app")
    logger.info("  3. Verify camera firmware is up to date")
    logger.info("  4. Check network connectivity to camera")
    logger.info("  5. Wait 30 minutes if camera is locked out")

if failed_methods:
    logger.info()
    logger.info(f"[WARNING] Failed methods: {', '.join(failed_methods)}")
    for method in failed_methods:
        error = results[method].get("error", "Unknown error")
        logger.info(f"   {method}: {error}")

logger.info()
logger.info("=" * 70)
