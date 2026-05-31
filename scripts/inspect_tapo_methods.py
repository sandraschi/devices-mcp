"""Inspect Tapo P115 plug object to see what methods are available."""

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from devices_mcp.ingest.tapo_p115 import TapoP115IngestionService


async def inspect_plug_methods(host: str, name: str):
    """Inspect the plug object to see what methods are available."""
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Inspecting {name} (IP: {host})")
    logger.info(f"{'=' * 60}")

    try:
        service = TapoP115IngestionService()
        client = await service._get_client()
        plug = await client.p115(host)

        logger.info(f"\nPlug object type: {type(plug)}")
        logger.info("\nPlug object methods:")
        methods = [attr for attr in dir(plug) if not attr.startswith("_") and callable(getattr(plug, attr))]
        for method in sorted(methods):
            logger.info(f"  - {method}")

        # Try to get device info and see what's available
        logger.info("\nDevice info:")
        device_info = await plug.get_device_info()
        logger.info(f"  Device info type: {type(device_info)}")
        logger.info(f"  Device info attributes: {[attr for attr in dir(device_info) if not attr.startswith('_')]}")

        # Try to see if device_info has energy data
        logger.info("\nDevice info values:")
        for attr in dir(device_info):
            if not attr.startswith("_"):
                try:
                    val = getattr(device_info, attr)
                    if not callable(val):
                        logger.info(f"  {attr}: {val}")
                except:
                    pass

        # Try get_energy_usage
        logger.info("\nEnergy usage:")
        energy = await plug.get_energy_usage()
        logger.info(f"  Energy type: {type(energy)}")
        logger.info(f"  Energy attributes: {[attr for attr in dir(energy) if not attr.startswith('_')]}")
        logger.info(f"  today_energy: {energy.today_energy}")
        logger.info(f"  month_energy: {energy.month_energy}")

        # Check if there's a to_dict method
        if hasattr(energy, "to_dict"):
            logger.info("\nEnergy as dict:")
            energy_dict = energy.to_dict()
            for key, val in energy_dict.items():
                logger.info(f"  {key}: {val}")

        return True

    except Exception as e:
        logger.info(f"[FAILED] Inspection failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Inspect Server plug methods."""
    logger.info("=" * 60)
    logger.info("Tapo P115 Plug Methods Inspection")
    logger.info("=" * 60)

    # Inspect Server plug
    success = await inspect_plug_methods("192.168.0.38", "Server")

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
