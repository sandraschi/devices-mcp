"""
Portmanteau Tools Module

Consolidates multiple related tools into single, action-based tools to reduce
the tool explosion problem and improve MCP client usability.

Production mode: Portmanteau tools only (cleaner UI)
Testing mode: Individual tools also available
"""

import logging

from fastmcp import FastMCP

from .ai_analysis import register_ai_analysis_tool
from .alerts_management import register_alerts_management_tool
from .analytics_management import register_analytics_management_tool
from .appliance_monitor_management import register_appliance_monitor_management_tool
from .audio_management import register_audio_management_tool
from .automation_management import register_automation_management_tool
from .camera_management import register_camera_management_tool
from .configuration_management import register_configuration_management_tool
from .energy_management import register_energy_management_tool
from .grafana_management import register_grafana_management_tool
from .home_assistant_management import register_home_assistant_management_tool
from .kitchen_management import register_kitchen_management_tool
from .lighting_management import register_lighting_management_tool
from .media_management import register_media_management_tool
from .medical_management import register_medical_management_tool
from .messages_management import register_messages_management_tool
from .motion_management import register_motion_management_tool
from .ptz_management import register_ptz_management_tool
from .ring_management import register_ring_management_tool
from .robotics_management import register_robotics_management_tool
from .security_management import register_security_management_tool
from .sensor_health import register_sensor_health_tool
from .shelly_management import register_shelly_management_tool
from .system_management import register_system_management_tool
from .tapo_control import register_tapo_control_tool
from .thermal_management import register_thermal_management_tool
from .weather_management import register_weather_management_tool

# Import agentic tools (SEP-1577)
try:
    from .. import agentic_security as _agentic_security_mod

    _agentic_security_available = hasattr(_agentic_security_mod, "agentic_security_workflow")
except ImportError:
    _agentic_security_available = False

logger = logging.getLogger(__name__)


def register_all_portmanteau_tools(mcp: FastMCP) -> None:
    """Register all portmanteau tools with the FastMCP server.

    Args:
        mcp: The FastMCP instance to register tools with
    """
    # Core portmanteau tools (always registered)
    register_tapo_control_tool(mcp)  # Unified "device_control" tool - register first for natural commands
    register_camera_management_tool(mcp)
    register_ptz_management_tool(mcp)
    register_media_management_tool(mcp)
    register_energy_management_tool(mcp)
    register_lighting_management_tool(mcp)
    register_kitchen_management_tool(mcp)
    register_security_management_tool(mcp)
    register_system_management_tool(mcp)
    register_weather_management_tool(mcp)
    register_sensor_health_tool(mcp)
    register_configuration_management_tool(mcp)

    # New tools (v1.5.0)
    register_ring_management_tool(mcp)  # Ring doorbell integration
    register_audio_management_tool(mcp)  # Audio streaming
    register_motion_management_tool(mcp)  # Motion detection
    register_home_assistant_management_tool(mcp)  # HA bridge for Nest Protect

    # New tools (v1.6.0)
    register_robotics_management_tool(mcp)  # Moorebot Scout robotics
    register_ai_analysis_tool(mcp)  # Scene analysis and AI
    register_automation_management_tool(mcp)  # Smart automation
    register_analytics_management_tool(mcp)  # Performance analytics
    register_grafana_management_tool(mcp)  # Grafana integration

    register_medical_management_tool(mcp)
    register_shelly_management_tool(mcp)
    register_thermal_management_tool(mcp)
    register_appliance_monitor_management_tool(mcp)
    register_alerts_management_tool(mcp)
    register_messages_management_tool(mcp)

    # Register agentic tools (SEP-1577) if available
    if _agentic_security_available:
        # The agentic_security_workflow tool is already registered via @mcp.tool decorator
        logger.info("Agentic security workflow tool registered (SEP-1577)")
    else:
        logger.warning("Agentic security workflow tool not available (missing advanced_memory dependency)")

    logger.info("All portmanteau tools registered successfully (20+ agentic tools)")


# Export the registration function
__all__ = ["register_all_portmanteau_tools"]
