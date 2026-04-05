"""Inspect Tapo P115 energy object to see what attributes are available."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from devices_mcp.ingest.tapo_p115 import TapoP115IngestionService

logger = logging.getLogger(__name__)


async def inspect_energy(host: str, name: str):
    """Inspect the energy object to see what attributes are available."""
    logger.info(f"Inspecting {name} (IP: {host})")

    try:
        service = TapoP115IngestionService()
        client = await service._get_client()
        plug = await client.p115(host)

        # Get device info first
        logger.info("Getting device info...")
        device_info = await plug.get_device_info()
        logger.info(f"Device info type: {type(device_info)}")
        logger.info(
            f"Device info attributes: {[attr for attr in dir(device_info) if not attr.startswith('_')]}"
        )

        # Try to get device info as dict
        if hasattr(device_info, "__dict__"):
            logger.info("\nDevice info __dict__:")
            for key, val in device_info.__dict__.items():
                logger.info(f"  {key}: {val}")

        # Get energy usage
        logger.info("\n" + "=" * 50)
        logger.info("Getting energy usage...")
        energy = await plug.get_energy_usage()

        logger.info(f"\nEnergy object type: {type(energy)}")
        logger.info("\nEnergy object attributes:")
        logger.info(f"  dir(): {[attr for attr in dir(energy) if not attr.startswith('_')]}")

        logger.info("\nTrying to access common attributes:")
        attrs_to_try = [
            "current_power",
            "power",
            "power_mw",
            "realtime_power",
            "voltage",
            "voltage_v",
            "realtime_voltage",
            "current",
            "current_a",
            "realtime_current",
            "current_ma",
            "today_energy",
            "today",
            "today_kwh",
            "energy_today",
            "month_energy",
            "month",
            "month_kwh",
            "energy_month",
        ]

        for attr in attrs_to_try:
            try:
                val = getattr(energy, attr, None)
                if val is not None:
                    logger.info(f"  {attr}: {val} (type: {type(val)})")
            except Exception as e:
                logger.info(f"  {attr}: ERROR - {e}")

        # Try to get as dict if possible
        if hasattr(energy, "__dict__"):
            logger.info("\nEnergy object __dict__:")
            for key, val in energy.__dict__.items():
                logger.info(f"  {key}: {val}")

        # Check if plug has other methods for power data
        logger.info("\n" + "=" * 50)
        logger.info("Checking plug object methods...")
        plug_methods = [
            method
            for method in dir(plug)
            if not method.startswith("_") and callable(getattr(plug, method))
        ]
        logger.info(f"Available methods: {plug_methods}")

        # Try get_current_power method
        logger.info("\n" + "=" * 50)
        logger.info("Testing get_current_power() method...")
        try:
            current_power_result = await plug.get_current_power()
            logger.info(f"get_current_power() result type: {type(current_power_result)}")
            logger.info(f"get_current_power() result: {current_power_result}")

            if hasattr(current_power_result, "__dict__"):
                logger.info("get_current_power() result __dict__:")
                for key, val in current_power_result.__dict__.items():
                    logger.info(f"  {key}: {val}")

            # Check if it has power attribute
            if hasattr(current_power_result, "power"):
                logger.info(f"Power from get_current_power(): {current_power_result.power}")
            elif hasattr(current_power_result, "current_power"):
                logger.info(
                    f"Current power from get_current_power(): {current_power_result.current_power}"
                )

        except Exception as e:
            logger.info(f"get_current_power() failed: {e}")
            import traceback

            traceback.print_exc()

        # Try get_power_data method
        logger.info("\n" + "=" * 50)
        logger.info("Testing get_power_data() method...")
        try:
            power_data_result = await plug.get_power_data()
            logger.info(f"get_power_data() result type: {type(power_data_result)}")
            logger.info(f"get_power_data() result: {power_data_result}")

            if hasattr(power_data_result, "__dict__"):
                logger.info("get_power_data() result __dict__:")
                for key, val in power_data_result.__dict__.items():
                    logger.info(f"  {key}: {val}")

        except Exception as e:
            logger.info(f"get_power_data() failed: {e}")

        # Try get_device_usage method
        logger.info("\n" + "=" * 50)
        logger.info("Testing get_device_usage() method...")
        try:
            device_usage_result = await plug.get_device_usage()
            logger.info(f"get_device_usage() result type: {type(device_usage_result)}")
            logger.info(f"get_device_usage() result: {device_usage_result}")

            if hasattr(device_usage_result, "__dict__"):
                logger.info("get_device_usage() result __dict__:")
                for key, val in device_usage_result.__dict__.items():
                    logger.info(f"  {key}: {val}")

        except Exception as e:
            logger.info(f"get_device_usage() failed: {e}")

        return True

    except Exception as e:
        logger.info(f"[FAILED] Inspection failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Inspect Server plug energy object."""
    logger.info("=" * 60)
    logger.info("Tapo P115 Energy Object Inspection")
    logger.info("=" * 60)

    # Inspect Server plug (should be ~400W)
    success = await inspect_energy("192.168.0.38", "Server")

    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n\n[INTERRUPTED] Inspection cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.info(f"\n[FATAL ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
