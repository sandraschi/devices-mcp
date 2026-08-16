import logging

logger = logging.getLogger(__name__)

# !/usr/bin/env python3
"""
Demo script showcasing Devices MCP features.

Demonstrates:
- ONVIF camera connection
- PTZ controls (pan, tilt, zoom)
- Snapshot capture
- Ring doorbell status
- Camera info display

Usage:
    python scripts/demo.py
    python scripts/demo.py --camera kitchen_cam
    python scripts/demo.py --no-ptz  # Skip PTZ movements
"""

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def demo_camera_info(camera):
    """Display camera information."""
    logger.info("\n📹 Camera Information")
    logger.info("=" * 50)
    info = await camera.get_info()
    for key, value in info.items():
        if key != "capabilities":
            logger.info(f"  {key}: {value}")
    if "capabilities" in info:
        logger.info("  Capabilities:")
        for cap, enabled in info["capabilities"].items():
            status = "✅" if enabled else "❌"
            logger.info(f"    {status} {cap}")


async def demo_camera_status(camera):
    """Display camera status."""
    logger.info("\n📊 Camera Status")
    logger.info("=" * 50)
    status = await camera.get_status()
    for key, value in status.items():
        logger.info(f"  {key}: {value}")


async def demo_ptz_movements(camera, camera_name: str):
    """Demonstrate PTZ movements."""
    logger.info("\n🎮 PTZ Demo")
    logger.info("=" * 50)

    movements = [
        ("Looking LEFT", -0.3, 0, 0, 1.5),
        ("Looking RIGHT", 0.3, 0, 0, 1.5),
        ("Looking UP", 0, 0.3, 0, 1.5),
        ("Looking DOWN", 0, -0.3, 0, 1.5),
        ("Centering...", 0, 0, 0, 0.5),
        ("Zooming IN", 0, 0, 0.3, 2.0),
        ("Zooming OUT", 0, 0, -0.3, 2.0),
    ]

    for description, pan, tilt, zoom, duration in movements:
        logger.info(f"  🔄 {description}")
        await camera.ptz_move(pan=pan, tilt=tilt, zoom=zoom)
        await asyncio.sleep(duration)
        await camera.ptz_stop()
        await asyncio.sleep(0.3)

    logger.info("  ✅ PTZ demo complete!")


async def demo_snapshot(camera, camera_name: str):
    """Capture and save a snapshot."""
    logger.info("\n📸 Snapshot Demo")
    logger.info("=" * 50)

    snapshot_dir = Path("demo_snapshots")
    snapshot_dir.mkdir(exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = snapshot_dir / f"{camera_name}_{timestamp}.jpg"

    logger.info("  Capturing snapshot...")
    image = await camera.capture_still(str(filename))
    logger.info(f"  ✅ Saved: {filename}")
    logger.info(f"  📐 Size: {image.size[0]}x{image.size[1]}")

    return filename


async def demo_ring_status():
    """Show Ring doorbell status."""
    logger.info("\n🔔 Ring Doorbell Status")
    logger.info("=" * 50)

    try:
        from devices_mcp.integrations.ring_client import get_ring_client

        client = get_ring_client()
        if not client or not client.is_initialized:
            logger.info("  ⚠️  Ring not initialized")
            return

        summary = await client.get_summary()
        logger.info(f"  Initialized: {summary.get('initialized', False)}")
        logger.info(f"  Doorbells: {summary.get('doorbell_count', 0)}")

        doorbells = await client.get_doorbells()
        for db in doorbells:
            logger.info(f"\n  📍 {db.get('name', 'Unknown')}")
            logger.info(f"     Battery: {db.get('battery_life', 'N/A')}%")
            logger.info(f"     WiFi: {db.get('wifi_signal_strength', 'N/A')} dBm")

    except Exception as e:
        logger.info(f"  ❌ Ring error: {e}")


async def demo_all_cameras():
    """List all available cameras."""
    logger.info("\n📷 Available Cameras")
    logger.info("=" * 50)

    try:
        from devices_mcp.core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        cameras = await server.camera_manager.list_cameras()

        for cam in cameras:
            status = cam.get("status", {})
            connected = status.get("connected", False) if isinstance(status, dict) else False
            icon = "🟢" if connected else "🔴"
            logger.info(f"  {icon} {cam['name']} ({cam['type']})")
            if isinstance(status, dict):
                logger.info(f"     Model: {status.get('model', 'Unknown')}")
                logger.info(f"     Resolution: {status.get('resolution', 'Unknown')}")

    except Exception as e:
        logger.info(f"  ❌ Error listing cameras: {e}")


async def run_demo(camera_name: str = "kitchen_cam", skip_ptz: bool = False):
    """Run the full demo."""
    logger.info("\n" + "=" * 60)
    logger.info("   🏠 Home Security MCP - Feature Demo")
    logger.info("=" * 60)

    # Import camera classes
    from devices_mcp.camera.base import CameraConfig, CameraType
    from devices_mcp.camera.onvif_camera import ONVIFBasedCamera
    from devices_mcp.config import get_config

    # Load config
    config = get_config()
    cameras_config = config.get("cameras", {})

    if camera_name not in cameras_config:
        logger.info(f"\n❌ Camera '{camera_name}' not found in config.yaml")
        logger.info(f"   Available: {list(cameras_config.keys())}")
        return

    cam_config = cameras_config[camera_name]
    cam_config["name"] = camera_name

    # Create camera
    logger.info(f"\n🔌 Connecting to {camera_name}...")
    camera_cfg = CameraConfig(name=camera_name, type=CameraType(cam_config["type"]), params=cam_config["params"])
    camera = ONVIFBasedCamera(camera_cfg)

    try:
        await camera.connect()
        logger.info("   ✅ Connected!")

        # Run demos
        await demo_camera_info(camera)
        await demo_camera_status(camera)

        if not skip_ptz:
            await demo_ptz_movements(camera, camera_name)
        else:
            logger.info("\n⏭️  Skipping PTZ demo (--no-ptz)")

        await demo_snapshot(camera, camera_name)
        await demo_ring_status()
        await demo_all_cameras()

    finally:
        await camera.disconnect()

    logger.info("\n" + "=" * 60)
    logger.info("   ✅ Demo Complete!")
    logger.info("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Devices MCP Demo")
    parser.add_argument(
        "--camera",
        "-c",
        default="kitchen_cam",
        help="Camera name from config.yaml (default: kitchen_cam)",
    )
    parser.add_argument("--no-ptz", action="store_true", help="Skip PTZ movement demo")
    parser.add_argument("--list", action="store_true", help="Just list available cameras")

    args = parser.parse_args()

    if args.list:
        asyncio.run(demo_all_cameras())
    else:
        asyncio.run(run_demo(args.camera, args.no_ptz))


if __name__ == "__main__":
    main()
