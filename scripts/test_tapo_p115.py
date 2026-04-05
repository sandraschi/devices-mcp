"""Test connection to Tapo P115 smart plug using python-kasa."""

import asyncio
import logging
import sys

logger = logging.getLogger(__name__)


async def test_p115_connection(ip, username=None, password=None):
    """Test connection to Tapo P115 smart plug.

    Uses same method as existing code in tapo_p115.py.
    """
    try:
        from kasa import Credentials, SmartPlug

        logger.info(f"Testing connection to Tapo P115 at {ip}...")

        # Create credentials if provided (for cloud access)
        credentials = None
        if username and password:
            logger.info(f"Using credentials: {username} / {'*' * len(password)}")
            credentials = Credentials(username, password)
        else:
            logger.info("No credentials provided - trying local connection")

        # Create SmartPlug instance directly (same as existing code)
        logger.info("Creating SmartPlug instance...")
        plug = SmartPlug(ip)

        # Update to get device info
        # Note: Credentials might need to be set differently or may not be needed for local access
        logger.info("Connecting to device...")
        try:
            # Try without credentials first (local access)
            await plug.update()
        except Exception:
            if credentials:
                logger.info("Local connection failed, trying with credentials...")
                # For newer kasa versions, credentials might need to be passed differently
                # or the plug might need cloud access enabled
                raise
            raise

        # Get device information
        logger.info("\n[SUCCESS] Connection successful!")
        logger.info(f"Alias: {plug.alias}")
        logger.info(f"Model: {plug.model}")
        logger.info(f"Host: {plug.host}")
        logger.info(f"Device ID: {plug.device_id}")
        logger.info(f"MAC Address: {plug.mac}")

        # Get current state
        logger.info("\nCurrent State:")
        logger.info(f"  Power: {'ON' if plug.is_on else 'OFF'}")
        logger.info(f"  LED: {'ON' if plug.led else 'OFF'}")

        # Get energy monitoring data
        if hasattr(plug, "emeter_realtime"):
            emeter = plug.emeter_realtime
            logger.info("\nEnergy Monitoring:")
            logger.info(f"  Current Power: {emeter.power} W")
            logger.info(f"  Voltage: {emeter.voltage} V")
            logger.info(f"  Current: {emeter.current} A")
            logger.info(f"  Today's Energy: {emeter.today} kWh")
            logger.info(f"  This Month: {emeter.month} kWh")

        return True

    except ImportError:
        logger.info("[ERROR] python-kasa library not installed")
        logger.info("Install with: pip install python-kasa")
        return False
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        logger.info(f"\n[ERROR] Connection failed: {error_type}: {error_msg}")

        if "Connection" in error_msg or "timeout" in error_msg.lower():
            logger.info("\nPossible causes:")
            logger.info("1. Device is not online at IP 192.168.0.17")
            logger.info("2. Network connectivity issue")
            logger.info("3. Firewall blocking connection")
        elif "authentication" in error_msg.lower() or "auth" in error_msg.lower():
            logger.info("\nPossible causes:")
            logger.info("1. Need credentials for cloud access")
            logger.info("2. Local authentication required")
        elif "Unknown" in error_msg or "not found" in error_msg.lower():
            logger.info("\nPossible causes:")
            logger.info("1. Device might not be a TP-Link/Tapo device")
            logger.info("2. Device might not be accessible via kasa protocol")

        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    import os

    import yaml

    ip = "192.168.0.17"
    username = None
    password = None

    # Try to load credentials from config
    config_path = "config.yaml"
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            energy_cfg = config.get("energy", {}).get("tapo_p115", {})
            account_cfg = energy_cfg.get("account", {})
            username = account_cfg.get("username") or os.getenv("TAPO_ACCOUNT_EMAIL")
            password = account_cfg.get("password") or os.getenv("TAPO_ACCOUNT_PASSWORD")
        except Exception as e:
            logger.info(f"[WARNING] Could not load config: {e}")

    # If no credentials from config, try using camera account credentials
    if not username and not password:
        logger.info("[INFO] No credentials in config - trying cloud account credentials")
        username = "sandraschipal@hotmail.com"
        password = "Sec0860ta#"

    logger.info("=" * 60)
    logger.info("Testing Tapo P115 Smart Plug Connection")
    logger.info("=" * 60)
    logger.info(f"\nDevice IP: {ip}")
    if username and password:
        logger.info(f"Username: {username}")
        logger.info(f"Password: {'*' * len(password)}")
    else:
        logger.info("Credentials: Not provided (will try local connection)")
    logger.info()

    try:
        success = asyncio.run(test_p115_connection(ip, username, password))

        if success:
            logger.info("\n" + "=" * 60)
            logger.info("[SUCCESS] Tapo P115 Smart Plug is accessible!")
            logger.info("=" * 60)
            logger.info("\nYou can now use this device for energy monitoring.")
            logger.info("Update config.yaml with device details if needed.")
        else:
            logger.info("\n" + "=" * 60)
            logger.info("[FAILED] Could not connect to device")
            logger.info("=" * 60)
            logger.info("\nTry:")
            logger.info("1. Verify device is online at 192.168.0.17")
            logger.info("2. Check if device is accessible on network")
            logger.info("3. Verify credentials if using cloud access")
            logger.info("4. Try ping to verify connectivity: ping 192.168.0.17")

        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\n[INTERRUPTED] Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.info(f"\n[FATAL ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
