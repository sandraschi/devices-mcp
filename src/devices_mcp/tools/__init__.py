"""
Devices MCP Tools Package

This package contains all the tools for the Devices MCP server,
organized into logical modules for better maintainability.
"""

import logging
import os
import pkgutil

# Import standard library modules
from importlib import import_module

# Import types first to avoid circular imports
from typing import List, Optional, Type

# Import base tool components
from devices_mcp.tools.base_tool import (
    BaseTool,
    ToolCategory,
    ToolDefinition,
    ToolResult,
    _tool_registry,
    register_tool,
)
from devices_mcp.tools.base_tool import get_all_tools as _get_all_tools
from devices_mcp.tools.base_tool import get_tool as _get_tool

# Import discovery functions
from devices_mcp.tools.discovery import discover_tools

# Set up logging
logger = logging.getLogger(__name__)

# Re-export functions from base_tool
get_tool = _get_tool
get_all_tools = _get_all_tools


def discover_tools_wrapper(package: str | None = None) -> list[type[BaseTool]]:
    """Discover and import all tools in the specified package.

    Args:
        package: The package to search for tools (default: current package)

    Returns:
        List of discovered tool classes
    """
    if package is None:
        package = __name__

    # Get the directory containing the tools
    package_path = os.path.dirname(os.path.abspath(__file__))

    # Determine subpackage directory names to avoid importing same-named .py modules
    subpackage_dirs = {name for name in os.listdir(package_path) if os.path.isdir(os.path.join(package_path, name))}

    # Import all modules in the tools directory
    for finder, module_name, is_pkg in pkgutil.iter_modules([package_path]):
        # Skip the base module and private modules
        if module_name == "base_tool" or module_name.startswith("_"):
            continue

        # If there exists a subpackage with the same name, skip importing the .py module to avoid conflicts
        if not is_pkg and module_name in subpackage_dirs:
            continue

        full_module_name = f"{package}.{module_name}"
        try:
            # Use finder.find_spec to properly handle package imports
            spec = finder.find_spec(module_name)
            if spec is not None:
                import_module(full_module_name)
                if is_pkg:
                    # Recursively discover tools in subpackages
                    subpackage_path = os.path.join(package_path, module_name)
                    discover_tools_in_path(subpackage_path, full_module_name)
        except ImportError:
            logger.exception("Failed to import tool module")

    return _get_all_tools()


def discover_tools_in_path(package_path: str, package_name: str) -> None:
    """Discover tools in a specific package path.

    Args:
        package_path: The directory path to search
        package_name: The full package name for imports
    """
    # Import all modules in the subpackage directory
    for finder, module_name, is_pkg in pkgutil.iter_modules([package_path]):
        # Skip private modules
        if module_name.startswith("_"):
            continue

        full_module_name = f"{package_name}.{module_name}"
        try:
            # Use finder.find_spec to properly handle package imports
            spec = finder.find_spec(module_name)
            if spec is not None:
                import_module(full_module_name)
                if is_pkg:
                    # Recursively discover tools in deeper subpackages
                    subpackage_path = os.path.join(package_path, module_name)
                    discover_tools_in_path(subpackage_path, full_module_name)
        except ImportError:
            logger.exception("Failed to import tool module")


# Re-export functions from base_tool
get_tool = _get_tool
get_all_tools = _get_all_tools

# Global flag to prevent multiple calls
_tools_registered = False


# Import consolidated portmanteau tools only (FastMCP 3.1 compliant)
def import_consolidated_tools():
    """Import only consolidated portmanteau tools following FastMCP 3.1 standards.

    This replaces the old discovery system to ensure only our 16 consolidated
    portmanteau tools are registered, avoiding the 64+ individual tools.
    """
    global _tools_registered

    try:
        # Check if we already have consolidated tools registered
        if len(_tool_registry) >= 16:
            return

        # Clear any existing tool registry first
        _tool_registry.clear()

        # Import consolidated tools
        from .alarms.nest_protect_tool import NestProtectTool
        from .alarms.security_analysis_tool import SecurityAnalysisTool
        from .camera.camera_connection_tool import CameraConnectionTool
        from .camera.camera_info_tool import CameraInfoTool
        from .camera.camera_management_tool import CameraManagementTool
        from .configuration.device_settings_tool import DeviceSettingsTool
        from .configuration.privacy_settings_tool import PrivacySettingsTool
        from .energy.energy_management_tool import EnergyManagementTool
        from .media.image_capture_tool import ImageCaptureTool
        from .media.video_recording_tool import VideoRecordingTool
        from .ptz.ptz_control_tool import PTZControlTool
        from .ptz.ptz_preset_tool import PTZPresetTool
        from .system.system_control_tool import SystemControlTool
        from .system.system_info_tool import SystemInfoTool
        from .weather.netatmo_analysis_tool import NetatmoAnalysisTool
        from .weather.netatmo_weather_tool import NetatmoWeatherTool

        # Manually register all consolidated tools (FastMCP 3.1 compliant)
        consolidated_tools = [
            PTZControlTool,
            PTZPresetTool,
            CameraManagementTool,
            CameraConnectionTool,
            CameraInfoTool,
            EnergyManagementTool,
            NetatmoWeatherTool,
            NetatmoAnalysisTool,
            NestProtectTool,
            SecurityAnalysisTool,
            ImageCaptureTool,
            VideoRecordingTool,
            SystemInfoTool,
            SystemControlTool,
            DeviceSettingsTool,
            PrivacySettingsTool,
        ]

        # Register each tool manually
        from .base_tool import register_tool

        for tool_cls in consolidated_tools:
            try:
                register_tool(tool_cls)
            except Exception:
                logger.exception("Failed to register")

        _tools_registered = True
        logger.info("[OK] All 16 consolidated portmanteau tools registered (FastMCP 3.1 compliant)")
        logger.info("[SUCCESS] Tool consolidation successful: 64 -> 16 tools (75% reduction)")

    except ImportError:
        logger.exception("Failed to import consolidated tools")
        # Fallback to old discovery method if needed
        logger.warning("Falling back to old discovery method...")
        discover_tools()


# Import only consolidated tools (skip old discovery)
import_consolidated_tools()

__all__ = [
    "BaseTool",
    "ToolCategory",
    "ToolDefinition",
    "ToolResult",
    "_tool_registry",
    "discover_tools",
    "get_all_tools",
    "get_tool",
    "register_tool",
]
