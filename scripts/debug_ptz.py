"""Debug PTZ functionality for Tapo C200 cameras."""

import asyncio
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from devices_mcp.core.server import TapoCameraServer


async def debug_ptz_capabilities(camera_id: str):
    """Debug PTZ capabilities for a specific camera."""
    logger.info(f"\n{'=' * 60}")
    logger.info(f"Debugging PTZ for camera: {camera_id}")
    logger.info(f"{'=' * 60}")

    try:
        # Get server instance
        server = await TapoCameraServer.get_instance()

        # Get camera manager
        if not hasattr(server, "camera_manager") or not server.camera_manager:
            logger.info("[ERROR] No camera manager available")
            return

        # Get camera
        camera = server.camera_manager.cameras.get(camera_id)
        if not camera:
            logger.info(f"[ERROR] Camera {camera_id} not found")
            return

        logger.info(f"[OK] Found camera: {camera}")
        logger.info(f"   Type: {camera.config.type}")
        logger.info(f"   Name: {camera.config.name}")

        # Check if camera is connected
        is_connected = await camera.is_connected()
        logger.info(f"   Connected: {is_connected}")

        if not is_connected:
            logger.info("[ERROR] Camera is not connected - cannot test PTZ")
            return

        # Get camera status to check PTZ capability
        status = await camera.get_status()
        logger.info("\n[STATUS] Camera Status:")
        logger.info(f"   PTZ Capable: {status.get('ptz_capable', False)}")
        logger.info(f"   Model: {status.get('model', 'Unknown')}")
        logger.info(f"   Manufacturer: {status.get('manufacturer', 'Unknown')}")

        # Check if camera has PTZ methods
        logger.info("\n[STATUS] PTZ Methods Available:")
        ptz_methods = ["ptz_move", "ptz_stop", "ptz_go_to_preset", "ptz_get_presets", "ptz_go_home"]
        for method in ptz_methods:
            has_method = hasattr(camera, method)
            logger.info(f"   {method}: {'YES' if has_method else 'NO'}")

        if not status.get("ptz_capable", False):
            logger.info("[ERROR] Camera reports as not PTZ capable - cannot test PTZ functions")
            return

        # Test PTZ service connection
        logger.info("\n[TEST] Testing PTZ Service Connection...")
        try:
            # Try to access the underlying ONVIF PTZ service
            if hasattr(camera, "_camera") and camera._camera:
                ptz_service = camera._camera.get_ptz_service()
                logger.info("[OK] PTZ service accessible")

                # Get PTZ status
                profiles = camera._camera.get_media_profiles()
                if profiles:
                    logger.info(f"[OK] Found {len(profiles)} media profiles")
                    profile = profiles[0]

                    # Try to get PTZ configuration
                    try:
                        ptz_config = ptz_service.GetConfiguration(profile.token)
                        logger.info("[OK] PTZ Configuration retrieved")
                        logger.info(
                            f"   DefaultTimeout: {getattr(ptz_config, 'DefaultTimeout', 'N/A')}"
                        )
                        logger.info(
                            f"   PanTiltLimits: {getattr(ptz_config, 'PanTiltLimits', 'N/A')}"
                        )
                        logger.info(f"   ZoomLimits: {getattr(ptz_config, 'ZoomLimits', 'N/A')}")
                    except Exception as e:
                        logger.info(f"[WARN] Could not get PTZ config: {e}")

                    # Try to get PTZ status
                    try:
                        ptz_status = ptz_service.GetStatus(profile.token)
                        logger.info("[OK] PTZ Status retrieved")
                        if hasattr(ptz_status, "Position"):
                            pos = ptz_status.Position
                            if hasattr(pos, "PanTilt"):
                                logger.info(f"   Current Pan: {getattr(pos.PanTilt, 'x', 'N/A')}")
                                logger.info(f"   Current Tilt: {getattr(pos.PanTilt, 'y', 'N/A')}")
                            if hasattr(pos, "Zoom"):
                                logger.info(f"   Current Zoom: {getattr(pos.Zoom, 'x', 'N/A')}")
                    except Exception as e:
                        logger.info(f"[WARN] Could not get PTZ status: {e}")

                else:
                    logger.info("[ERROR] No media profiles found")

            else:
                logger.info("[ERROR] Cannot access underlying ONVIF camera object")

        except Exception as e:
            logger.info(f"[ERROR] PTZ service connection failed: {e}")

        # Test small PTZ movement
        logger.info("\n[TEST] Testing Small PTZ Movement...")
        try:
            # Move right for 1 second
            logger.info("   Moving RIGHT for 1 second (speed=0.3)...")
            await camera.ptz_move(pan=0.3, tilt=0, zoom=0)  # Small pan right
            await asyncio.sleep(1.0)
            await camera.ptz_stop()
            logger.info("[OK] Small PTZ movement test completed")

        except Exception as e:
            logger.info(f"[ERROR] PTZ movement test failed: {e}")
            import traceback

            traceback.print_exc()

        # Test presets
        logger.info("\n[TEST] Testing PTZ Presets...")
        try:
            if hasattr(camera, "ptz_get_presets"):
                presets = await camera.ptz_get_presets()
                logger.info(f"[OK] Found {len(presets)} presets")
                for preset in presets[:3]:  # Show first 3
                    logger.info(
                        f"   - {preset.get('name', 'Unknown')}: {preset.get('token', 'Unknown')}"
                    )
            else:
                logger.info("[ERROR] ptz_get_presets method not available")

        except Exception as e:
            logger.info(f"[ERROR] Preset retrieval failed: {e}")

    except Exception as e:
        logger.info(f"[ERROR] Debug failed: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Debug kitchen camera PTZ."""
    logger.info("=" * 60)
    logger.info("PTZ Debug Tool - Tapo C200 Camera")
    logger.info("=" * 60)

    await debug_ptz_capabilities("kitchen_cam")


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        logger.info("\n\n[INTERRUPTED] PTZ debug cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.info(f"\n[FATAL ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
