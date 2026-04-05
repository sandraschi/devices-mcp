#!/usr/bin/env python3
"""
Quick script to add a test camera to the Devices MCP system.
"""

import asyncio
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


async def add_test_webcam():
    """Add a USB webcam for testing."""
    try:
        from devices_mcp.core.server import DevicesMCPServer

        logger.info("CAMERA: Adding test USB webcam...")

        # Get the server instance
        server = await DevicesMCPServer.get_instance()

        # Add the camera using the camera manager
        config = {
            "name": "test_webcam",
            "type": "webcam",
            "params": {},  # Empty params for webcam
        }

        success = await server.camera_manager.add_camera(config)

        if success:
            logger.info("SUCCESS: Test webcam added successfully!")
            return True
        logger.info("ERROR Failed to add webcam: Camera manager returned False")
        return False

    except Exception as e:
        logger.info(f"ERROR Failed to add webcam: {e}")
        import traceback

        traceback.print_exc()
        return False


async def add_tapo_camera(ip_address, username, password, camera_name="tapo_camera"):
    """Add a Tapo camera with provided details."""
    try:
        from devices_mcp.core.server import TapoCameraServer

        logger.info(f"CAMERA: Adding Tapo camera '{camera_name}' at {ip_address}...")

        # Get the server instance
        server = await TapoCameraServer.get_instance()

        # Add the camera using the camera manager
        config = {
            "name": camera_name,
            "type": "tapo",
            "params": {"host": ip_address, "username": username, "password": password},
        }

        success = await server.camera_manager.add_camera(config)

        if success:
            logger.info("SUCCESS: Tapo camera added successfully!")
            return True
        logger.info("ERROR Failed to add Tapo camera: Camera manager returned False")
        return False

    except Exception as e:
        logger.info(f"ERROR Failed to add Tapo camera: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Add a camera to Devices MCP")
    parser.add_argument(
        "--type",
        choices=["webcam", "tapo"],
        default="webcam",
        help="Camera type to add",
    )
    parser.add_argument("--name", default="test_webcam", help="Camera name")
    parser.add_argument("--ip", help="Camera IP address (for Tapo)")
    parser.add_argument("--username", default="admin", help="Camera username")
    parser.add_argument("--password", default="admin", help="Camera password")

    args = parser.parse_args()

    if args.type == "tapo":
        if not args.ip:
            logger.info("ERROR Error: --ip is required for Tapo cameras")
            return 1

        success = asyncio.run(add_tapo_camera(args.ip, args.username, args.password, args.name))
    else:
        success = asyncio.run(add_test_webcam())

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
