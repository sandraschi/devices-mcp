"""
PlexMCP Quality Profiles Portmanteau Tool

Consolidates all quality profile management operations into a single comprehensive interface.
FastMCP 2.13+ compliant with comprehensive docstrings and AI-friendly error messages.
"""

import os
from typing import Any, Dict, Literal, Optional

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
async def plex_quality(
    operation: Literal[
        "list_profiles",
        "get_profile",
        "create_profile",
        "update_profile",
        "delete_profile",
        "set_default",
    ],
    profile_name: Optional[str] = None,
    settings: Optional[Dict[str, Any]] = None,
    is_default: bool = False,
) -> Dict[str, Any]:
    """Comprehensive quality profile management tool for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 6 separate tools (one per profile operation), this tool consolidates related
    quality profile operations into a single interface. This design:
    - Prevents tool explosion (6 tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with quality profile tasks
    - Enables consistent quality profile interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - list_profiles: List all available quality profiles
    - get_profile: Get detailed information about a specific profile
    - create_profile: Create a new quality profile
    - update_profile: Update an existing quality profile
    - delete_profile: Delete a quality profile
    - set_default: Set a profile as the default

    OPERATIONS DETAIL:

    list_profiles: List all quality profiles
    - Parameters: None
    - Returns: List of all quality profiles with basic information
    - Use when: Browsing available quality profiles

    get_profile: Get profile details
    - Parameters: profile_name (required)
    - Returns: Detailed profile information including settings
    - Use when: Viewing profile configuration

    create_profile: Create new profile
    - Parameters: profile_name (required), settings (required), is_default (optional)
    - Returns: Created profile information
    - Use when: Creating a custom quality profile

    update_profile: Update profile
    - Parameters: profile_name (required), settings (required)
    - Returns: Updated profile information
    - Use when: Modifying profile settings

    delete_profile: Delete profile
    - Parameters: profile_name (required)
    - Returns: Deletion confirmation
    - Use when: Removing a quality profile

    set_default: Set default profile
    - Parameters: profile_name (required)
    - Returns: Confirmation with default profile information
    - Use when: Setting the default quality profile

    Prerequisites:
        - Plex Media Server running and accessible
        - Valid PLEX_TOKEN environment variable set
        - PLEX_SERVER_URL configured (or defaults to http://localhost:32400)
        - Admin/owner permissions for create/update/delete operations

    Args:
        operation (str): The quality profile operation to perform. Required. Must be one of: "list_profiles", "get_profile", "create_profile", "update_profile", "delete_profile", "set_default"
        profile_name (str | None): Name of the quality profile. Required for: get_profile, create_profile, update_profile, delete_profile, set_default.
        settings (dict[str, Any] | None): Profile settings dictionary. Required for: create_profile, update_profile.
        is_default (bool): Whether to set as default profile (used for create_profile). Default: False.

    Returns:
        Operation-specific result with profile data

    Examples:
        # List all profiles
        plex_quality("list_profiles")

        # Get profile details
        plex_quality("get_profile", profile_name="High Quality")

        # Create a new profile
        plex_quality("create_profile", profile_name="4K Profile", settings={"quality": "4K", "bitrate": 20000})

        # Set default profile
        plex_quality("set_default", profile_name="High Quality")

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Configure authentication token
        - "profile_name required": Provide profile name for profile operations
        - "settings required": Provide settings when creating/updating profiles
        - "Profile not found": Verify profile_name is correct
        - "Permission denied": Admin access required for create/update/delete
    """
    try:
        plex = _get_plex_service()

        if operation == "list_profiles":
            profiles = await plex.list_quality_profiles()
            return {
                "success": True,
                "operation": "list_profiles",
                "profiles": profiles,
                "count": len(profiles) if isinstance(profiles, list) else 0,
            }

        if operation == "get_profile":
            if not profile_name:
                return {
                    "success": False,
                    "error": "profile_name is required for get_profile operation",
                    "error_code": "MISSING_PARAMETER",
                    "suggestions": ["Provide a profile name"],
                }

            settings = await plex.get_transcode_settings(profile_name=profile_name)
            return {
                "success": True,
                "operation": "get_profile",
                "profile_name": profile_name,
                "settings": settings,
            }

        if operation == "create_profile":
            if not profile_name:
                return {
                    "success": False,
                    "error": "profile_name is required for create_profile operation",
                    "error_code": "MISSING_PARAMETER",
                }
            if not settings:
                return {
                    "success": False,
                    "error": "settings is required for create_profile operation",
                    "error_code": "MISSING_PARAMETER",
                }

            result = await plex.create_quality_profile(
                name=profile_name, settings=settings, is_default=is_default
            )
            return {
                "success": True,
                "operation": "create_profile",
                "profile_name": profile_name,
                "is_default": is_default,
                "result": result,
            }

        if operation == "update_profile":
            if not profile_name:
                return {
                    "success": False,
                    "error": "profile_name is required for update_profile operation",
                    "error_code": "MISSING_PARAMETER",
                }
            if not settings:
                return {
                    "success": False,
                    "error": "settings is required for update_profile operation",
                    "error_code": "MISSING_PARAMETER",
                }

            result = await plex.update_transcode_settings(
                profile_name=profile_name, settings=settings
            )
            return {
                "success": True,
                "operation": "update_profile",
                "profile_name": profile_name,
                "result": result,
            }

        if operation == "delete_profile":
            if not profile_name:
                return {
                    "success": False,
                    "error": "profile_name is required for delete_profile operation",
                    "error_code": "MISSING_PARAMETER",
                }

            result = await plex.delete_quality_profile(profile_name=profile_name)
            return {
                "success": True,
                "operation": "delete_profile",
                "profile_name": profile_name,
                "result": result,
            }

        if operation == "set_default":
            if not profile_name:
                return {
                    "success": False,
                    "error": "profile_name is required for set_default operation",
                    "error_code": "MISSING_PARAMETER",
                }

            # Update profile to set as default
            result = await plex.create_quality_profile(
                name=profile_name, settings={}, is_default=True
            )
            return {
                "success": True,
                "operation": "set_default",
                "profile_name": profile_name,
                "result": result,
            }

        return {
            "success": False,
            "error": f"Unknown operation: {operation}",
            "error_code": "INVALID_OPERATION",
            "suggestions": [
                "Use one of: list_profiles, get_profile, create_profile, update_profile, delete_profile, set_default"
            ],
        }

    except Exception as e:
        logger.exception("Error in plex_quality operation '{operation}':")
        return {
            "success": False,
            "error": str(e),
            "error_code": "EXECUTION_ERROR",
            "suggestions": [
                "Verify Plex server is accessible",
                "Check PLEX_TOKEN is set correctly",
                "Verify profile_name is valid if provided",
                "Ensure you have admin permissions for create/update/delete operations",
            ],
        }
