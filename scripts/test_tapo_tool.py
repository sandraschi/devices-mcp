#!/usr/bin/env python3
"""Test the unified tapo tool."""

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# Import the actual function
from devices_mcp.tools.portmanteau.tapo_control import tapo

logger.info("Testing tapo tool...\n")


async def test_action(action: str, **kwargs):
    """Test a tapo action."""
    logger.info(f"Testing: tapo(action='{action}', {kwargs})")
    try:
        result = await tapo(action=action, **kwargs)
        if result.get("success"):
            data = result.get("data", {})
            if "lights" in data:
                logger.info(f"  [OK] Found {data.get('count', 0)} lights")
                for light in data.get("lights", [])[:3]:
                    logger.info(
                        f"    - {light.get('name')} (ID: {light.get('light_id')}) - {'ON' if light.get('on') else 'OFF'}"
                    )
            elif "devices" in data:
                logger.info(f"  [OK] Found {data.get('count', 0)} devices")
                for device in data.get("devices", [])[:3]:
                    logger.info(
                        f"    - {device.get('name')} (ID: {device.get('device_id')}) - {'ON' if device.get('power_state') else 'OFF'}"
                    )
            else:
                logger.info(f"  [OK] Success: {result}")
        else:
            logger.info(f"  [ERROR] Error: {result.get('error')}")
    except Exception as e:
        logger.info(f"  [EXCEPTION] Exception: {e}")
    logger.info()


async def main():
    # Test list lights
    await test_action("list lights")

    # Test list plugs
    await test_action("list plugs")


if __name__ == "__main__":
    asyncio.run(main())
