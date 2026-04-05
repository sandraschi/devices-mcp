"""Turn on Zojirushi hot water dispenser."""

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


sys.path.insert(0, str(Path("src")))

from devices_mcp.ingest.tapo_p115 import TapoP115IngestionService


async def turn_on():
    service = TapoP115IngestionService()
    host = "192.168.0.17"

    logger.info("Turning on Zojirushi hot water dispenser...")
    await service.control_device(host, turn_on=True)
    logger.info("[OK] Turned ON")

    await asyncio.sleep(2)
    snapshot = await service._fetch_device_snapshot(host)
    if snapshot:
        logger.info(f"State: {'ON' if snapshot.get('power_state') else 'OFF'}")
        logger.info(f"Power: {snapshot.get('current_power')}W")


asyncio.run(turn_on())
