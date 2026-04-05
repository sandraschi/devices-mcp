"""Debug camera streaming issues."""

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from devices_mcp.core.server import TapoCameraServer


async def debug_camera_streaming(camera_id: str):
    """Debug streaming issues for a specific camera."""
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Debugging streaming for camera: {camera_id}")
    logger.info(f"{'=' * 60}")

    try:
        # Get server instance
        server = await TapoCameraServer.get_instance()

        # Get camera manager
        if not hasattr(server, "camera_manager") or not server.camera_manager:
            logger.info("❌ No camera manager available")
            return

        # Get camera
        camera = server.camera_manager.cameras.get(camera_id)
        if not camera:
            logger.info(f"❌ Camera {camera_id} not found")
            return

        logger.info(f"[OK] Found camera: {camera}")
        logger.info(f"   Type: {camera.config.type}")
        logger.info(f"   Name: {camera.config.name}")

        # Check if camera is connected
        is_connected = await camera.is_connected()
        logger.info(f"   Connected: {is_connected}")

        if not is_connected:
            logger.info("[ERROR] Camera is not connected - cannot stream")
            return

        # Try to get stream URL
        logger.info("\n[DEBUG] Testing get_stream_url()...")
        try:
            stream_url = await asyncio.wait_for(camera.get_stream_url(), timeout=15.0)
            if stream_url:
                logger.info(f"[OK] Got stream URL: {stream_url[:50]}...")
            else:
                logger.info("[ERROR] get_stream_url() returned None")
        except asyncio.TimeoutError:
            logger.info("[ERROR] get_stream_url() timed out (15s)")
        except Exception as e:
            logger.info(f"[ERROR] get_stream_url() failed: {e}")
            import traceback

            traceback.print_exc()

        # Test snapshot (should work if camera is online)
        logger.info("\n[DEBUG] Testing snapshot...")
        try:
            snapshot = await camera.get_snapshot()
            if snapshot:
                logger.info(f"[OK] Snapshot successful (size: {len(snapshot)} bytes)")
            else:
                logger.info("[ERROR] Snapshot returned None")
        except Exception as e:
            logger.info(f"[ERROR] Snapshot failed: {e}")

    except Exception as e:
        logger.info(f"❌ Debug failed: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Debug kitchen camera streaming."""
    logger.info("=" * 60)
    logger.info("Camera Streaming Debug Tool")
    logger.info("=" * 60)

    await debug_camera_streaming("kitchen_cam")


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        logger.info("\n\n[INTERRUPTED] Debug cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.info(f"\n[FATAL ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
