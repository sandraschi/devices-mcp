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

try:
    from devices_mcp.integrations.vbot_client import VbotClient

    logger.info("Successfully imported VbotClient")
except ImportError as e:
    logger.info(f"Failed to import VbotClient: {e}")
