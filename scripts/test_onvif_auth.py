import logging

logger = logging.getLogger(__name__)

"""Test Tapo camera using ONVIF authentication instead of pytapo.

Some Tapo cameras support ONVIF protocol which may work better
than the Tapo API for authentication.
"""

import sys


def test_onvif_connection(ip, username, password):
    """Test ONVIF authentication to Tapo camera."""
    try:
        from onvif import ONVIFCamera

        logger.info(f"Testing ONVIF connection to {ip}...")
        logger.info(f"Username: {username}")
        logger.info(f"Password: {'*' * len(password)}")

        # Tapo C200 typically uses port 2020 for ONVIF
        camera = ONVIFCamera(ip, 2020, username, password)

        # Get device capabilities
        logger.info("\nGetting device capabilities...")
        capabilities = camera.devicemgmt.GetCapabilities()

        logger.info("[SUCCESS] ONVIF connection successful!")
        logger.info(
            f"Device Manufacturer: {capabilities.Device.Manufacturer if hasattr(capabilities.Device, 'Manufacturer') else 'Unknown'}"
        )
        logger.info(
            f"Device Model: {capabilities.Device.Model if hasattr(capabilities.Device, 'Model') else 'Unknown'}"
        )

        # Try to get profiles
        media_service = camera.create_media_service()
        profiles = media_service.GetProfiles()
        logger.info(f"Video Profiles: {len(profiles)}")

        return True

    except ImportError:
        logger.info("[ERROR] ONVIF library not installed")
        logger.info("Install with: pip install onvif-zeep")
        return False
    except Exception as e:
        error_msg = str(e)
        logger.info(f"\n[ERROR] ONVIF connection failed: {error_msg}")

        if "401" in error_msg or "Unauthorized" in error_msg:
            logger.info("Authentication failed - check username/password")
        elif "Connection refused" in error_msg or "timeout" in error_msg.lower():
            logger.info("Camera may not support ONVIF or port 2020 is not open")
            logger.info("Some Tapo cameras use different ports or don't support ONVIF")

        return False


if __name__ == "__main__":
    import os

    import yaml

    # Load kitchen camera credentials from config
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
    logger.info("Testing ONVIF Authentication to Tapo Camera")
    logger.info("=" * 60)
    logger.info("\nNote: ONVIF is an alternative protocol that some Tapo cameras support")
    logger.info("If this works, we may need to use ONVIF instead of pytapo")
    logger.info()

    success = test_onvif_connection(ip, username, password)

    if not success:
        logger.info("\n" + "=" * 60)
        logger.info("ONVIF Authentication Failed")
        logger.info("=" * 60)
        logger.info("\nPossible reasons:")
        logger.info("1. Camera doesn't support ONVIF")
        logger.info("2. ONVIF port (2020) is not open")
        logger.info("3. ONVIF is not enabled in camera settings")
        logger.info("4. Wrong credentials")
        logger.info("\nCheck camera settings:")
        logger.info("- Camera -> Settings -> Advanced -> ONVIF")
        logger.info("- Enable ONVIF if available")
        logger.info("=" * 60)

    sys.exit(0 if success else 1)
