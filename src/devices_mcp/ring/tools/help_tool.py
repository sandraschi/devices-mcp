"""
Ring MCP Help System Tools - FastMCP 3.1

Comprehensive help and documentation system providing multilevel assistance:
- Tool discovery and listing
- Detailed tool help and usage examples
- Tool search and filtering
- System information and capabilities

This module uses FastMCP 3.1 patterns with multiline decorators and proper
tool registration for Claude Desktop stdio communication.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

logger = logging.getLogger(__name__)


def register_tools(app: FastMCP) -> None:
    """Register help system tools with the FastMCP application.

    Uses FastMCP 3.1 patterns with multiline decorators and proper
    stdio communication support for Claude Desktop integration.

    Args:
        app: FastMCP application instance
    """

    @app.tool(
        name="list_available_tools",
        description="List all available Ring MCP tools with categories and descriptions",
    )
    async def list_available_tools(
        category: Optional[str] = None, include_hidden: bool = False
    ) -> Dict[str, Any]:
        """List all available Ring MCP tools with categories and descriptions.

        Provides a comprehensive overview of all available tools, organized by category.
        Shows tool names, descriptions, parameters, and usage information.

        Args:
            category: Optional category filter (cameras, doorbells, security, fire, monitoring, automation)
            include_hidden: Include internal/system tools (default: False)

        Returns:
            Dict containing:
            - tools: List of available tools with metadata
            - categories: Available tool categories
            - total_count: Total number of tools
            - filtered_count: Number of tools in current filter
        """
        # Tool registry - comprehensive list of all Ring MCP tools
        all_tools = {
            # Camera Management Tools
            "cameras": [
                {
                    "name": "get_camera_status",
                    "description": "Get comprehensive status of all Ring security cameras",
                    "category": "cameras",
                    "parameters": {},
                    "example": "get_camera_status()",
                    "returns": "Camera status including online/offline, battery, recording",
                },
                {
                    "name": "stream_all_cameras",
                    "description": "Start live video streams from all cameras",
                    "category": "cameras",
                    "parameters": {},
                    "example": "stream_all_cameras()",
                    "returns": "Live stream URLs and status for all cameras",
                },
            ],
            # Doorbell Management Tools
            "doorbells": [
                {
                    "name": "get_doorbell_status",
                    "description": "Get comprehensive status of all Ring doorbells",
                    "category": "doorbells",
                    "parameters": {},
                    "example": "get_doorbell_status()",
                    "returns": "Doorbell connectivity, battery, and visitor detection status",
                },
                {
                    "name": "get_doorbell_live_stream",
                    "description": "Get live stream URL for a specific doorbell",
                    "category": "doorbells",
                    "parameters": {"doorbell_id": "string"},
                    "example": "get_doorbell_live_stream(doorbell_id='1234567890')",
                    "returns": "Live stream URL for the specified doorbell",
                },
                {
                    "name": "answer_doorbell_call",
                    "description": "Answer an active doorbell call",
                    "category": "doorbells",
                    "parameters": {"doorbell_id": "string"},
                    "example": "answer_doorbell_call(doorbell_id='1234567890')",
                    "returns": "Call handling status",
                },
                {
                    "name": "get_visitor_history",
                    "description": "Get visitor history and activity logs",
                    "category": "doorbells",
                    "parameters": {"hours": "int", "doorbell_id": "string"},
                    "example": "get_visitor_history(hours=24, doorbell_id='1234567890')",
                    "returns": "Recent visitor activity and motion events",
                },
                {
                    "name": "configure_motion_detection",
                    "description": "Configure motion detection settings for doorbells",
                    "category": "doorbells",
                    "parameters": {
                        "doorbell_id": "string",
                        "enabled": "bool",
                        "sensitivity": "int",
                    },
                    "example": "configure_motion_detection(doorbell_id='1234567890', enabled=True, sensitivity=80)",
                    "returns": "Motion detection configuration status",
                },
            ],
            # Security System Tools
            "security": [
                {
                    "name": "get_security_system_status",
                    "description": "Get comprehensive status of the entire Ring security system",
                    "category": "security",
                    "parameters": {},
                    "example": "get_security_system_status()",
                    "returns": "Overall security system status, modes, and device health",
                },
                {
                    "name": "arm_security_system",
                    "description": "Arm the security system in specified mode",
                    "category": "security",
                    "parameters": {"mode": "string", "devices": "list"},
                    "example": "arm_security_system(mode='home', devices=['front_door', 'back_door'])",
                    "returns": "Arming status and countdown information",
                },
                {
                    "name": "disarm_security_system",
                    "description": "Disarm the security system",
                    "category": "security",
                    "parameters": {"code": "string"},
                    "example": "disarm_security_system(code='1234')",
                    "returns": "Disarming status and system state",
                },
                {
                    "name": "get_security_history",
                    "description": "Get security system history and events",
                    "category": "security",
                    "parameters": {"hours": "int", "event_type": "string"},
                    "example": "get_security_history(hours=24, event_type='alarm')",
                    "returns": "Security events and system activity logs",
                },
            ],
            # Fire Safety Tools
            "fire": [
                {
                    "name": "get_fire_alarm_status",
                    "description": "Get comprehensive status of all Ring fire alarms and smoke detectors",
                    "category": "fire",
                    "parameters": {},
                    "example": "get_fire_alarm_status()",
                    "returns": "Fire alarm health, battery levels, and system status",
                },
                {
                    "name": "test_fire_safety_system",
                    "description": "Test fire safety system components",
                    "category": "fire",
                    "parameters": {"device_id": "string", "test_type": "string"},
                    "example": "test_fire_safety_system(device_id='smoke_detector_1', test_type='battery')",
                    "returns": "Test results and system health report",
                },
            ],
            # Monitoring Tools
            "monitoring": [
                {
                    "name": "monitor_system_health",
                    "description": "Perform comprehensive health check of entire Ring security system",
                    "category": "monitoring",
                    "parameters": {},
                    "example": "monitor_system_health()",
                    "returns": "System health score, device status, and maintenance alerts",
                },
                {
                    "name": "get_real_time_activity",
                    "description": "Get real-time activity and alerts from all devices",
                    "category": "monitoring",
                    "parameters": {"minutes": "int"},
                    "example": "get_real_time_activity(minutes=30)",
                    "returns": "Recent activity, motion events, and system alerts",
                },
            ],
            # Automation Tools
            "automation": [
                {
                    "name": "create_security_automation",
                    "description": "Create custom security automation rule with triggers and responses",
                    "category": "automation",
                    "parameters": {
                        "trigger_type": "string",
                        "trigger_conditions": "dict",
                        "response_actions": "list",
                        "automation_name": "string",
                    },
                    "example": "create_security_automation(trigger_type='motion', automation_name='Front Door Alert')",
                    "returns": "Automation rule creation status and ID",
                },
                {
                    "name": "trigger_emergency_protocol",
                    "description": "Trigger emergency response protocol",
                    "category": "automation",
                    "parameters": {"protocol_type": "string", "severity": "string"},
                    "example": "trigger_emergency_protocol(protocol_type='intruder', severity='high')",
                    "returns": "Emergency protocol activation status",
                },
                {
                    "name": "schedule_security_modes",
                    "description": "Schedule automatic security mode changes",
                    "category": "automation",
                    "parameters": {
                        "schedule_name": "string",
                        "time_rules": "list",
                        "mode_sequence": "list",
                    },
                    "example": "schedule_security_modes(schedule_name='Night Schedule')",
                    "returns": "Schedule creation status and validation",
                },
            ],
            # System Tools
            "system": [
                {
                    "name": "health_check",
                    "description": "Check the health of the Ring MCP service",
                    "category": "system",
                    "parameters": {},
                    "example": "health_check()",
                    "returns": "Service health status and diagnostic information",
                },
                {
                    "name": "get_system_status",
                    "description": "Get detailed system status including auth and device connectivity",
                    "category": "system",
                    "parameters": {},
                    "example": "get_system_status()",
                    "returns": "Authentication status, device connectivity, and system health",
                },
            ],
        }

        # Flatten tools list
        tools = []
        categories = set()

        for category_tools in all_tools.values():
            for tool in category_tools:
                tools.append(tool)
                categories.add(tool["category"])

        # Filter by category if specified
        if category:
            tools = [t for t in tools if t["category"] == category]

        # Filter out hidden tools unless requested
        if not include_hidden:
            tools = [t for t in tools if t["category"] != "internal"]

        return {
            "tools": tools,
            "categories": sorted(list(categories)),
            "total_count": len(tools),
            "filtered_count": len(tools),
            "timestamp": datetime.now().isoformat(),
        }

    @app.tool(
        name="get_tool_help",
        description="Get detailed help and usage information for a specific tool",
    )
    async def get_tool_help(tool_name: str, include_examples: bool = True) -> Dict[str, Any]:
        """Get detailed help and usage information for a specific tool.

        Provides comprehensive information about a specific tool including:
        - Detailed description and purpose
        - Parameter specifications and types
        - Usage examples and best practices
        - Return value descriptions
        - Related tools and use cases

        Args:
            tool_name: Name of the tool to get help for
            include_examples: Include usage examples (default: True)

        Returns:
            Dict containing detailed tool information and usage guidance
        """
        # Get all tools
        all_tools_response = await list_available_tools(include_hidden=True)
        all_tools = all_tools_response["tools"]

        # Find the specific tool
        tool = None
        for t in all_tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            return {
                "error": f"Tool '{tool_name}' not found",
                "available_tools": [t["name"] for t in all_tools],
                "suggestion": "Use 'list_available_tools()' to see all available tools",
            }

        # Enhanced help information
        help_info = {
            "tool_name": tool["name"],
            "description": tool["description"],
            "category": tool["category"],
            "parameters": tool["parameters"],
            "returns": tool["returns"],
            "usage": tool["example"],
        }

        if include_examples:
            help_info["examples"] = {
                "basic": tool["example"],
                "advanced": generate_advanced_example(tool),
                "error_handling": generate_error_handling_example(tool),
            }

            help_info["tips"] = generate_usage_tips(tool)
            help_info["related_tools"] = find_related_tools(tool, all_tools)

        return help_info

    @app.tool(
        name="search_tools", description="Search for tools by name, description, or functionality"
    )
    async def search_tools(
        query: str, category: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """Search for tools by name, description, or functionality.

        Intelligent search across all tools using fuzzy matching on:
        - Tool names and descriptions
        - Parameter names and types
        - Use cases and functionality
        - Categories and tags

        Args:
            query: Search query string
            category: Optional category filter
            limit: Maximum number of results to return (default: 10)

        Returns:
            Dict containing search results with relevance scoring
        """
        # Get all tools
        all_tools_response = await list_available_tools(include_hidden=True)
        all_tools = all_tools_response["tools"]

        # Search algorithm
        matches = []
        query_lower = query.lower()

        for tool in all_tools:
            relevance_score = 0

            # Exact name match - highest priority
            if query_lower == tool["name"].lower():
                relevance_score = 100
            # Partial name match
            elif query_lower in tool["name"].lower():
                relevance_score = 80
            # Description match
            elif query_lower in tool["description"].lower():
                relevance_score = 60
            # Category match
            elif category and tool["category"] == category.lower():
                relevance_score = 40
            # Parameter match
            elif any(query_lower in str(param).lower() for param in tool["parameters"].values()):
                relevance_score = 50
            # Use case match
            elif query_lower in tool["returns"].lower():
                relevance_score = 30

            if relevance_score > 0:
                tool["relevance_score"] = relevance_score
                tool["match_type"] = get_match_type(relevance_score)
                matches.append(tool)

        # Sort by relevance score
        matches.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Limit results
        matches = matches[:limit]

        return {
            "query": query,
            "category_filter": category,
            "total_matches": len(matches),
            "results": matches,
            "search_tips": [
                "Use exact tool names for best results",
                "Try partial names or keywords",
                "Specify category for focused results",
                "Check parameter names and descriptions",
            ],
        }


def generate_advanced_example(tool: Dict[str, Any]) -> str:
    """Generate advanced usage examples for a tool."""
    examples = {
        "get_camera_status": "get_camera_status()  # Get all cameras with detailed status",
        "get_doorbell_status": "get_doorbell_status()  # Monitor visitor detection and battery",
        "monitor_system_health": "monitor_system_health()  # Comprehensive system check",
        "get_security_system_status": "get_security_system_status()  # Check security mode and devices",
    }
    return examples.get(tool["name"], f"{tool['name']}()  # Advanced usage with error handling")


def generate_error_handling_example(tool: Dict[str, Any]) -> str:
    """Generate error handling examples for a tool."""
    return f"""try:
    result = await {tool["name"]}()
    print(f"Success: {{result}}")
except ValueError as e:
    print(f"Authentication/parameter error: {{e}}")
except Exception as e:
    print(f"Unexpected error: {{e}}")
    # Tools are designed to handle errors gracefully"""


def generate_usage_tips(tool: Dict[str, Any]) -> List[str]:
    """Generate usage tips for a tool."""
    tips = []

    if "camera" in tool["name"]:
        tips.extend(
            [
                "Check camera status before streaming",
                "Monitor battery levels regularly",
                "Test motion detection in different lighting",
            ]
        )
    elif "doorbell" in tool["name"]:
        tips.extend(
            [
                "Configure motion zones for better detection",
                "Check visitor history regularly",
                "Test call answering functionality",
            ]
        )
    elif "security" in tool["name"]:
        tips.extend(
            [
                "Set up entry/exit delays appropriately",
                "Test alarm system regularly",
                "Monitor device connectivity status",
            ]
        )
    elif "fire" in tool["name"]:
        tips.extend(
            [
                "Test smoke detectors monthly",
                "Replace batteries annually",
                "Clean sensors regularly",
            ]
        )
    else:
        tips.append("Check tool help for detailed usage instructions")

    return tips


def find_related_tools(tool: Dict[str, Any], all_tools: List[Dict[str, Any]]) -> List[str]:
    """Find tools related to the current tool."""
    related = []
    current_category = tool["category"]

    # Find tools in same category
    for t in all_tools:
        if t["category"] == current_category and t["name"] != tool["name"]:
            related.append(t["name"])

    return related[:5]  # Limit to 5 related tools


def get_match_type(score: int) -> str:
    """Get human-readable match type based on relevance score."""
    if score >= 80:
        return "exact_match"
    if score >= 60:
        return "partial_match"
    if score >= 40:
        return "category_match"
    return "related_match"
