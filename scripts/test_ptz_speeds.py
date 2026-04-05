"""Test different PTZ speed values for Tapo C200."""

import asyncio
import sys
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from devices_mcp.core.server import TapoCameraServer


async def test_ptz_speeds(camera_id: str):
    """Test different PTZ speed values."""
    logger.info(f"\n{'='*60}")
    logger.info(f"Testing PTZ speeds for camera: {camera_id}")
    logger.info(f"{'='*60}")

    try:
        # Get server instance
        server = await TapoCameraServer.get_instance()

        # Get camera
        camera = server.camera_manager.cameras.get(camera_id)
        if not camera:
            logger.info(f"[ERROR] Camera {camera_id} not found")
            return

        logger.info(f"[OK] Found camera: {camera.config.name}")

        # Test different speed values
        test_speeds = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]

        for speed in test_speeds:
            logger.info(f"\n[TEST] Testing speed: {speed}")
            try:
                # Move right
                logger.info(f"   Moving RIGHT at speed {speed} for 2 seconds...")
                await camera.ptz_move(pan=speed, tilt=0, zoom=0)
                await asyncio.sleep(2.0)
                await camera.ptz_stop()

                # Wait a moment
                await asyncio.sleep(0.5)

                # Move left to return
                logger.info(f"   Moving LEFT at speed {speed} for 2 seconds...")
                await camera.ptz_move(pan=-speed, tilt=0, zoom=0)
                await asyncio.sleep(2.0)
                await camera.ptz_stop()

                logger.info(f"[OK] Speed {speed} test completed")

            except Exception as e:
                logger.info(f"[ERROR] Speed {speed} test failed: {e}")

            # Wait between tests
            await asyncio.sleep(1.0)

        # Test tilt (up/down)
        logger.info("
[TEST] Testing TILT movements..."        try:
            logger.info("   Moving UP for 2 seconds...")
            await camera.ptz_move(pan=0, tilt=0.5, zoom=0)
            await asyncio.sleep(2.0)
            await camera.ptz_stop()

            await asyncio.sleep(0.5)

            logger.info("   Moving DOWN for 2 seconds...")
            await camera.ptz_move(pan=0, tilt=-0.5, zoom=0)
            await asyncio.sleep(2.0)
            await camera.ptz_stop()

            logger.info("[OK] Tilt test completed")

        except Exception as e:
            logger.info(f"[ERROR] Tilt test failed: {e}")

        # Test zoom if available
        logger.info("
[TEST] Testing ZOOM..."        try:
            logger.info("   Zooming IN for 2 seconds...")
            await camera.ptz_move(pan=0, tilt=0, zoom=0.3)
            await asyncio.sleep(2.0)
            await camera.ptz_stop()

            await asyncio.sleep(0.5)

            logger.info("   Zooming OUT for 2 seconds...")
            await camera.ptz_move(pan=0, tilt=0, zoom=-0.3)
            await asyncio.sleep(2.0)
            await camera.ptz_stop()

            logger.info("[OK] Zoom test completed")

        except Exception as e:
            logger.info(f"[ERROR] Zoom test failed: {e}")

        logger.info("
[COMPLETE] PTZ speed testing finished"        logger.info("Recommended speed settings for Tapo C200:")
        logger.info("  - Pan/Tilt: 0.5-0.7 (good balance of speed and control)")
        logger.info("  - Zoom: 0.3 (slower for precision)")

    except Exception as e:
        logger.info(f"[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Test PTZ speeds on kitchen camera."""
    logger.info("="*60)
    logger.info("PTZ Speed Test - Tapo C200 Camera")
    logger.info("="*60)
    logger.info("This will move the camera - ensure it's safe to do so!")
    logger.info("Press Ctrl+C to stop early")
    logger.info("="*60)

    await test_ptz_speeds("kitchen_cam")


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        logger.info("\n\n[INTERRUPTED] PTZ speed test cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.info(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
