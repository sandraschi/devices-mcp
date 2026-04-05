"""
Media tools for Devices MCP.

This module contains tools for capturing and analyzing images and video streams.
"""

import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import Field

from devices_mcp.tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


@tool(name="capture_image")
class CaptureImageTool(BaseTool):
    """Tool to capture an image from the camera."""

    class Meta:
        name = "capture_image"
        description = "Capture an image from the camera"
        category = ToolCategory.MEDIA

        class Parameters:
            quality: str = Field(
                default="high",
                description="Image quality (high/medium/low)",
                json_schema_extra={"enum": ["high", "medium", "low"]},
            )
            save_to_disk: bool = Field(
                default=True, description="Whether to save the image to disk"
            )
            return_base64: bool = Field(
                default=True, description="Whether to return the image as base64"
            )

    quality: str
    save_to_disk: bool
    return_base64: bool

    async def execute(self) -> Dict[str, Any]:
        """Capture an image from the camera.

        Returns:
            Dict containing the image data or base64 string and metadata

        Raises:
            Exception: If there's an error capturing the image
        """
        try:
            from devices_mcp.core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()

            if not server.camera or not server._connected:
                return {
                    "status": "error",
                    "message": "No camera connected. Please connect to a camera first.",
                }

            # Capture image from real camera
            image = await server.camera.capture_still()

            result = {
                "status": "success",
                "message": "Image captured successfully",
                "timestamp": datetime.utcnow().isoformat(),
                "quality": self.quality,
                "image_size": image.size,
                "image_mode": image.mode,
            }

            # Save to disk if requested
            if self.save_to_disk:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"capture_{timestamp}.jpg"
                save_path = Path("captures") / filename
                save_path.parent.mkdir(exist_ok=True)

                # Adjust quality based on setting
                quality_map = {"high": 95, "medium": 75, "low": 50}
                save_quality = quality_map.get(self.quality, 75)

                image.save(save_path, "JPEG", quality=save_quality)
                result["saved_path"] = str(save_path)
                result["saved_to_disk"] = True
            else:
                result["saved_to_disk"] = False

            # Return base64 if requested
            if self.return_base64:
                import io

                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=quality_map.get(self.quality, 75))
                image_bytes = buffer.getvalue()
                image_base64 = base64.b64encode(image_bytes).decode("utf-8")
                result["base64_image"] = image_base64
                result["base64_available"] = True
            else:
                result["base64_available"] = False

            return result

        except Exception as e:
            logger.exception("Error capturing image:")
            return {"status": "error", "message": f"Failed to capture image: {e!s}"}


@tool(name="find_similar_images")
class FindSimilarImagesTool(BaseTool):
    """Tool to find similar images using DINOv3."""

    class Meta:
        name = "find_similar_images"
        description = "Find images similar to the query image using DINOv3"
        category = ToolCategory.MEDIA

        class Parameters:
            image_path: str = Field(..., description="Path to the query image")
            threshold: float = Field(
                default=0.7, ge=0.0, le=1.0, description="Similarity threshold (0.0 to 1.0)"
            )
            max_results: int = Field(
                default=5, ge=1, description="Maximum number of similar images to return"
            )

    image_path: str
    threshold: float = 0.7
    max_results: int = 5

    async def execute(self) -> Dict[str, Any]:
        """Find images similar to the query image using DINOv3."""
        try:
            from ...core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()
            return await server.find_similar_images(
                image_path=self.image_path, threshold=self.threshold, limit=self.max_results
            )
        except Exception as e:
            logger.exception("Error finding similar images:")
            return {"status": "error", "message": f"Failed to find similar images: {e!s}"}


@tool(name="get_stream_url")
class GetStreamURLTool(BaseTool):
    """Tool to get the RTSP stream URL for the camera."""

    class Meta:
        name = "get_stream_url"
        description = "Get the RTSP stream URL for the camera"
        category = ToolCategory.MEDIA

        class Parameters:
            quality: str = Field(
                default="hd",
                description="Stream quality (hd/sd)",
                json_schema_extra={"enum": ["hd", "sd"]},
            )
            protocol: str = Field(
                default="rtsp",
                description="Stream protocol (rtsp/rtmp)",
                json_schema_extra={"enum": ["rtsp", "rtmp"]},
            )

    quality: str = "hd"
    protocol: str = "rtsp"

    async def execute(self) -> Dict[str, Any]:
        """Get the RTSP stream URL for the camera."""
        try:
            from ...core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()
            return await server.get_stream_url(quality=self.quality, protocol=self.protocol)
        except Exception as e:
            logger.exception("Error getting stream URL:")
            return {"status": "error", "message": f"Failed to get stream URL: {e!s}"}


@tool(name="start_recording")
class StartRecordingTool(BaseTool):
    """Tool to start recording video from the camera."""

    class Meta:
        name = "start_recording"
        description = "Start recording video from the camera"
        category = ToolCategory.MEDIA

        class Parameters:
            duration: int = Field(
                default=0, ge=0, description="Duration to record in seconds (0 for unlimited)"
            )
            output_dir: Optional[str] = Field(None, description="Directory to save the recording")

    duration: int = 0
    output_dir: Optional[str] = None

    async def execute(self) -> Dict[str, Any]:
        """Start recording video from the camera."""
        try:
            from ...core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()
            return await server.start_recording(
                duration=self.duration,
                output_dir=self.output_dir if hasattr(self, "output_dir") else None,
            )
        except Exception as e:
            logger.exception("Error starting recording:")
            return {"status": "error", "message": f"Failed to start recording: {e!s}"}


@tool(name="stop_recording")
class StopRecordingTool(BaseTool):
    """Tool to stop the current recording."""

    class Meta:
        name = "stop_recording"
        description = "Stop the current recording"
        category = ToolCategory.MEDIA

        class Parameters:
            pass

    async def execute(self) -> Dict[str, Any]:
        """Stop the current recording."""
        try:
            from ...core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()
            return await server.stop_recording()
        except Exception as e:
            logger.exception("Error stopping recording:")
            return {"status": "error", "message": f"Failed to stop recording: {e!s}"}


@tool(name="analyze_image")
class AnalyzeImageTool(BaseTool):
    """Tool to analyze images with multimodal LLM."""

    class Meta:
        name = "analyze_image"
        description = "Analyze one or more images with multimodal LLM"
        category = ToolCategory.ANALYSIS

        class Parameters:
            image_path: str = Field(..., description="Path to image file(s) or directory")
            prompt: str = Field(
                default="general", description="Analysis prompt or preset name (default: 'general')"
            )
            preset: Optional[str] = Field(
                None, description="Use a predefined analysis preset (overrides prompt)"
            )
            use_cache: bool = Field(default=True, description="Use cached results")
            batch_size: int = Field(default=4, ge=1, description="Max concurrent analyses")
            output_format: str = Field(
                default="full",
                description="Output format ('full', 'summary', or 'minimal')",
                json_schema_extra={"enum": ["full", "summary", "minimal"]},
            )
            confidence_threshold: float = Field(
                default=0.5, ge=0.0, le=1.0, description="Filter results by confidence (0.0-1.0)"
            )

    image_path: str
    prompt: str = "general"
    preset: Optional[str] = None
    use_cache: bool = True
    batch_size: int = 4
    output_format: str = "full"
    confidence_threshold: float = 0.5

    async def execute(self) -> Dict[str, Any]:
        """Analyze one or more images with multimodal LLM."""
        try:
            from ...core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()
            return await server.analyze_image(
                image_path=self.image_path,
                prompt=self.prompt,
                preset=self.preset,
                use_cache=self.use_cache,
                batch_size=self.batch_size,
                output_format=self.output_format,
                confidence_threshold=self.confidence_threshold,
            )
        except Exception as e:
            logger.exception("Error analyzing image:")
            return {"status": "error", "message": f"Failed to analyze image: {e!s}"}


@tool(name="security_scan")
class SecurityScanTool(BaseTool):
    """Tool to perform security scan across multiple cameras."""

    class Meta:
        name = "security_scan"
        description = "Perform security scan across multiple cameras"
        category = ToolCategory.SECURITY

        class Parameters:
            cameras: Optional[List[Dict[str, Any]]] = Field(
                None, description="List of camera configs (default: current camera)"
            )
            threat_types: List[str] = Field(
                default=["person", "unknown_person", "package"], description="Types to detect"
            )
            save_images: bool = Field(default=True, description="Save captured images")

    cameras: Optional[List[Dict[str, Any]]] = None
    threat_types: List[str] = ["person", "unknown_person", "package"]
    save_images: bool = True

    async def execute(self) -> Dict[str, Any]:
        """Perform security scan across multiple cameras."""
        try:
            from ...core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()
            return await server.security_scan(
                cameras=self.cameras, threat_types=self.threat_types, save_images=self.save_images
            )
        except Exception as e:
            logger.exception("Error performing security scan:")
            return {
                "status": "error",
                "message": f"Failed to perform security scan: {e!s}",
                "timestamp": datetime.utcnow().isoformat(),
            }


@tool(name="capture_still")
class CaptureStillTool(BaseTool):
    """Tool to capture still images from one or more cameras."""

    class Meta:
        name = "capture_still"
        description = "Capture still image(s) from one or more cameras"
        category = ToolCategory.MEDIA

        class Parameters:
            camera_name: str = Field(..., description="Name of the camera to capture from")
            save_to_temp: bool = Field(True, description="Save to temporary directory")
            quality: int = Field(85, description="Image quality (1-100)", ge=1, le=100)
            include_timestamp: bool = Field(True, description="Include timestamp in filename")
            analyze: bool = Field(False, description="Analyze the captured image")
            prompt: str = Field("general", description="Analysis prompt or preset name")
            group: Optional[str] = Field(None, description="Camera group name")
            batch_size: int = Field(4, description="Batch size for multiple cameras", ge=1)
            use_cache: bool = Field(True, description="Use cached results")

    camera_name: str
    save_to_temp: bool = True
    quality: int = 85
    include_timestamp: bool = True
    analyze: bool = False
    prompt: str = "general"
    group: Optional[str] = None
    batch_size: int = 4
    use_cache: bool = True

    async def execute(self) -> Dict[str, Any]:
        """Capture still images from cameras with optional analysis capabilities.

        Takes high-quality snapshots from specified cameras with configurable options
        for image quality, storage, and automatic analysis. Supports single camera capture,
        camera groups, and batch processing for efficient multi-camera operations.

        Parameters:
            camera_name: Name of the camera to capture from (required)
                - Must match an existing camera name exactly
                - Camera must be connected and operational
                - Case-sensitive matching
            save_to_temp: Whether to save images to temporary directory (optional, default: True)
                - True: Save to system temp directory (auto-cleaned)
                - False: Save to configured recordings directory
                - Affects storage location and cleanup behavior
            quality: JPEG image quality percentage (optional, default: 85)
                - Range: 1-100 (1=lowest quality, 100=highest quality)
                - Higher quality increases file size
                - 85 provides good balance of quality and size
            include_timestamp: Whether to include timestamp in filename (optional, default: True)
                - True: Adds ISO timestamp to filename for uniqueness
                - False: Uses simple filename without timestamp
                - Recommended for archival purposes
            analyze: Whether to perform AI analysis on captured image (optional, default: False)
                - True: Runs image analysis after capture
                - False: Only captures image without analysis
                - Analysis results included in response
            prompt: Analysis prompt or preset name (optional, default: "general")
                - "general": General image description
                - "security": Security-focused analysis
                - "people": Person detection and counting
                - "objects": Object identification
                - Custom prompts supported
            group: Camera group name for batch capture (optional, default: None)
                - If specified, captures from all cameras in group
                - Overrides camera_name parameter
                - Useful for synchronized multi-camera capture
            batch_size: Number of cameras to process simultaneously (optional, default: 4)
                - Controls parallelism for group captures
                - Higher values may improve speed but increase resource usage
                - Lower values reduce memory usage
            use_cache: Whether to use cached analysis results (optional, default: True)
                - True: Reuse previous analysis for similar images
                - False: Always perform fresh analysis
                - Affects performance vs accuracy trade-off

        Returns:
            Dictionary containing:
                - success: Boolean indicating if capture was successful
                - camera_name: Name of camera that was captured from
                - image_path: Full path to saved image file (if saved)
                - image_data: Base64 encoded image data (if not saved)
                - timestamp: ISO timestamp of capture
                - file_size: Size of saved file in bytes
                - quality: Quality setting used for capture
                - analysis: Analysis results (only present if analyze=True)
                    - description: Text description of image content
                    - objects: List of detected objects
                    - people_count: Number of people detected
                    - confidence: Analysis confidence score
                - message: Success confirmation or error description

        Usage:
            Use this tool to capture high-quality images for monitoring, analysis, or archival
            purposes. The analysis feature provides AI-powered understanding of image content,
            making it valuable for security applications, automated monitoring, and intelligent
            surveillance systems.

            Common scenarios:
                - Security monitoring and incident documentation
                - Automated surveillance with AI analysis
                - Quality assurance and camera testing
                - Environmental monitoring and documentation
                - Batch capture from multiple cameras

        Examples:
            Basic image capture:
                result = await capture_still_tool.execute(camera_name='front_door')
                if result['success']:
                    logger.info(f"Image saved to: {result['image_path']}")
                # Returns: {
                #     'success': True,
                #     'camera_name': 'front_door',
                #     'image_path': '/tmp/camera_front_door_20241201_120000.jpg',
                #     'timestamp': '2024-12-01T12:00:00Z',
                #     'file_size': 245760,
                #     'quality': 85,
                #     'message': 'Image captured successfully'
                # }

            Capture with AI analysis:
                result = await capture_still_tool.execute(
                    camera_name='backyard',
                    analyze=True,
                    prompt='security'
                )
                # Returns: {
                #     'success': True,
                #     'camera_name': 'backyard',
                #     'image_path': '/tmp/camera_backyard_analyzed.jpg',
                #     'analysis': {
                #         'description': 'Outdoor backyard scene with clear weather',
                #         'objects': ['tree', 'fence', 'grass'],
                #         'people_count': 0,
                #         'confidence': 0.92
                #     },
                #     ...
                # }

            Batch capture from camera group:
                result = await capture_still_tool.execute(
                    camera_name='',  # Not used when group specified
                    group='exterior',
                    batch_size=2
                )
                # Captures from all cameras in 'exterior' group

            High-quality archival capture:
                result = await capture_still_tool.execute(
                    camera_name='entrance',
                    quality=95,
                    save_to_temp=False,
                    include_timestamp=True
                )
                # Saves high-quality image to permanent recordings directory

            Error handling - camera not found:
                result = await capture_still_tool.execute(camera_name='nonexistent')
                # Returns: {
                #     'success': False,
                #     'message': 'Camera not found: nonexistent'
                # }

            Error handling - camera offline:
                result = await capture_still_tool.execute(camera_name='disconnected_cam')
                # Returns: {
                #     'success': False,
                #     'message': 'Camera disconnected_cam is not connected'
                # }

        Raises:
            Exception: Propagated from camera operations (connection failures, hardware issues, file system errors)

        Notes:
            - Camera must be connected and operational for capture
            - Image capture may take several seconds depending on camera and network
            - Analysis adds processing time (2-5 seconds typically)
            - Temporary files are automatically cleaned up (configurable)
            - File paths are absolute and include timestamps when requested
            - Quality vs file size trade-off should be considered
            - Batch operations are processed in parallel for efficiency

        See Also:
            - get_stream_url_tool: For continuous video streaming
            - analyze_image_tool: For analysis of existing images
            - list_cameras_tool: To verify camera availability
        """
        try:
            from datetime import datetime

            from ...core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()
            return await server.capture_still(
                camera_name=self.camera_name,
                save_to_temp=self.save_to_temp,
                quality=self.quality,
                include_timestamp=self.include_timestamp,
                analyze=self.analyze,
                prompt=self.prompt,
                group=self.group,
                batch_size=self.batch_size,
                use_cache=self.use_cache,
            )
        except Exception as e:
            logger.exception("Error capturing still image(s):")
            return {
                "status": "error",
                "message": f"Failed to capture still image(s): {e!s}",
                "timestamp": datetime.now().isoformat(),
            }
