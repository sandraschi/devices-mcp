import logging

logger = logging.getLogger(__name__)

"""Test Tapo P115 smart plug using tapo library (not python-kasa).

Tapo P115 uses the Tapo API (same as cameras) not the Kasa protocol.
"""

import asyncio
import sys


async def test_p115_tapo_api(ip, username, password):
    """Test connection to Tapo P115 using tapo library."""
    try:
        from tapo import ApiClient

        logger.info("Testing Tapo P115 connection using Tapo API...")
        logger.info(f"IP: {ip}")
        logger.info(f"Username: {username}")
        logger.info(f"Password: {'*' * len(password)}")
        logger.info()

        # Create API client
        logger.info("Creating Tapo API client...")
        client = ApiClient(username, password)

        # Connect to P115 device
        logger.info(f"Connecting to P115 at {ip}...")
        plug = await client.p115(ip)

        # Get device info (returns object, not dict)
        device_info = await plug.get_device_info()

        logger.info("\n[SUCCESS] Connection successful!")
        logger.info(f"Device Info Type: {type(device_info).__name__}")

        # Access attributes directly (object, not dict)
        device_name = getattr(device_info, "nickname", getattr(device_info, "name", "Unknown"))
        model = getattr(device_info, "model", "Unknown")
        firmware = getattr(
            device_info, "fw_ver", getattr(device_info, "firmware_version", "Unknown")
        )
        mac = getattr(device_info, "mac", "Unknown")
        device_id = getattr(device_info, "device_id", "Unknown")

        logger.info(f"Device Name: {device_name}")
        logger.info(f"Model: {model}")
        logger.info(f"Firmware: {firmware}")
        logger.info(f"MAC: {mac}")
        logger.info(f"Device ID: {device_id}")

        # Get current state (different API methods for P115)
        logger.info("\nCurrent State:")
        try:
            # Try different methods to get state
            is_on = await plug.is_on()
            logger.info(f"  Power: {'ON' if is_on else 'OFF'}")
        except AttributeError:
            try:
                state = await plug.get_state()
                is_on = getattr(state, "is_on", getattr(state, "device_on", False))
                logger.info(f"  Power: {'ON' if is_on else 'OFF'}")
            except Exception:
                logger.info("  Power: State information not available")

        # Get energy usage if available
        try:
            energy_usage = await plug.get_energy_usage()
            if energy_usage:
                logger.info("\nEnergy Usage:")
                current_power = getattr(
                    energy_usage, "current_power", getattr(energy_usage, "power", 0)
                )
                today_energy = getattr(
                    energy_usage, "today_energy", getattr(energy_usage, "today", 0)
                )
                month_energy = getattr(
                    energy_usage, "month_energy", getattr(energy_usage, "month", 0)
                )
                logger.info(f"  Current Power: {current_power} W")
                logger.info(f"  Today's Energy: {today_energy} kWh")
                logger.info(f"  This Month: {month_energy} kWh")
        except Exception as e:
            logger.info(f"\nNote: Energy usage not available: {e}")

        return True

    except ImportError:
        logger.info("[ERROR] tapo library not installed")
        logger.info("Install with: pip install tapo")
        logger.info("\nNote: Tapo P115 uses 'tapo' library (Tapo API), not 'python-kasa'")
        return False
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__
        logger.info(f"\n[ERROR] Connection failed: {error_type}: {error_msg}")

        if "Temporary Suspension" in error_msg or "1800 seconds" in error_msg:
            logger.info("\n[LOCKOUT] Device is temporarily locked out")
            logger.info("Wait 30 minutes or power cycle the device")
        elif "Invalid authentication" in error_msg or "Invalid auth" in error_msg:
            logger.info("\n[FAILED] Authentication failed")
            logger.info("Check username/password")
            logger.info("Note: Tapo P115 uses Tapo account credentials (cloud account)")
        elif "Connection" in error_msg or "timeout" in error_msg.lower():
            logger.info("\n[FAILED] Connection failed")
            logger.info("Check:")
            logger.info("1. Device is online at IP 192.168.0.17")
            logger.info("2. Device is accessible on network")
            logger.info("3. Third-Party Compatibility is enabled in Tapo app")

        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    ip = "192.168.0.17"
    username = "sandraschipal@hotmail.com"
    password = "Sec0860ta#"

    logger.info("=" * 60)
    logger.info("Testing Tapo P115 Smart Plug via Tapo API")
    logger.info("=" * 60)
    logger.info("\nNote: Tapo P115 uses Tapo API (same as cameras)")
    logger.info("Uses 'tapo' Python library, not 'python-kasa'")
    logger.info()

    try:
        success = asyncio.run(test_p115_tapo_api(ip, username, password))

        if success:
            logger.info("\n" + "=" * 60)
            logger.info("[SUCCESS] Tapo P115 is accessible via Tapo API!")
            logger.info("=" * 60)
            logger.info("\nThis confirms Tapo API works for smart plugs.")
            logger.info("The authentication issue is likely specific to cameras.")
        else:
            logger.info("\n" + "=" * 60)
            logger.info("[FAILED] Could not connect to P115")
            logger.info("=" * 60)
            logger.info("\nTroubleshooting:")
            logger.info("1. Verify device is online and accessible")
            logger.info("2. Check credentials (use cloud account)")
            logger.info("3. Enable Third-Party Compatibility in Tapo app")
            logger.info("4. Make sure 'tapo' library is installed")

        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\n[INTERRUPTED] Test cancelled")
        sys.exit(1)
    except Exception as e:
        logger.info(f"\n[FATAL ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
