"""Discover all Tapo P115 smart plugs on the network."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def discover_all_plugs():
    """Discover all P115 plugs using Tapo API."""
    try:
        from tapo import ApiClient

        # Tapo cloud account credentials
        email = "sandraschipal@hotmail.com"
        password = "Sec0860ta#"

        logger.info("=" * 60)
        logger.info("Discovering Tapo P115 Smart Plugs")
        logger.info("=" * 60)
        logger.info(f"Account: {email}")
        logger.info()

        # Create API client
        client = ApiClient(email, password)

        # Get all devices
        logger.info("Fetching devices from Tapo account...")
        devices = await client.list_devices()

        logger.info(f"\nFound {len(devices)} device(s)")
        logger.info()

        p115_plugs = []
        for device in devices:
            device_type = getattr(device, "device_type", "Unknown")
            device_id = getattr(device, "device_id", "Unknown")
            alias = getattr(device, "alias", "Unknown")

            # Check if it's a P115 plug
            if "P115" in str(device_type) or "P115" in str(alias) or "P115" in str(device_id):
                ip = getattr(device, "ip", getattr(device, "device_ip", "Unknown"))
                model = getattr(device, "device_model", "P115")

                p115_plugs.append(
                    {
                        "device_id": device_id,
                        "alias": alias,
                        "ip": ip,
                        "model": model,
                        "device_type": device_type,
                    }
                )

                logger.info("✅ Found P115 Plug:")
                logger.info(f"   Device ID: {device_id}")
                logger.info(f"   Name: {alias}")
                logger.info(f"   IP: {ip}")
                logger.info(f"   Model: {model}")
                logger.info()

        if not p115_plugs:
            logger.info("⚠️  No P115 plugs found in device list")
            logger.info("   Make sure plugs are registered in your Tapo app")
            return []

        logger.info(f"\n{'=' * 60}")
        logger.info(f"Summary: Found {len(p115_plugs)} P115 plug(s)")
        logger.info(f"{'=' * 60}\n")

        # Test connection to each
        logger.info("Testing connections...")
        for plug_info in p115_plugs:
            try:
                ip = plug_info["ip"]
                if ip == "Unknown" or not ip:
                    logger.info(f"⚠️  {plug_info['alias']}: No IP address available")
                    continue

                logger.info(f"\nTesting {plug_info['alias']} at {ip}...")
                plug = await client.p115(ip)

                # Get device info
                device_info = await plug.get_device_info()
                device_name = getattr(
                    device_info, "nickname", getattr(device_info, "name", plug_info["alias"])
                )
                model = getattr(device_info, "model", "P115")
                firmware = getattr(
                    device_info, "fw_ver", getattr(device_info, "firmware_version", "Unknown")
                )
                mac = getattr(device_info, "mac", "Unknown")

                # Try to get state
                try:
                    is_on = await plug.is_on()
                    power_state = "ON" if is_on else "OFF"
                except:
                    power_state = "Unknown"

                # Try to get energy usage
                try:
                    energy = await plug.get_energy_usage()
                    current_power = getattr(energy, "current_power", getattr(energy, "power", 0))
                    today_energy = getattr(energy, "today_energy", getattr(energy, "today", 0))
                except:
                    current_power = 0
                    today_energy = 0

                logger.info("   ✅ Connected!")
                logger.info(f"   Name: {device_name}")
                logger.info(f"   Model: {model}")
                logger.info(f"   Firmware: {firmware}")
                logger.info(f"   MAC: {mac}")
                logger.info(f"   State: {power_state}")
                logger.info(f"   Current Power: {current_power} W")
                logger.info(f"   Today's Energy: {today_energy} kWh")

            except Exception as e:
                logger.info(f"   ❌ Failed to connect: {e}")

        return p115_plugs

    except ImportError:
        logger.info("[ERROR] 'tapo' library not installed")
        logger.info("Install it with: pip install tapo")
        return []
    except Exception as e:
        logger.exception("Discovery failed")
        logger.info(f"\n[ERROR] Discovery failed: {e}")
        return []


if __name__ == "__main__":
    asyncio.run(discover_all_plugs())
