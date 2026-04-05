"""
Device Settings Portmanteau Tool

Combines device settings operations:
- Set LED enabled
- Set motion detection
"""

import logging
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


@tool("device_settings")
class DeviceSettingsTool(BaseTool):
    """Device settings management tool.

    Provides unified device settings operations including LED control
    and motion detection configuration.

    Parameters:
        operation: Type of settings operation (led, motion_detection).
        camera_id: Camera ID for settings operations.
        enabled: Whether to enable the setting (true/false).
        motion_sensitivity: Motion detection sensitivity (1-5) for motion_detection operation.
        motion_areas: Motion detection areas for motion_detection operation.

    Returns:
        A dictionary containing the device settings result.
    """

    class Meta:
        name = "device_settings"
        description = (
            "Unified device settings management including LED control and motion detection"
        )
        category = ToolCategory.CONFIGURATION

        class Parameters(BaseModel):
            operation: str = Field(..., description="Settings operation: 'led', 'motion_detection'")
            camera_id: str = Field(..., description="Camera ID for settings operations")
            enabled: Optional[bool] = Field(None, description="Whether to enable the setting")
            motion_sensitivity: Optional[int] = Field(3, description="Motion sensitivity (1-5)")
            motion_areas: Optional[List[Dict[str, int]]] = Field(
                None, description="Motion detection areas"
            )

    async def execute(
        self,
        operation: str,
        camera_id: str,
        enabled: Optional[bool] = None,
        motion_sensitivity: int = 3,
        motion_areas: Optional[List[Dict[str, int]]] = None,
    ) -> Dict[str, Any]:
        """Execute device settings operation."""
        try:
            logger.info(f"Device settings {operation} operation for camera {camera_id}")

            if operation == "led":
                return await self._set_led(camera_id, enabled)
            if operation == "motion_detection":
                return await self._set_motion_detection(
                    camera_id, enabled, motion_sensitivity, motion_areas
                )
            return {
                "success": False,
                "error": f"Invalid operation: {operation}. Must be 'led' or 'motion_detection'",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception(f"Device settings {operation} operation failed")
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "camera_id": camera_id,
                "timestamp": time.time(),
            }

    async def _set_led(self, camera_id: str, enabled: Optional[bool]) -> Dict[str, Any]:
        """Set LED status."""
        if enabled is None:
            return {
                "success": False,
                "error": "Enabled parameter is required for LED operation",
                "timestamp": time.time(),
            }

        # Simulate LED setting
        led_status = {
            "camera_id": camera_id,
            "led_enabled": enabled,
            "led_mode": "auto" if enabled else "off",
            "brightness": 100 if enabled else 0,
            "color": "blue" if enabled else "off",
            "blink_pattern": "solid" if enabled else "none",
        }

        return {
            "success": True,
            "operation": "led",
            "led_status": led_status,
            "message": f"Camera {camera_id} LED {'enabled' if enabled else 'disabled'}",
            "timestamp": time.time(),
        }

    async def _set_motion_detection(
        self,
        camera_id: str,
        enabled: Optional[bool],
        motion_sensitivity: int,
        motion_areas: Optional[List[Dict[str, int]]],
    ) -> Dict[str, Any]:
        """Set motion detection settings."""
        if enabled is None:
            return {
                "success": False,
                "error": "Enabled parameter is required for motion_detection operation",
                "timestamp": time.time(),
            }

        # Validate sensitivity
        if motion_sensitivity < 1 or motion_sensitivity > 5:
            return {
                "success": False,
                "error": "Motion sensitivity must be between 1 and 5",
                "timestamp": time.time(),
            }

        # Set default motion areas if not provided
        if motion_areas is None:
            motion_areas = [
                {"x": 0, "y": 0, "width": 100, "height": 100}  # Full frame
            ]

        # Simulate motion detection settings
        motion_config = {
            "camera_id": camera_id,
            "motion_detection_enabled": enabled,
            "sensitivity": motion_sensitivity,
            "detection_areas": motion_areas,
            "min_object_size": motion_sensitivity * 10,  # pixels
            "detection_threshold": motion_sensitivity * 20,
            "cooldown_period": 30,  # seconds
            "recording_duration": 60,  # seconds
            "email_alerts": enabled,
            "push_notifications": enabled,
            "ai_detection": enabled and motion_sensitivity >= 3,
        }

        return {
            "success": True,
            "operation": "motion_detection",
            "motion_config": motion_config,
            "message": f"Motion detection {'enabled' if enabled else 'disabled'} for camera {camera_id} (sensitivity: {motion_sensitivity})",
            "timestamp": time.time(),
        }
