"""Patch script to fix ring_doorbell imports.

This module patches websockets imports for ring_doorbell compatibility.
Uses logging instead of print to avoid corrupting MCP stdio protocol.
"""

import importlib
import logging

# Get logger - will be configured by the main server
logger = logging.getLogger(__name__)


def patch_ring_doorbell() -> bool:
    """Patch the ring_doorbell package to fix imports.

    Returns:
        bool: True if patching succeeded, False otherwise.
    """
    try:
        # First, try to import the websockets package directly
        import websockets

        logger.info(f"Websockets found: {websockets.__file__}")

        # Try to import the specific module that's failing
        try:
            from websockets.asyncio.client import connect  # noqa: F401

            logger.info("websockets.asyncio.client OK")
        except ImportError as e:
            logger.info(f"Patching websockets.asyncio: {e}")
            # If the direct import fails, try to patch the module
            try:
                websockets.asyncio = importlib.import_module("websockets.asyncio")
                logger.info("Patched websockets.asyncio OK")
            except ImportError as patch_error:
                logger.warning(f"Failed to patch websockets.asyncio: {patch_error}")
                return False

        # Now try to import the ring_doorbell package
        try:
            from ring_doorbell.webrtcstream import RingWebRtcStream  # noqa: F401

            logger.info("RingWebRtcStream OK - Ring integration enabled")
            return True
        except ImportError as e:
            logger.info(f"RingWebRtcStream not available: {e} (Ring WebRTC disabled)")
            # This is not a fatal error - Ring integration is optional
            return True

    except ImportError as e:
        logger.info(f"Websockets not installed - Ring integration disabled: {e}")
        # Websockets not installed - Ring features won't work but that's OK
        return True


if __name__ == "__main__":
    # Configure logging for standalone testing
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(levelname)s - %(message)s",
    )
    logger.info("Attempting to patch ring_doorbell...")
    if patch_ring_doorbell():
        logger.info("Successfully patched ring_doorbell!")
    else:
        logger.error("Failed to patch ring_doorbell.")
