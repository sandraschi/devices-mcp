"""
Media Management Portmanteau Tool
Consolidates all media-related operations into a single tool with action-based interface.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

from devices_mcp.tools.media.image_capture_tool import ImageCaptureTool
from devices_mcp.tools.media.video_recording_tool import VideoRecordingTool

logger = logging.getLogger(__name__)
MEDIA_ACTIONS = {
    "capture": "Capture image",
    "capture_still": "Capture still image",
    "analyze": "Analyze image",
    "start_recording": "Start video recording",
    "stop_recording": "Stop video recording",
    "get_stream_url": "Get stream URL",
    "capabilities": "Get media capabilities",
}


def register_media_management_tool(mcp: FastMCP) -> None:
    """Register the media management portmanteau tool."""

    @mcp.tool()
    async def media_management(
        action: Literal[
            "capture",
            "capture_still",
            "analyze",
            "start_recording",
            "stop_recording",
            "get_stream_url",
            "capabilities",
        ],
        camera_name: str | None = None,
        quality: str | None = None,
        save_to_temp: bool = False,
        analyze: bool = False,
        prompt: str | None = None,
        duration: int | None = None,
        output_dir: str | None = None,
    ) -> dict[str, Any]:
        """
        Comprehensive media management portmanteau tool.
        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 6+ separate tools (one per operation), this tool consolidates related
        media operations into a single interface. Prevents tool explosion (6+ tools → 1 tool) while maintaining
        full functionality and improving discoverability. Follows FastMCP 3.1+ best practices.
        Args:
            action (Literal, required): The operation to perform. Must be one of: "capture", "capture_still",
                "analyze", "start_recording", "stop_recording", "get_stream_url".
                - "capture": Capture image (requires: camera_name)
                - "capture_still": Capture still image (requires: camera_name)
                - "analyze": Analyze captured image (requires: camera_name, prompt)
                - "start_recording": Start video recording (requires: camera_name, duration)
                - "stop_recording": Stop video recording (requires: camera_name)
                - "get_stream_url": Get stream URL (requires: camera_name)
            camera_name (str | None): Camera name/ID. Required for: all operations.
            quality (str | None): Image/video quality. Used by: capture, capture_still, start_recording operations.
                Default: "high". Valid: "low", "medium", "high", "ultra"
            save_to_temp (bool): Save to temporary file. Used by: capture, capture_still operations. Default: False
            analyze (bool): Analyze captured image. Used by: capture, capture_still operations. Default: False
            prompt (str | None): Analysis prompt for image analysis. Required for: analyze operation.
                Example: "Detect people and objects"
            duration (int | None): Recording duration in seconds. Required for: start_recording operation.
            output_dir (str | None): Output directory for recordings. Used by: start_recording operation.
                Default: current directory
        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data (image data, stream URL, etc.)
                - error (str | None): Error message if success is False
        Examples:
            # Capture image
            result = await media_management(action="capture", camera_name="Front Door", quality="high")
            # Capture and analyze
            result = await media_management(action="capture", camera_name="Front Door", analyze=True, prompt="Detect people")
            # Start recording
            result = await media_management(action="start_recording", camera_name="Front Door", duration=60)
            # Get stream URL
            result = await media_management(action="get_stream_url", camera_name="Front Door")
        """
        try:
            if action not in MEDIA_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(MEDIA_ACTIONS.keys())}",
                }
            logger.info(f"Executing media management action: {action}")
            if action in ["capture", "capture_still", "analyze"]:
                if not camera_name:
                    return {
                        "success": False,
                        "message": "camera_name is required for this action",
                        "error": "camera_name is required for this action",
                    }
                if action == "analyze":
                    if not prompt:
                        return {
                            "success": False,
                            "message": "prompt is required for analyze action",
                            "error": "prompt is required for analyze action",
                        }
                tool = ImageCaptureTool()
                operation_map = {
                    "capture": "capture",
                    "capture_still": "still",
                    "analyze": "analyze",
                }
                result = await tool.execute(
                    operation=operation_map[action],
                    camera_id=camera_name,
                    quality=quality or "high",
                    save_to_temp=save_to_temp,
                    analyze=analyze,
                    prompt=prompt,
                )
                return {"success": True, "action": action, "data": result}
            if action in ["start_recording", "stop_recording", "get_stream_url"]:
                if not camera_name:
                    return {
                        "success": False,
                        "message": "camera_name is required for this action",
                        "error": "camera_name is required for this action",
                    }
                if action == "start_recording":
                    if not duration:
                        return {
                            "success": False,
                            "message": "duration is required for start_recording action",
                            "error": "duration is required for start_recording action",
                        }
                tool = VideoRecordingTool()
                operation_map = {
                    "start_recording": "start",
                    "stop_recording": "stop",
                    "get_stream_url": "stream_url",
                }
                result = await tool.execute(
                    operation=operation_map[action],
                    camera_id=camera_name,
                    duration=duration,
                    output_dir=output_dir,
                )
                return {"success": True, "action": action, "data": result}
            if action == "capabilities":
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "supported_actions": list(MEDIA_ACTIONS.keys()),
                        "image_formats": ["jpeg", "png", "raw"],
                        "resolutions": ["720p", "1080p", "4k"],
                        "quality_range": "1-100",
                        "analysis_types": ["objects", "faces", "motion"],
                    },
                }
            return {
                "success": False,
                "message": f"Action '{action}' not implemented",
                "error": f"Action '{action}' not implemented",
            }
        except Exception as e:
            logger.exception("Error in media management action '{action}':")
            return {
                "success": False,
                "message": f"Failed to execute action '{action}': {e!s}",
                "error": f"Failed to execute action '{action}': {e!s}",
            }
