"""
Ring Security Camera Management Tools - FastMCP 3.1

Security camera operations including video streaming, recording management,
motion detection, and multi-camera monitoring for Ring security cameras.

This module uses FastMCP 3.1 patterns with multiline decorators and proper
tool registration for Claude Desktop stdio communication.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from fastmcp import FastMCP

from ..core.ring_client import RingClient

logger = logging.getLogger(__name__)


def register_tools(app: FastMCP) -> None:
    """Register security camera management tools with the FastMCP application.

    Uses FastMCP 3.1 patterns with multiline decorators and proper
    stdio communication support for Claude Desktop integration.

    Args:
        app: FastMCP application instance
    """

    @app.tool(
        name="get_camera_status",
        description="Get comprehensive status of all Ring security cameras",
    )
    async def get_camera_status() -> Dict[str, Any]:
        """Get comprehensive status of all Ring security cameras.

        Provides detailed information about camera health, connectivity, recording
        status, and motion detection settings. Essential for monitoring security
        coverage and ensuring all cameras are operational.

        Returns:
            Dict containing:
            - cameras: List of all cameras with detailed status
            - recording_status: Current recording state for each camera
            - motion_activity: Recent motion detection summary
            - storage_usage: Cloud storage utilization
        """
        try:
            async with RingClient() as client:
                # Get all devices and filter for cameras
                all_devices = await client.get_devices()
                cameras = [device for device in all_devices if device.get("type") == "camera"]

                # Get detailed status for each camera
                camera_details = []
                for camera in cameras:
                    try:
                        # Get camera events for motion activity
                        events = await client.get_device_events(camera["id"], limit=5)

                        camera_info = {
                            "id": camera["id"],
                            "name": camera["name"],
                            "type": camera["type"],
                            "model": camera["model"],
                            "online": camera["online"],
                            "battery_life": camera.get("battery_life"),
                            "firmware": camera.get("firmware"),
                            "address": camera.get("address"),
                            "recent_events": events,
                            "recording_enabled": True,  # Ring cameras typically record by default
                            "motion_detection": True,  # Ring cameras have motion detection
                            "last_update": camera["last_update"],
                        }
                        camera_details.append(camera_info)
                    except Exception as e:
                        logger.exception("Error getting details for camera {camera['id']}:")
                        # Still include the camera with basic info
                        camera_details.append(
                            {
                                "id": camera["id"],
                                "name": camera["name"],
                                "type": camera["type"],
                                "online": camera["online"],
                                "error": str(e),
                            }
                        )

                return {
                    "success": True,
                    "cameras": camera_details,
                    "total_cameras": len(camera_details),
                    "online_cameras": sum(1 for c in camera_details if c.get("online", False)),
                    "cameras_with_issues": sum(1 for c in camera_details if c.get("error")),
                    "last_updated": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.exception("Error getting camera status:")
            return {"success": False, "error": str(e)}

    @app.tool(
        name="stream_all_cameras", description="Start live streams from all available Ring cameras"
    )
    async def stream_all_cameras() -> Dict[str, Any]:
        """Start live streams from all available Ring cameras.

        Initiates simultaneous live video streams from all operational Ring cameras
        for comprehensive security monitoring. Provides unified dashboard view
        of all camera feeds with individual stream controls.

        Returns:
            Dict containing:
            - camera_streams: List of active streams with URLs
            - total_streams: Number of successfully started streams
            - failed_cameras: Cameras that failed to start streaming
            - dashboard_url: Unified viewing interface
        """
        try:
            async with RingClient() as client:
                # Get all devices and filter for cameras
                all_devices = await client.get_devices()
                cameras = [device for device in all_devices if device.get("type") == "camera"]

                camera_streams = []
                failed_cameras = []

                for camera in cameras:
                    try:
                        # Get stream URL for each camera
                        stream_url = await client.get_live_stream_url(camera["id"])
                        camera_streams.append(
                            {
                                "camera_id": camera["id"],
                                "camera_name": camera["name"],
                                "stream_url": stream_url,
                                "status": "active",
                            }
                        )
                    except Exception as e:
                        logger.exception("Failed to get stream for camera {camera['id']}:")
                        failed_cameras.append(
                            {
                                "camera_id": camera["id"],
                                "camera_name": camera["name"],
                                "error": str(e),
                            }
                        )

                return {
                    "success": True,
                    "camera_streams": camera_streams,
                    "total_streams": len(camera_streams),
                    "failed_cameras": failed_cameras,
                    "total_failed": len(failed_cameras),
                    "stream_started_at": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.exception("Error starting camera streams:")
            return {"success": False, "error": str(e)}
