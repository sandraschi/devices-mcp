"""
System tools for Devices MCP.

This module contains tools for system-level operations and configuration.
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import Field

from devices_mcp.tools.base_tool import BaseTool, ToolCategory, register_tool

logger = logging.getLogger(__name__)

__all__ = [
    "GetHelpTool",
    "GetLogsTool",
    "GetSystemInfoTool",
    "HelpTool",
    "RebootCameraTool",
    "SetLEDEnabledTool",
    "SetMotionDetectionTool",
    "SetPrivacyModeTool",
]


class GetSystemInfoTool(BaseTool):
    """Tool to get system information and status."""

    class Meta:
        name = "get_system_info"
        description = "Get system information and status"
        category = ToolCategory.SYSTEM

        class Parameters:
            pass

    async def execute(self) -> Dict[str, Any]:
        """Get system information and status."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        return await server.get_system_info()


# Register the tool
GetSystemInfoTool = register_tool(GetSystemInfoTool)


class RebootCameraTool(BaseTool):
    """Tool to reboot the camera."""

    class Meta:
        name = "reboot_camera"
        description = "Reboot the camera"
        category = ToolCategory.SYSTEM

        class Parameters:
            pass

    async def execute(self) -> Dict[str, Any]:
        """Reboot the camera."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        return await server.reboot_camera()


# Register the tool
RebootCameraTool = register_tool(RebootCameraTool)


class GetLogsTool(BaseTool):
    """Tool to get system logs."""

    class Meta:
        name = "get_logs"
        description = "Get system logs"
        category = ToolCategory.SYSTEM

        class Parameters:
            level: str = Field(
                default="info",
                description="Log level to retrieve",
                json_schema_extra={"enum": ["debug", "info", "warning", "error", "critical"]},
            )
            limit: int = Field(
                default=100, ge=1, description="Maximum number of log entries to return"
            )

    level: str = "info"
    limit: int = 100

    async def execute(self) -> Dict[str, Any]:
        """Get system logs."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        return await server.get_logs(level=self.level, limit=self.limit)


# Register the tool
GetLogsTool = register_tool(GetLogsTool)


class GetHelpTool(BaseTool):
    """Tool to get help about available tools and their usage."""

    class Meta:
        name = "get_help"
        description = "Get help about available tools and their usage"
        category = ToolCategory.UTILITY

        class Parameters:
            tool_name: Optional[str] = Field(None, description="Name of the tool to get help for")

    tool_name: Optional[str] = None

    async def execute(self) -> Dict[str, Any]:
        """Get help about available tools and their usage."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        return await server.get_help(tool_name=self.tool_name)


# Register the tool
GetHelpTool = register_tool(GetHelpTool)


class SetMotionDetectionTool(BaseTool):
    """Tool to control motion detection settings."""

    class Meta:
        name = "set_motion_detection"
        description = "Control motion detection settings"
        category = ToolCategory.CONFIGURATION

        class Parameters:
            enabled: bool = Field(..., description="Whether to enable motion detection")
            sensitivity: Optional[int] = Field(
                None, ge=1, le=100, description="Sensitivity level (1-100)"
            )
            zones: Optional[List[Any]] = Field(None, description="List of motion detection zones")

    enabled: bool
    sensitivity: Optional[int] = None
    zones: Optional[List[Any]] = None

    async def execute(self) -> Dict[str, Any]:
        """Enable or disable motion detection."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        return await server.set_motion_detection(
            enabled=self.enabled, sensitivity=self.sensitivity, zones=self.zones
        )


# Register the tool
SetMotionDetectionTool = register_tool(SetMotionDetectionTool)


class SetLEDEnabledTool(BaseTool):
    """Tool to control the camera LED."""

    class Meta:
        name = "set_led_enabled"
        description = "Control the camera LED"
        category = ToolCategory.CONFIGURATION

        class Parameters:
            enabled: bool = Field(..., description="Whether to enable the LED")

    enabled: bool

    async def execute(self) -> Dict[str, Any]:
        """Enable or disable the camera LED."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        return await server.set_led_enabled(enabled=self.enabled)


# Register the tool
SetLEDEnabledTool = register_tool(SetLEDEnabledTool)


class SetPrivacyModeTool(BaseTool):
    """Tool to control privacy mode."""

    class Meta:
        name = "set_privacy_mode"
        description = "Control privacy mode"
        category = ToolCategory.CONFIGURATION

        class Parameters:
            enabled: bool = Field(..., description="Whether to enable privacy mode")

    enabled: bool

    async def execute(self) -> Dict[str, Any]:
        """Enable or disable privacy mode."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        return await server.set_privacy_mode(enabled=self.enabled)


# Register the tool
SetPrivacyModeTool = register_tool(SetPrivacyModeTool)


class HelpTool(BaseTool):
    """Tool to get comprehensive help about available tools and their usage."""

    class Meta:
        name = "help"
        description = "Get comprehensive help about available tools and their usage"
        category = ToolCategory.UTILITY

        class Parameters:
            tool_name: Optional[str] = Field(None, description="Name of the tool to get help for")
            category: Optional[str] = Field(None, description="Filter tools by category")

    tool_name: Optional[str] = None
    category: Optional[str] = None

    async def execute(self) -> Dict[str, Any]:
        """Get comprehensive help about available tools and their usage."""
        from ...core.server import TapoCameraServer

        server = await TapoCameraServer.get_instance()
        return await server.get_help(tool_name=self.tool_name, category=self.category)


# Register the tool
HelpTool = register_tool(HelpTool)
