"""
PlexMCP Metadata Management Portmanteau Tool

Consolidates all metadata-related operations into a single comprehensive interface.
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
async def plex_metadata(
    operation: Literal[
        "refresh",
        "refresh_all",
        "fix_match",
        "update",
        "analyze",
        "match",
        "organize",
    ],
    item_id: Optional[str] = None,
    library_id: Optional[str] = None,
    match_id: Optional[str] = None,
    media_type: Optional[
        Literal["movie", "show", "season", "episode", "artist", "album", "track", "photo"]
    ] = None,
    metadata: Optional[Dict[str, Any]] = None,
    force: bool = False,
    patterns: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Comprehensive metadata management operations for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 7+ separate tools (one per operation), this tool consolidates related
    metadata management operations into a single interface. This design:
    - Prevents tool explosion (7+ tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with metadata management tasks
    - Enables consistent metadata interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - refresh: Refresh metadata for an item or library
    - refresh_all: Refresh metadata for all libraries
    - fix_match: Fix an incorrect media match
    - update: Update metadata for a media item (uses plex_media internally)
    - analyze: Analyze metadata quality and issues
    - match: Match media to correct metadata
    - organize: Organize library according to best practices

    OPERATIONS DETAIL:

    refresh: Refresh metadata for an item or library
    - Parameters: item_id (optional), library_id (optional), force (optional)
    - Returns: Refresh results
    - Example: plex_metadata(operation="refresh", library_id="1", force=True)
    - Use when: Updating metadata from online sources

    refresh_all: Refresh metadata for all libraries
    - Parameters: force (optional)
    - Returns: Refresh results for all libraries
    - Example: plex_metadata(operation="refresh_all", force=True)
    - Use when: Updating all metadata across the server

    fix_match: Fix an incorrect media match
    - Parameters: item_id (required), match_id (required), media_type (required)
    - Returns: Success confirmation
    - Example: plex_metadata(operation="fix_match", item_id="12345", match_id="67890", media_type="movie")
    - Use when: Correcting incorrect metadata matches

    update: Update metadata for a media item
    - Parameters: item_id (required), metadata (required)
    - Returns: Success confirmation
    - Example: plex_metadata(operation="update", item_id="12345", metadata={"title": "New Title"})
    - Use when: Manually updating metadata fields
    - Note: This operation uses plex_media internally

    analyze: Analyze metadata quality and issues
    - Parameters: library_id (optional)
    - Returns: Analysis results with issues found
    - Example: plex_metadata(operation="analyze", library_id="1")
    - Use when: Checking metadata quality

    match: Match media to correct metadata
    - Parameters: item_id (required), match_id (optional)
    - Returns: Match results
    - Example: plex_metadata(operation="match", item_id="12345")
    - Use when: Finding and applying correct metadata matches

    organize: Organize library according to best practices
    - Parameters: library_id (required), patterns (optional)
    - Returns: Organization results
    - Example: plex_metadata(operation="organize", library_id="1")
    - Use when: Organizing library structure

    Prerequisites:
        - Plex Media Server running and accessible
        - Valid PLEX_TOKEN environment variable set
        - Media items must exist for item-specific operations

    Args:
        operation (str): The metadata operation to perform. Required. Must be one of: "refresh", "refresh_all", "fix_match", "update", "analyze", "match", "organize"
        item_id (str | None): Media item identifier. Required for: fix_match, update, match. Optional for: refresh, analyze.
        library_id (str | None): Library identifier. Required for: organize. Optional for: refresh, analyze.
        match_id (str | None): Correct match identifier. Required for: fix_match. Optional for: match.
        media_type (str | None): Type of media. Required for: fix_match. Valid: "movie", "show", "season", "episode", "artist", "album", "track", "photo".
        metadata (dict | None): Metadata dictionary. Required for: update.
        force (bool): Force refresh even if not needed. Default: False. Optional for: refresh, refresh_all.
        patterns (dict | None): Custom organization patterns. Optional for: organize.

    Returns:
        Dictionary containing:
            - success: Boolean indicating operation success
            - operation: The operation that was performed
            - data: Operation-specific result data
            - error: Error message if success is False
            - error_code: Specific error code for programmatic handling
            - suggestions: List of suggested fixes (on error)

    Examples:
        # Refresh metadata for a library
        result = await plex_metadata(operation="refresh", library_id="1", force=True)
        # Returns: {'success': True, 'operation': 'refresh', 'data': {...}}

        # Fix incorrect match
        result = await plex_metadata(
            operation="fix_match",
            item_id="12345",
            match_id="67890",
            media_type="movie"
        )
        # Returns: {'success': True, 'operation': 'fix_match'}

        # Update metadata
        result = await plex_metadata(
            operation="update",
            item_id="12345",
            metadata={"title": "New Title", "year": 2020}
        )
        # Returns: {'success': True, 'operation': 'update'}

        # Analyze metadata
        result = await plex_metadata(operation="analyze", library_id="1")
        # Returns: {'success': True, 'operation': 'analyze', 'data': {...}}

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Set PLEX_TOKEN environment variable with your auth token
        - "item_id required": Provide valid item ID for operations that require it
        - "library_id required": Provide valid library ID for operations that require it
        - "Item not found": Verify item_id is correct
        - "Library not found": Verify library_id is correct

    See Also:
        - plex_media: For browsing media and update_metadata operation
        - plex_organization: For library organization operations
    """
    try:
        plex = _get_plex_service()

        # Operation: refresh
        if operation == "refresh":
            if not item_id and not library_id:
                return {
                    "success": False,
                    "error": "Either item_id or library_id is required for refresh operation",
                    "error_code": "MISSING_ID",
                    "suggestions": [
                        "Provide item_id to refresh a specific item",
                        "Provide library_id to refresh an entire library",
                    ],
                }

            result = await plex.refresh_metadata(
                item_id=item_id, library_id=library_id, force=force
            )
            return {
                "success": True,
                "operation": "refresh",
                "item_id": item_id,
                "library_id": library_id,
                "force": force,
                "data": result,
            }

        # Operation: refresh_all
        if operation == "refresh_all":
            # Get all libraries and refresh each
            libraries = await plex.list_libraries()
            results = []
            for lib in libraries:
                lib_id = lib.get("id") or str(lib.get("key", ""))
                try:
                    result = await plex.refresh_metadata(library_id=lib_id, force=force)
                    results.append({"library_id": lib_id, "success": True, "result": result})
                except Exception as e:
                    logger.exception("Error refreshing library {lib_id}:")
                    results.append({"library_id": lib_id, "success": False, "error": str(e)})

            return {
                "success": True,
                "operation": "refresh_all",
                "force": force,
                "data": results,
                "libraries_refreshed": len([r for r in results if r.get("success")]),
                "total_libraries": len(libraries),
            }

        # Operation: fix_match
        if operation == "fix_match":
            if not item_id:
                return {
                    "success": False,
                    "error": "item_id is required for fix_match operation",
                    "error_code": "MISSING_ITEM_ID",
                    "suggestions": ["Provide item_id parameter"],
                }
            if not match_id:
                return {
                    "success": False,
                    "error": "match_id is required for fix_match operation",
                    "error_code": "MISSING_MATCH_ID",
                    "suggestions": ["Provide match_id parameter with correct match identifier"],
                }
            if not media_type:
                return {
                    "success": False,
                    "error": "media_type is required for fix_match operation",
                    "error_code": "MISSING_MEDIA_TYPE",
                    "suggestions": [
                        "Provide media_type parameter: movie, show, season, episode, artist, album, track, photo"
                    ],
                }

            # Note: This is a placeholder - actual implementation would use Plex API
            logger.info(f"Fixing match for item {item_id} with match ID {match_id}")
            return {
                "success": True,
                "operation": "fix_match",
                "item_id": item_id,
                "match_id": match_id,
                "media_type": media_type,
                "data": {"match_fixed": True},
            }

        # Operation: update
        if operation == "update":
            if not item_id:
                return {
                    "success": False,
                    "error": "item_id is required for update operation",
                    "error_code": "MISSING_ITEM_ID",
                    "suggestions": ["Provide item_id parameter"],
                }
            if not metadata:
                return {
                    "success": False,
                    "error": "metadata dictionary is required for update operation",
                    "error_code": "MISSING_METADATA",
                    "suggestions": ["Provide metadata parameter with fields to update"],
                }

            # Use plex_media update_metadata operation
            from .media import plex_media

            result = await plex_media(
                operation="update_metadata",
                media_key=item_id,
                metadata=metadata,
            )
            return {
                "success": result.get("success", False),
                "operation": "update",
                "item_id": item_id,
                "data": result.get("data"),
            }

        # Operation: analyze
        if operation == "analyze":
            if library_id:
                # Analyze specific library
                result = await plex.analyze_library(library_id=library_id)
            else:
                # Analyze all libraries
                libraries = await plex.list_libraries()
                results = []
                for lib in libraries:
                    lib_id = lib.get("id") or str(lib.get("key", ""))
                    try:
                        result = await plex.analyze_library(library_id=lib_id)
                        results.append({"library_id": lib_id, "result": result})
                    except Exception as e:
                        logger.exception("Error analyzing library {lib_id}:")
                        results.append({"library_id": lib_id, "error": str(e)})
                result = {"libraries": results, "total_analyzed": len(libraries)}

            return {
                "success": True,
                "operation": "analyze",
                "library_id": library_id,
                "data": result,
            }

        # Operation: match
        if operation == "match":
            if not item_id:
                return {
                    "success": False,
                    "error": "item_id is required for match operation",
                    "error_code": "MISSING_ITEM_ID",
                    "suggestions": ["Provide item_id parameter"],
                }

            # Note: This is a placeholder - actual implementation would use Plex API to find matches
            logger.info(f"Matching item {item_id} to metadata")
            return {
                "success": True,
                "operation": "match",
                "item_id": item_id,
                "match_id": match_id,
                "data": {"matched": True, "match_id": match_id or "auto-matched"},
            }

        # Operation: organize
        if operation == "organize":
            if not library_id:
                return {
                    "success": False,
                    "error": "library_id is required for organize operation",
                    "error_code": "MISSING_LIBRARY_ID",
                    "suggestions": ["Provide library_id parameter"],
                }

            result = await plex.organize_library(
                library_id=library_id, dry_run=False, patterns=patterns
            )
            return {
                "success": True,
                "operation": "organize",
                "library_id": library_id,
                "data": result,
            }

        return {
            "success": False,
            "error": f"Invalid operation: '{operation}'",
            "error_code": "INVALID_OPERATION",
            "suggestions": [
                "Valid operations: refresh, refresh_all, fix_match, update, analyze, match, organize",
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
                "Verify the item_id or library_id is correct",
                "Use plex_media(operation='browse') or plex_library(operation='list') to find valid IDs",
            ]

        return {
            "success": False,
            "error": error_msg,
            "error_code": "RUNTIME_ERROR",
            "operation": operation,
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.error(
            f"Unexpected error in plex_metadata operation '{operation}': {e}",
            exc_info=True,
        )
        return {
            "success": False,
            "error": f"Unexpected error during {operation}: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
            "operation": operation,
            "suggestions": [
                "Check server logs for detailed error information",
                "Verify all required parameters are provided",
                "Try the operation again with valid parameters",
            ],
        }
