"""Test both Tapo P115 plugs: 192.168.0.17 (Living Room) and 192.168.0.137 (Kitchen)."""

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from devices_mcp.ingest.tapo_p115 import TapoP115IngestionService


async def test_plug(host: str, name: str):
    """Test a single plug connection and get energy data."""
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Testing {name} (IP: {host})")
    logger.info(f"{'=' * 60}")

    try:
        service = TapoP115IngestionService()
        snapshot = await service._fetch_device_snapshot(host)

        if snapshot:
            logger.info("[SUCCESS] Connection successful!")
            logger.info("\nDevice Info:")
            logger.info(f"  Device ID: {snapshot.get('device_id')}")
            logger.info(f"  Name: {snapshot.get('name')}")
            logger.info(f"  Location: {snapshot.get('location')}")
            logger.info(f"  Model: {snapshot.get('device_model')}")
            logger.info("\nPower State:")
            logger.info(f"  Power: {'ON' if snapshot.get('power_state') else 'OFF'}")
            logger.info("\nEnergy Monitoring:")
            logger.info(f"  Current Power: {snapshot.get('current_power', 0):.2f} W")
            logger.info(f"  Voltage: {snapshot.get('voltage', 0):.2f} V")
            logger.info(f"  Current: {snapshot.get('current', 0):.3f} A")
            logger.info(f"  Today's Energy: {snapshot.get('daily_energy', 0):.3f} kWh")
            logger.info(f"  Monthly Energy: {snapshot.get('monthly_energy', 0):.2f} kWh")
            logger.info(f"  Last Seen: {snapshot.get('last_seen')}")
            return True
        logger.info("[FAILED] Connection failed - no data returned")
        return False

    except Exception as e:
        logger.info(f"[FAILED] Connection failed: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Test all plugs."""
    logger.info("=" * 60)
    logger.info("Tapo P115 Plug Connection Test")
    logger.info("=" * 60)

    results = []

    # Test Living Room plug (192.168.0.17)
    results.append(await test_plug("192.168.0.17", "Living Room Aircon"))

    # Test Kitchen plug (192.168.0.137)
    results.append(await test_plug("192.168.0.137", "Kitchen Zojirushi"))

    # Test Server plug (192.168.0.38)
    results.append(await test_plug("192.168.0.38", "Server"))

    # Summary
    logger.info(f"\n{'=' * 60}")
    logger.info("Test Summary")
    logger.info(f"{'=' * 60}")
    logger.info(f"Living Room (192.168.0.17): {'[PASS]' if results[0] else '[FAIL]'}")
    logger.info(f"Kitchen (192.168.0.137): {'[PASS]' if results[1] else '[FAIL]'}")
    logger.info(f"Server (192.168.0.38): {'[PASS]' if results[2] else '[FAIL]'}")
    logger.info(
        f"\nOverall: {'[SUCCESS] All tests passed' if all(results) else '[FAILED] Some tests failed'}"
    )

    return 0 if all(results) else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n\n[INTERRUPTED] Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.info(f"\n[FATAL ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
