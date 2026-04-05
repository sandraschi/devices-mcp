#!/usr/bin/env python3
"""List all Hue scenes to see what they are."""

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from collections import defaultdict

from devices_mcp.tools.lighting.hue_tools import hue_manager


async def main():
    await hue_manager.initialize()
    scenes = await hue_manager.get_all_scenes()

    logger.info(f"\nTotal scenes: {len(scenes)}\n")
    logger.info("=" * 60)

    # Group by room/group
    by_group = defaultdict(list)
    for scene in scenes:
        group = scene.group or "Ungrouped"
        by_group[group].append(scene.name)

    # Print grouped
    for group in sorted(by_group.keys()):
        scenes_list = sorted(by_group[group])
        logger.info(f"\n{group}: {len(scenes_list)} scenes")
        logger.info("-" * 60)
        for name in scenes_list:
            logger.info(f"  • {name}")


if __name__ == "__main__":
    asyncio.run(main())
