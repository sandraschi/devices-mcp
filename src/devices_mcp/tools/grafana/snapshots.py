"""Grafana live camera snapshot tool - MANDATORY FOR VIDEO/IMAGES."""

import base64
from datetime import datetime
from typing import Any, Dict

from ..base_tool import BaseTool, ToolCategory


class GrafanaSnapshotsTool(BaseTool):
    """Tool for capturing live camera snapshots for Grafana image panels."""

    class Meta:
        name: str = "get_camera_snapshot"
        description: str = (
            "Capture live camera snapshot for Grafana image panels - MANDATORY FOR VIDEO/IMAGES"
        )
        category: ToolCategory = ToolCategory.UTILITY

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Capture a snapshot from the specified camera."""
        try:
            camera_id = kwargs.get("camera_id")
            quality = kwargs.get("quality", "medium")
            width = kwargs.get("width")
            height = kwargs.get("height")

            if not camera_id:
                raise ValueError("camera_id is required")

            # Get camera instance
            camera = self.get_camera_manager().get_camera(camera_id)
            if not camera:
                raise ValueError(f"Camera {camera_id} not found")

            # Capture snapshot
            image_data = await camera.get_snapshot(quality=quality, width=width, height=height)

            # Convert to base64 for web display
            image_base64 = base64.b64encode(image_data).decode("utf-8")

            return {
                "success": True,
                "data": {
                    "image": f"data:image/jpeg;base64,{image_base64}",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "camera_id": camera_id,
                    "format": "jpeg",
                },
                "content_type": "application/json",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to capture snapshot: {e!s}",
                "content_type": "application/json",
            }
