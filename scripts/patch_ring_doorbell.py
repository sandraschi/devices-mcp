"""Patch script to fix ring_doorbell imports."""

import importlib
import logging

logger = logging.getLogger(__name__)


def patch_ring_doorbell():
    """Patch the ring_doorbell package to fix imports."""
    try:
        # First, try to import the websockets package directly
        import websockets

        logger.info(f"Websockets package found at: {websockets.__file__}")

        # Try to import the specific module that's failing
        try:
            importlib.import_module("websockets.asyncio.client")

            logger.info("Successfully imported websockets.asyncio.client")
        except ImportError as e:
            logger.info(f"Error importing websockets.asyncio.client: {e}")
            # If the direct import fails, try to patch the module
            websockets.asyncio = importlib.import_module("websockets.asyncio")
            logger.info("Patched websockets.asyncio")

        # Now try to import the ring_doorbell package
        try:
            importlib.import_module("ring_doorbell.webrtcstream")

            logger.info("Successfully imported RingWebRtcStream")
            return True
        except ImportError as e:
            logger.info(f"Error importing RingWebRtcStream: {e}")
            return False

    except ImportError as e:
        logger.info(f"Error importing websockets: {e}")
        return False


if __name__ == "__main__":
    logger.info("Attempting to patch ring_doorbell...")
    if patch_ring_doorbell():
        logger.info("Successfully patched ring_doorbell!")
    else:
        logger.info("Failed to patch ring_doorbell.")
