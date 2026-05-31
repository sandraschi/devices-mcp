"""
Configuration Management Portmanteau Tool

Consolidates all configuration-related operations into a single tool with action-based interface.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

from devices_mcp.tools.configuration.device_settings_tool import DeviceSettingsTool
from devices_mcp.tools.configuration.privacy_settings_tool import PrivacySettingsTool

logger = logging.getLogger(__name__)

CONFIG_ACTIONS = {
    "device_settings": "Manage device settings",
    "privacy_settings": "Manage privacy settings",
    "led_control": "Control LED",
    "motion_detection": "Configure motion detection",
    "privacy_mode": "Configure privacy mode",
}


def register_configuration_management_tool(mcp: FastMCP) -> None:
    """Register the configuration management portmanteau tool."""

    @mcp.tool()
    async def configuration_management(
        action: Literal["device_settings", "privacy_settings", "led_control", "motion_detection", "privacy_mode"],
        camera_name: str | None = None,
        setting_name: str | None = None,
        setting_value: Any = None,
        enabled: bool | None = None,
    ) -> dict[str, Any]:
        """
        Comprehensive configuration management portmanteau tool.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 5+ separate tools (one per operation), this tool consolidates related
        configuration operations into a single interface. Prevents tool explosion (5+ tools → 1 tool) while maintaining
        full functionality and improving discoverability. Follows FastMCP 3.1+ best practices.

        Args:
            action (Literal, required): The operation to perform. Must be one of: "device_settings", "privacy_settings",
                "led_control", "motion_detection", "privacy_mode".
                - "device_settings": Manage device settings (requires: camera_name, setting_name, setting_value)
                - "privacy_settings": Manage privacy settings (requires: camera_name, enabled)
                - "led_control": Control LED (requires: camera_name, enabled)
                - "motion_detection": Configure motion detection (requires: camera_name, enabled)
                - "privacy_mode": Configure privacy mode (requires: camera_name, enabled)

            camera_name (str | None): Camera name/ID. Required for: all operations.

            setting_name (str | None): Setting name to configure. Required for: device_settings operation.
                Examples: "resolution", "fps", "night_vision"

            setting_value (Any): Setting value. Required for: device_settings operation.
                Type depends on setting_name (str, int, bool, etc.)

            enabled (bool | None): Enable/disable flag. Required for: privacy_settings, led_control,
                motion_detection, privacy_mode operations.

        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data (settings, status, etc.)
                - error (str | None): Error message if success is False

        Examples:
            # Configure device setting
            result = await configuration_management(action="device_settings", camera_name="Front Door", setting_name="resolution", setting_value="1920x1080")

            # Enable motion detection
            result = await configuration_management(action="motion_detection", camera_name="Front Door", enabled=True)

            # Control LED
            result = await configuration_management(action="led_control", camera_name="Front Door", enabled=False)

            # Enable privacy mode
            result = await configuration_management(action="privacy_mode", camera_name="Front Door", enabled=True)
        """
        try:
            if action not in CONFIG_ACTIONS:
                return {
                    "success": False,
                    "error": f"Invalid action '{action}'. Available: {list(CONFIG_ACTIONS.keys())}",
                }

            logger.info(f"Executing configuration management action: {action}")

            if action == "device_settings":
                # DeviceSettingsTool doesn't support generic device_settings operation
                # This would need a different tool or implementation
                return {
                    "success": False,
                    "error": "device_settings action requires a specific setting. Use led_control or motion_detection instead.",
                }

            if action in ["led_control", "motion_detection"]:
                if not camera_name:
                    return {"success": False, "error": "camera_name is required for this action"}

                tool = DeviceSettingsTool()
                operation_map = {
                    "led_control": "led",
                    "motion_detection": "motion_detection",
                }
                result = await tool.execute(
                    operation=operation_map[action],
                    camera_id=camera_name,
                    enabled=enabled,
                )
                return {"success": True, "action": action, "data": result}

            if action in ["privacy_settings", "privacy_mode"]:
                if not camera_name:
                    return {"success": False, "error": "camera_name is required for this action"}

                tool = PrivacySettingsTool()
                result = await tool.execute(
                    operation=action,
                    camera_id=camera_name,
                    enabled=enabled,
                )
                return {"success": True, "action": action, "data": result}

            return {"success": False, "error": f"Action '{action}' not implemented"}

        except Exception as e:
            logger.exception("Error in configuration management action '{action}':")
            return {"success": False, "error": f"Failed to execute action '{action}': {e!s}"}
