"""
PlexMCP Performance & Quality Management Portmanteau Tool

Consolidates all performance, quality, transcoding, and server status operations into a single comprehensive interface.
FastMCP 2.13+ compliant with comprehensive docstrings and AI-friendly error messages.
"""

import os
from typing import Any, Literal

from ...app import mcp
from ...utils import get_logger

logger = get_logger(__name__)


def _get_plex_service():
    """Get PlexService instance with proper environment variable handling."""
    from ...services.plex_service import PlexService

    base_url = os.getenv("PLEX_URL") or os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    token = os.getenv("PLEX_TOKEN")

    if not token:
        raise RuntimeError(
            "PLEX_TOKEN environment variable is required. "
            "Get your token from Plex Web App (Settings → Account → Authorized Devices) "
            "or visit https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/ "
            "for detailed instructions."
        )

    return PlexService(base_url=base_url, token=token)


@mcp.tool()
async def plex_performance(
    operation: Literal[
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
    ],
    profile_name: str | None = None,
    settings: dict[str, Any] | None = None,
    quality: str | None = None,
    bitrate: int | None = None,
    enabled: bool | None = None,
    download_limit: int | None = None,
    upload_limit: int | None = None,
    time_range: str = "day",
    is_default: bool = False,
) -> dict[str, Any]:
    """Comprehensive performance, quality, and server status operations for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 12+ separate tools (one per operation), this tool consolidates related
    performance, quality, transcoding, and server status operations into a single interface. This design:
    - Prevents tool explosion (12+ tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with performance management tasks
    - Enables consistent performance interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - get_transcode_settings: Get current transcode settings for a quality profile
    - update_transcode_settings: Update transcode settings for a quality profile
    - get_transcoding_status: Get current transcoding status
    - get_bandwidth: Get bandwidth usage statistics
    - set_quality: Set streaming quality settings for a profile
    - get_throttling: Get current throttling status and settings
    - set_throttling: Configure throttling settings
    - list_profiles: List all available quality profiles
    - create_profile: Create a new quality profile
    - delete_profile: Delete a quality profile
    - get_server_status: Get current server status
    - get_server_info: Get comprehensive server information

    OPERATIONS DETAIL:

    get_transcode_settings: Get current transcode settings
    - Parameters: profile_name (optional)
    - Returns: Dictionary with transcode settings
    - Example: plex_performance(operation="get_transcode_settings", profile_name="default")
    - Use when: Checking current transcoding configuration

    update_transcode_settings: Update transcode settings
    - Parameters: profile_name (required), settings (required)
    - Returns: Success confirmation
    - Example: plex_performance(operation="update_transcode_settings", profile_name="default", settings={"quality": "1080p"})
    - Use when: Modifying transcoding configuration

    get_transcoding_status: Get current transcoding status
    - Parameters: None required
    - Returns: Current transcoding status information
    - Example: plex_performance(operation="get_transcoding_status")
    - Use when: Monitoring active transcoding operations

    get_bandwidth: Get bandwidth usage statistics
    - Parameters: time_range (optional, default: "day")
    - Returns: Bandwidth usage analysis
    - Example: plex_performance(operation="get_bandwidth", time_range="week")
    - Use when: Analyzing network usage

    set_quality: Set streaming quality settings
    - Parameters: profile_name (required), quality (required), bitrate (optional)
    - Returns: Success confirmation
    - Example: plex_performance(operation="set_quality", profile_name="default", quality="1080p", bitrate=20000)
    - Use when: Configuring streaming quality

    get_throttling: Get throttling status
    - Parameters: profile_name (optional)
    - Returns: Dictionary with throttling status and settings
    - Example: plex_performance(operation="get_throttling", profile_name="default")
    - Use when: Checking bandwidth throttling configuration

    set_throttling: Configure throttling settings
    - Parameters: profile_name (required), enabled (required), download_limit (optional), upload_limit (optional)
    - Returns: Success confirmation
    - Example: plex_performance(operation="set_throttling", profile_name="default", enabled=True, download_limit=10000)
    - Use when: Setting bandwidth limits

    list_profiles: List all quality profiles
    - Parameters: None required
    - Returns: List of quality profiles
    - Example: plex_performance(operation="list_profiles")
    - Use when: Viewing available quality profiles

    create_profile: Create a new quality profile
    - Parameters: profile_name (required), settings (required), is_default (optional)
    - Returns: Success confirmation
    - Example: plex_performance(operation="create_profile", profile_name="4K", settings={"quality": "4K"})
    - Use when: Creating custom quality profiles

    delete_profile: Delete a quality profile
    - Parameters: profile_name (required)
    - Returns: Success confirmation
    - Example: plex_performance(operation="delete_profile", profile_name="old-profile")
    - Use when: Removing unused quality profiles

    get_server_status: Get current server status
    - Parameters: None required
    - Returns: Server status information
    - Example: plex_performance(operation="get_server_status")
    - Use when: Checking server health and status

    get_server_info: Get comprehensive server information
    - Parameters: None required
    - Returns: Combined server status and library information
    - Example: plex_performance(operation="get_server_info")
    - Use when: Getting complete server overview

    Prerequisites:
        - Plex Media Server running and accessible
        - Valid PLEX_TOKEN environment variable set
        - Admin/owner permissions for settings modification operations

    Args:
        operation (str): The performance operation to perform. Required. Must be one of: "get_transcode_settings", "update_transcode_settings", "get_transcoding_status", "get_bandwidth", "set_quality", "get_throttling", "set_throttling", "list_profiles", "create_profile", "delete_profile", "get_server_status", "get_server_info"
        profile_name (str | None): Quality profile name. Required for: update_transcode_settings, set_quality, set_throttling, create_profile, delete_profile. Optional for: get_transcode_settings, get_throttling.
        settings (dict | None): Settings dictionary. Required for: update_transcode_settings, create_profile.
        quality (str | None): Quality setting (e.g., "1080p", "720p", "4K"). Required for: set_quality.
        bitrate (int | None): Maximum bitrate in kbps. Optional for: set_quality.
        enabled (bool | None): Whether to enable throttling. Required for: set_throttling.
        download_limit (int | None): Download limit in kbps. Optional for: set_throttling.
        upload_limit (int | None): Upload limit in kbps. Optional for: set_throttling.
        time_range (str): Time range for bandwidth data ("hour", "day", "week", "month"). Default: "day". Optional for: get_bandwidth.
        is_default (bool): Set as default profile. Default: False. Optional for: create_profile.

    Returns:
        Dictionary containing:
            - success: Boolean indicating operation success
            - operation: The operation that was performed
            - data: Operation-specific result data
            - error: Error message if success is False
            - error_code: Specific error code for programmatic handling
            - suggestions: List of suggested fixes (on error)

    Examples:
        # Get transcoding status
        result = await plex_performance(operation="get_transcoding_status")
        # Returns: {'success': True, 'operation': 'get_transcoding_status', 'data': {...}}

        # Get bandwidth usage
        result = await plex_performance(operation="get_bandwidth", time_range="week")
        # Returns: {'success': True, 'operation': 'get_bandwidth', 'data': {...}}

        # List quality profiles
        result = await plex_performance(operation="list_profiles")
        # Returns: {'success': True, 'operation': 'list_profiles', 'data': [...]}

        # Update transcode settings
        result = await plex_performance(
            operation="update_transcode_settings",
            profile_name="default",
            settings={"quality": "1080p", "bitrate": 20000}
        )
        # Returns: {'success': True, 'operation': 'update_transcode_settings'}

        # Get server status
        result = await plex_performance(operation="get_server_status")
        # Returns: {'success': True, 'operation': 'get_server_status', 'data': {...}}

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Set PLEX_TOKEN environment variable with your auth token
        - "profile_name required": Provide valid profile name for operations that require it
        - "Profile not found": Use plex_performance(operation="list_profiles") to find valid profile names
        - "Permission denied": Admin access required for settings modification operations

    See Also:
        - plex_library: For library management operations
        - plex_streaming: For playback control operations
    """
    try:
        plex = _get_plex_service()

        # Operation: get_transcode_settings
        if operation == "get_transcode_settings":
            result = await plex.get_transcode_settings(profile_name=profile_name)
            return {
                "success": True,
                "operation": "get_transcode_settings",
                "data": result,
            }

        # Operation: update_transcode_settings
        if operation == "update_transcode_settings":
            if not profile_name:
                return {
                    "success": False,
                    "message": "profile_name is required for update_transcode_settings operation",
                    "error": "profile_name is required for update_transcode_settings operation",
                    "error_code": "MISSING_PROFILE_NAME",
                    "suggestions": ["Provide profile_name parameter"],
                }
            if not settings:
                return {
                    "success": False,
                    "message": "settings dictionary is required for update_transcode_settings operation",
                    "error": "settings dictionary is required for update_transcode_settings operation",
                    "error_code": "MISSING_SETTINGS",
                    "suggestions": ["Provide settings parameter with configuration dictionary"],
                }

            result = await plex.update_transcode_settings(profile_name=profile_name, settings=settings)
            return {
                "success": result,
                "operation": "update_transcode_settings",
                "profile_name": profile_name,
                "data": {"updated": result},
            }

        # Operation: get_transcoding_status
        if operation == "get_transcoding_status":
            result = await plex.get_transcoding_status()
            return {
                "success": True,
                "operation": "get_transcoding_status",
                "data": result.model_dump() if hasattr(result, "dict") else result,
            }

        # Operation: get_bandwidth
        if operation == "get_bandwidth":
            result = await plex.get_bandwidth_usage(time_range=time_range)
            return {
                "success": True,
                "operation": "get_bandwidth",
                "time_range": time_range,
                "data": result.model_dump() if hasattr(result, "dict") else result,
            }

        # Operation: set_quality
        if operation == "set_quality":
            if not profile_name:
                return {
                    "success": False,
                    "message": "profile_name is required for set_quality operation",
                    "error": "profile_name is required for set_quality operation",
                    "error_code": "MISSING_PROFILE_NAME",
                    "suggestions": ["Provide profile_name parameter"],
                }
            if not quality:
                return {
                    "success": False,
                    "message": "quality is required for set_quality operation",
                    "error": "quality is required for set_quality operation",
                    "error_code": "MISSING_QUALITY",
                    "suggestions": ["Provide quality parameter (e.g., '1080p', '720p', '480p')"],
                }

            result = await plex.set_stream_quality(profile_name=profile_name, quality=quality, bitrate=bitrate)
            return {
                "success": result,
                "operation": "set_quality",
                "profile_name": profile_name,
                "quality": quality,
                "data": {"quality_set": result},
            }

        # Operation: get_throttling
        if operation == "get_throttling":
            result = await plex.get_throttling_status(profile_name=profile_name)
            return {
                "success": True,
                "operation": "get_throttling",
                "data": result,
            }

        # Operation: set_throttling
        if operation == "set_throttling":
            if not profile_name:
                return {
                    "success": False,
                    "message": "profile_name is required for set_throttling operation",
                    "error": "profile_name is required for set_throttling operation",
                    "error_code": "MISSING_PROFILE_NAME",
                    "suggestions": ["Provide profile_name parameter"],
                }
            if enabled is None:
                return {
                    "success": False,
                    "message": "enabled is required for set_throttling operation",
                    "error": "enabled is required for set_throttling operation",
                    "error_code": "MISSING_ENABLED",
                    "suggestions": ["Provide enabled parameter (True or False)"],
                }

            result = await plex.set_throttling(
                profile_name=profile_name,
                enabled=enabled,
                download_limit=download_limit,
                upload_limit=upload_limit,
            )
            return {
                "success": result,
                "operation": "set_throttling",
                "profile_name": profile_name,
                "enabled": enabled,
                "data": {"throttling_set": result},
            }

        # Operation: list_profiles
        if operation == "list_profiles":
            result = await plex.list_quality_profiles()
            return {
                "success": True,
                "operation": "list_profiles",
                "data": [p.model_dump() if hasattr(p, "dict") else p for p in result],
                "count": len(result),
            }

        # Operation: create_profile
        if operation == "create_profile":
            if not profile_name:
                return {
                    "success": False,
                    "message": "profile_name is required for create_profile operation",
                    "error": "profile_name is required for create_profile operation",
                    "error_code": "MISSING_PROFILE_NAME",
                    "suggestions": ["Provide profile_name parameter"],
                }
            if not settings:
                return {
                    "success": False,
                    "message": "settings dictionary is required for create_profile operation",
                    "error": "settings dictionary is required for create_profile operation",
                    "error_code": "MISSING_SETTINGS",
                    "suggestions": ["Provide settings parameter with profile configuration"],
                }

            result = await plex.create_quality_profile(name=profile_name, settings=settings, is_default=is_default)
            return {
                "success": result,
                "operation": "create_profile",
                "profile_name": profile_name,
                "data": {"created": result},
            }

        # Operation: delete_profile
        if operation == "delete_profile":
            if not profile_name:
                return {
                    "success": False,
                    "message": "profile_name is required for delete_profile operation",
                    "error": "profile_name is required for delete_profile operation",
                    "error_code": "MISSING_PROFILE_NAME",
                    "suggestions": ["Provide profile_name parameter"],
                }

            result = await plex.delete_quality_profile(profile_name=profile_name)
            return {
                "success": result,
                "operation": "delete_profile",
                "profile_name": profile_name,
                "data": {"deleted": result},
            }

        # Operation: get_server_status
        if operation == "get_server_status":
            result = await plex.get_server_status()
            return {
                "success": True,
                "operation": "get_server_status",
                "data": result.model_dump() if hasattr(result, "dict") else result,
            }

        # Operation: get_server_info
        if operation == "get_server_info":
            # This combines get_server_status and list_libraries
            status = await plex.get_server_status()
            libraries = await plex.list_libraries()
            return {
                "success": True,
                "operation": "get_server_info",
                "data": {
                    "status": status.model_dump() if hasattr(status, "dict") else status,
                    "libraries": libraries,
                },
            }

        return {
            "success": False,
            "message": f"Invalid operation: '{operation}'",
            "error_code": "INVALID_OPERATION",
            "suggestions": [
                "Valid operations: get_transcode_settings, update_transcode_settings, get_transcoding_status, "
                "get_bandwidth, set_quality, get_throttling, set_throttling, list_profiles, create_profile, "
                "delete_profile, get_server_status, get_server_info",
                f"You provided: '{operation}'",
            ],
        }

    except RuntimeError as e:
        error_msg = str(e)
        suggestions = []

        if "PLEX_TOKEN" in error_msg:
            suggestions = [
                "Set PLEX_TOKEN environment variable",
                "Get token from: Plex Web App → Settings → Account → Authorized Devices",
                "Or visit: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/",
            ]
        elif "not found" in error_msg.lower():
            suggestions = [
                "Verify the profile_name is correct",
                "Use plex_performance(operation='list_profiles') to find valid profile names",
            ]

        return {
            "success": False,
            "message": error_msg,
            "error": error_msg,
            "error_code": "RUNTIME_ERROR",
            "operation": operation,
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.error(
            f"Unexpected error in plex_performance operation '{operation}': {e}",
            exc_info=True,
        )
        return {
            "success": False,
            "message": f"Unexpected error during {operation}: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
            "operation": operation,
            "suggestions": [
                "Check server logs for detailed error information",
                "Verify all required parameters are provided",
                "Try the operation again with valid parameters",
            ],
        }
