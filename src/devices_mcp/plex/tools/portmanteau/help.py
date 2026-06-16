"""
PlexMCP Help & Discovery Portmanteau Tool

Provides help, tool discovery, and usage examples for PlexMCP.
FastMCP 2.13+ compliant with comprehensive docstrings and AI-friendly error messages.
"""

from typing import Any, Literal

from ...app import mcp
from ...utils import get_logger

logger = get_logger(__name__)


@mcp.tool()
async def plex_help(
    operation: Literal["help", "list_tools", "tool_info", "examples"],
    tool_name: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    """Comprehensive help and discovery tool for PlexMCP.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 4 separate tools (one per help operation), this tool consolidates related
    help and discovery operations into a single interface. This design:
    - Prevents tool explosion (4 tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with help tasks
    - Enables consistent help interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - help: Get general help and overview of PlexMCP
    - list_tools: List all available tools with brief descriptions
    - tool_info: Get detailed information about a specific tool
    - examples: Get usage examples for tools

    OPERATIONS DETAIL:

    help: General help
    - Parameters: category (optional, filter by category)
    - Returns: General help information and overview
    - Use when: Getting started or understanding PlexMCP capabilities

    list_tools: List all tools
    - Parameters: category (optional, filter by category)
    - Returns: List of all available tools with brief descriptions
    - Use when: Discovering available tools

    tool_info: Get tool details
    - Parameters: tool_name (required)
    - Returns: Detailed tool information including parameters and examples
    - Use when: Understanding how to use a specific tool

    examples: Get usage examples
    - Parameters: tool_name (optional, if omitted returns examples for all tools)
    - Returns: Usage examples for tools
    - Use when: Learning how to use tools through examples

    Prerequisites:
    - None (this tool provides help and discovery, no Plex server connection required)

    Args:
        operation (str): The help operation to perform. Required. Must be one of: "help", "list_tools", "tool_info", "examples"
        tool_name (str | None): Name of the tool to get information about (required for tool_info, optional for examples).
        category (str | None): Optional category filter (library, media, user, playlist, etc.).

    Returns:
        Operation-specific result with help information

    Examples:
        # Get general help
        plex_help("help")

        # List all tools
        plex_help("list_tools")

        # Get tool information
        plex_help("tool_info", tool_name="plex_library")

        # Get examples for a tool
        plex_help("examples", tool_name="plex_media")

    Errors:
        Common errors and solutions:
        - "tool_name required": Provide tool name for tool_info operation
        - "Tool not found": Verify tool_name is correct
    """
    try:
        # Define available tools and their categories
        tools_info = {
            "plex_library": {
                "name": "plex_library",
                "category": "library",
                "description": "Library management operations (list, get, create, update, delete, scan, refresh, optimize, etc.)",
                "operations": [
                    "list",
                    "get",
                    "create",
                    "update",
                    "delete",
                    "scan",
                    "refresh",
                    "optimize",
                    "empty_trash",
                    "add_location",
                    "remove_location",
                    "clean_bundles",
                ],
            },
            "plex_media": {
                "name": "plex_media",
                "category": "media",
                "description": "Media operations (browse, search, get_details, get_recent, update_metadata)",
                "operations": [
                    "browse",
                    "search",
                    "get_details",
                    "get_recent",
                    "update_metadata",
                ],
            },
            "plex_user": {
                "name": "plex_user",
                "category": "user",
                "description": "User management operations (list, get, create, update, delete, update_permissions)",
                "operations": [
                    "list",
                    "get",
                    "create",
                    "update",
                    "delete",
                    "update_permissions",
                ],
            },
            "plex_playlist": {
                "name": "plex_playlist",
                "category": "playlist",
                "description": "Playlist management operations (list, get, create, update, delete, add_items, remove_items, get_analytics)",
                "operations": [
                    "list",
                    "get",
                    "create",
                    "update",
                    "delete",
                    "add_items",
                    "remove_items",
                    "get_analytics",
                ],
            },
            "plex_streaming": {
                "name": "plex_streaming",
                "category": "streaming",
                "description": "Playback control operations (list_sessions, list_clients, play, pause, stop, seek, skip_next, skip_previous, control)",
                "operations": [
                    "list_sessions",
                    "list_clients",
                    "play",
                    "pause",
                    "stop",
                    "seek",
                    "skip_next",
                    "skip_previous",
                    "control",
                ],
            },
            "plex_metadata": {
                "name": "plex_metadata",
                "category": "metadata",
                "description": "Metadata management operations (refresh, refresh_all, fix_match, update, analyze, match, organize)",
                "operations": [
                    "refresh",
                    "refresh_all",
                    "fix_match",
                    "update",
                    "analyze",
                    "match",
                    "organize",
                ],
            },
            "plex_performance": {
                "name": "plex_performance",
                "category": "performance",
                "description": "Performance and quality operations (transcode settings, bandwidth, throttling, quality profiles, server status)",
                "operations": [
                    "get_transcode_settings",
                    "update_transcode_settings",
                    "get_transcoding_status",
                    "get_bandwidth",
                    "set_quality",
                    "get_throttling",
                    "set_throttling",
                    "list_profiles",
                    "create_profile",
                    "delete_profile",
                    "get_server_status",
                    "get_server_info",
                    "get_health",
                ],
            },
            "plex_organization": {
                "name": "plex_organization",
                "category": "organization",
                "description": "Library organization operations (organize, analyze, clean_bundles, optimize_database, fix_issues)",
                "operations": [
                    "organize",
                    "analyze",
                    "clean_bundles",
                    "optimize_database",
                    "fix_issues",
                ],
            },
            "plex_server": {
                "name": "plex_server",
                "category": "server",
                "description": "Server management operations (status, info, health, maintenance, restart, update)",
                "operations": [
                    "status",
                    "info",
                    "health",
                    "maintenance",
                    "restart",
                    "update",
                ],
            },
            "plex_integration": {
                "name": "plex_integration",
                "category": "integration",
                "description": "Third-party integration operations (list_integrations, vienna_recommendations, european_content, anime_season_info, configure, sync)",
                "operations": [
                    "list_integrations",
                    "vienna_recommendations",
                    "european_content",
                    "anime_season_info",
                    "configure",
                    "sync",
                ],
            },
            "plex_search": {
                "name": "plex_search",
                "category": "search",
                "description": "Advanced search operations (search, advanced_search, suggest, recent_searches, save_search)",
                "operations": [
                    "search",
                    "advanced_search",
                    "suggest",
                    "recent_searches",
                    "save_search",
                ],
            },
            "plex_reporting": {
                "name": "plex_reporting",
                "category": "reporting",
                "description": "Reporting and analytics operations (library_stats, usage_report, content_report, user_activity, performance_report, export_report)",
                "operations": [
                    "library_stats",
                    "usage_report",
                    "content_report",
                    "user_activity",
                    "performance_report",
                    "export_report",
                ],
            },
            "plex_collections": {
                "name": "plex_collections",
                "category": "collections",
                "description": "Collection management operations (list, get, create, update, delete, add_items, remove_items)",
                "operations": [
                    "list",
                    "get",
                    "create",
                    "update",
                    "delete",
                    "add_items",
                    "remove_items",
                ],
            },
            "plex_quality": {
                "name": "plex_quality",
                "category": "quality",
                "description": "Quality profile management operations (list_profiles, get_profile, create_profile, update_profile, delete_profile, set_default)",
                "operations": [
                    "list_profiles",
                    "get_profile",
                    "create_profile",
                    "update_profile",
                    "delete_profile",
                    "set_default",
                ],
            },
        }

        if operation == "help":
            help_text = """
PlexMCP - Plex Media Server MCP Tools

PlexMCP provides comprehensive tools for managing Plex Media Server through the Model Context Protocol (MCP).

Available Tool Categories:
- library: Library management (plex_library)
- media: Media operations (plex_media)
- user: User management (plex_user)
- playlist: Playlist management (plex_playlist)
- streaming: Playback control (plex_streaming)
- metadata: Metadata management (plex_metadata)
- performance: Performance and quality (plex_performance)
- organization: Library organization (plex_organization)
- server: Server management (plex_server)
- integration: Third-party integrations (plex_integration)
- search: Advanced search (plex_search)
- reporting: Reporting and analytics (plex_reporting)
- collections: Collection management (plex_collections)
- quality: Quality profiles (plex_quality)

Use list_tools to see all available tools, or tool_info to get details about a specific tool.
"""
            if category:
                filtered_tools = {k: v for k, v in tools_info.items() if v["category"] == category}
                help_text += f"\nTools in category '{category}':\n"
                for tool in filtered_tools.values():
                    help_text += f"  - {tool['name']}: {tool['description']}\n"

            return {
                "success": True,
                "operation": "help",
                "help": help_text,
                "category": category,
            }

        if operation == "list_tools":
            tools_list = list(tools_info.values())
            if category:
                tools_list = [t for t in tools_list if t["category"] == category]

            return {
                "success": True,
                "operation": "list_tools",
                "tools": tools_list,
                "count": len(tools_list),
                "category": category,
            }

        if operation == "tool_info":
            if not tool_name:
                return {
                    "success": False,
                    "message": "tool_name is required for tool_info operation",
                    "error": "tool_name is required for tool_info operation",
                    "error_code": "MISSING_PARAMETER",
                    "suggestions": ["Provide a tool name"],
                }

            if tool_name not in tools_info:
                return {
                    "success": False,
                    "message": f"Tool '{tool_name}' not found",
                    "error_code": "TOOL_NOT_FOUND",
                    "suggestions": ["Use list_tools to see available tools"],
                }

            tool = tools_info[tool_name]
            return {
                "success": True,
                "operation": "tool_info",
                "tool": tool,
                "usage": f"Use {tool_name} with operation parameter set to one of: {', '.join(tool['operations'])}",
            }

        if operation == "examples":
            examples = {}
            if tool_name:
                if tool_name not in tools_info:
                    return {
                        "success": False,
                        "message": f"Tool '{tool_name}' not found",
                        "error_code": "TOOL_NOT_FOUND",
                    }
                tools_to_show = [tools_info[tool_name]]
            else:
                tools_to_show = list(tools_info.values())

            for tool in tools_to_show:
                examples[tool["name"]] = {
                    "description": tool["description"],
                    "example_operations": tool["operations"][:3],  # Show first 3 operations as examples
                }

            return {
                "success": True,
                "operation": "examples",
                "examples": examples,
                "tool_name": tool_name,
            }

        return {
            "success": False,
            "message": f"Unknown operation: {operation}",
            "error_code": "INVALID_OPERATION",
            "suggestions": ["Use one of: help, list_tools, tool_info, examples"],
        }

    except Exception as e:
        logger.exception("Error in plex_help operation '{operation}':")
        return {
            "success": False,
            "message": str(e),
            "error": str(e),
            "error_code": "EXECUTION_ERROR",
            "suggestions": ["This is a help tool and should not normally fail"],
        }
