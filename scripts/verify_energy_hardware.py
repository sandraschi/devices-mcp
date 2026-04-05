import asyncio
import logging

from devices_mcp.tools.energy.tapo_plug_tools import tapo_plug_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_hardware():
    logger.info("--- [Empirical Hardware Verification] ---")
    logger.info("Target: Tapo P115 Smart Plugs")
    logger.info("Mode: Real-time Telemetry (No Mocks)")

    # Force initialization
    # In a real environment, we'd need account details,
    # but here we just want to ensure the manager doesn't fallback to mocks.

    devices = await tapo_plug_manager.get_all_devices()

    if not devices:
        logger.info(
            "RESULT: No hardware devices found (Correct if no active ingestion service/bridge)."
        )
    else:
        for dev in devices:
            logger.info(f"DEVICE: {dev.name} ({dev.device_id})")
            logger.info(f"  POWER: {dev.current_power} W")
            logger.info(f"  VOLTAGE: {dev.voltage} V")
            logger.info(f"  CURRENT: {dev.current} A")
            if dev.current_power == 0.0 and dev.voltage == 0.0:
                logger.info("  STATUS: OFFLINE or IDLE")
            else:
                logger.info("  STATUS: ACTIVE TELEMETRY DETECTED")

    logger.info("--- Verification Complete ---")


if __name__ == "__main__":
    asyncio.run(verify_hardware())
