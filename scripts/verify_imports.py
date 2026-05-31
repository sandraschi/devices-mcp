import logging
import os
import sys

logger = logging.getLogger(__name__)


logger.info(f"Current Working Directory: {os.getcwd()}")
logger.info(f"Python Path: {sys.path}")

try:
    import devices_mcp

    logger.info("Successfully imported devices_mcp")
    logger.info(f"Package location: {devices_mcp.__file__}")
except ImportError as e:
    logger.info(f"Failed to import devices_mcp: {e}")

import importlib.util

if importlib.util.find_spec("devices_mcp.integrations.vbot_client") is not None:
    logger.info("Successfully imported VbotClient module")
else:
    logger.info("Failed to import VbotClient module (not installed)")
