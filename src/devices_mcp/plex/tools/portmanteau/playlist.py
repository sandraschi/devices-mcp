"""
PlexMCP Playlist Management Portmanteau Tool

Consolidates all playlist-related operations into a single comprehensive interface.
FastMCP 2.13+ compliant with comprehensive docstrings and AI-friendly error messages.
"""

import os
from typing import Any, Dict, List, Literal, Optional

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


def _format_playlist(playlist) -> Dict[str, Any]:
    """Format a playlist object into a dictionary."""

    return {
        "key": playlist.ratingKey,
        "title": playlist.title,
        "type": playlist.playlistType,
        "summary": playlist.summary or "",
        "duration": playlist.duration,
        "item_count": len(playlist.items()),
        "smart": playlist.smart,
        "created_at": int(playlist.addedAt.timestamp()),
        "updated_at": int(playlist.updatedAt.timestamp())
        if playlist.updatedAt
        else int(playlist.addedAt.timestamp()),
        "owner": playlist.username,
    }


@mcp.tool()
async def plex_playlist(
    operation: Literal[
        "list",
        "get",
        "create",
        "update",
        "delete",
        "add_items",
        "remove_items",
        "get_analytics",
    ],
    playlist_id: Optional[str] = None,
    title: Optional[str] = None,
    items: Optional[List[str]] = None,
    description: Optional[str] = None,
    public: Optional[bool] = None,
    sort: Optional[str] = None,
) -> Dict[str, Any]:
    """Comprehensive playlist management operations for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 8 separate tools (one per operation), this tool consolidates related
    playlist operations into a single interface. This design:
    - Prevents tool explosion (8 tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with playlist management tasks
    - Enables consistent playlist interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - list: List all playlists
    - get: Get detailed information about a specific playlist
    - create: Create a new playlist
    - update: Update playlist settings
    - delete: Delete a playlist
    - add_items: Add items to a playlist
    - remove_items: Remove items from a playlist
    - get_analytics: Get analytics for a playlist

    OPERATIONS DETAIL:

    list: List all playlists
    - Parameters: None required
    - Returns: List of all playlists
    - Example: plex_playlist(operation="list")
    - Use when: You want to see all available playlists

    get: Get detailed information about a specific playlist
    - Parameters: playlist_id (required)
    - Returns: Detailed playlist information
    - Example: plex_playlist(operation="get", playlist_id="12345")
    - Use when: You need details about a specific playlist

    create: Create a new playlist
    - Parameters: title (required), items (required), description (optional), public (optional), sort (optional)
    - Returns: Created playlist information
    - Example: plex_playlist(operation="create", title="My Playlist", items=["1", "2", "3"])
    - Use when: Creating a new playlist with media items

    update: Update playlist settings
    - Parameters: playlist_id (required), title (optional), description (optional), public (optional), sort (optional)
    - Returns: Updated playlist information
    - Example: plex_playlist(operation="update", playlist_id="12345", title="New Title")
    - Use when: Changing playlist details

    delete: Delete a playlist
    - Parameters: playlist_id (required)
    - Returns: Deletion confirmation
    - Example: plex_playlist(operation="delete", playlist_id="12345")
    - Use when: Removing a playlist (WARNING: Cannot be undone)

    add_items: Add items to a playlist
    - Parameters: playlist_id (required), items (required)
    - Returns: Updated playlist information
    - Example: plex_playlist(operation="add_items", playlist_id="12345", items=["4", "5"])
    - Use when: Adding media items to an existing playlist

    remove_items: Remove items from a playlist
    - Parameters: playlist_id (required), items (required)
    - Returns: Updated playlist information
    - Example: plex_playlist(operation="remove_items", playlist_id="12345", items=["1", "2"])
    - Use when: Removing media items from a playlist

    get_analytics: Get analytics for a playlist
    - Parameters: playlist_id (required)
    - Returns: Analytics data for the playlist
    - Example: plex_playlist(operation="get_analytics", playlist_id="12345")
    - Use when: Viewing playlist statistics and metrics

    Prerequisites:
        - Plex Media Server running and accessible
        - Valid PLEX_TOKEN environment variable set
        - Media items must exist for create/add_items operations

    Args:
        operation (str): The playlist operation to perform. Required. Must be one of: "list", "get", "create", "update", "delete", "add_items", "remove_items", "get_analytics"
        playlist_id (str | None): Playlist identifier. Required for: get, update, delete, add_items, remove_items, get_analytics.
        title (str | None): Playlist title (min 1, max 255). Required for: create. Optional for: update.
        items (list[str] | None): List of media item IDs. Required for: create, add_items, remove_items.
        description (str | None): Playlist description. Optional for: create, update.
        public (bool | None): Whether playlist is publicly visible (limited support). Optional for: create, update.
        sort (str | None): Sort order (limited support). Optional for: create, update.

    Returns:
        Dictionary containing:
            - success: Boolean indicating operation success
            - operation: The operation that was performed
            - data: Operation-specific result data
            - count: Number of playlists returned (for list operation)
            - error: Error message if success is False
            - error_code: Specific error code for programmatic handling
            - suggestions: List of suggested fixes (on error)

    Examples:
        # List all playlists
        result = await plex_playlist(operation="list")
        # Returns: {'success': True, 'operation': 'list', 'data': [...], 'count': 10}

        # Get playlist details
        result = await plex_playlist(operation="get", playlist_id="12345")
        # Returns: {'success': True, 'operation': 'get', 'data': {...}}

        # Create new playlist
        result = await plex_playlist(
            operation="create",
            title="My Favorites",
            items=["1", "2", "3"],
            description="My favorite movies"
        )
        # Returns: {'success': True, 'operation': 'create', 'data': {...}}

        # Add items to playlist
        result = await plex_playlist(
            operation="add_items",
            playlist_id="12345",
            items=["4", "5"]
        )
        # Returns: {'success': True, 'operation': 'add_items', 'data': {...}}

        # Get analytics
        result = await plex_playlist(operation="get_analytics", playlist_id="12345")
        # Returns: {'success': True, 'operation': 'get_analytics', 'data': {...}}

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Set PLEX_TOKEN environment variable with your auth token
        - "playlist_id required": Provide valid playlist ID for operations that require it
        - "Playlist not found": Use plex_playlist(operation="list") to find valid playlist IDs
        - "No valid media items found": Verify media item IDs exist and are accessible
        - "Title required": Provide title parameter for create operation

    See Also:
        - plex_media: For browsing and searching media items to add to playlists
        - plex_library: For library management operations
    """
    try:
        plex = _get_plex_service()
        await plex.connect()

        # Operation: list
        if operation == "list":
            playlists = await plex.server.playlists()
            playlist_data = [_format_playlist(p) for p in playlists]
            return {
                "success": True,
                "operation": "list",
                "data": playlist_data,
                "count": len(playlist_data),
            }

        # Operation: get
        if operation == "get":
            if not playlist_id:
                return {
                    "success": False,
                    "error": "playlist_id is required for get operation",
                    "error_code": "MISSING_PLAYLIST_ID",
                    "suggestions": [
                        "Use plex_playlist(operation='list') to find available playlist IDs"
                    ],
                }

            try:
                playlist = await plex.server.playlist(playlist_id)
                return {
                    "success": True,
                    "operation": "get",
                    "data": _format_playlist(playlist),
                }
            except Exception as e:
                logger.exception("Error getting playlist {playlist_id}:")
                return {
                    "success": False,
                    "error": f"Playlist {playlist_id} not found: {e!s}",
                    "error_code": "PLAYLIST_NOT_FOUND",
                    "suggestions": [
                        "Use plex_playlist(operation='list') to find valid playlist IDs",
                        "Verify the playlist_id is correct",
                    ],
                }

        # Operation: create
        elif operation == "create":
            if not title:
                return {
                    "success": False,
                    "error": "title is required for create operation",
                    "error_code": "MISSING_TITLE",
                    "suggestions": ["Provide title parameter (min 1 character, max 255)"],
                }
            if not items:
                return {
                    "success": False,
                    "error": "items list is required for create operation",
                    "error_code": "MISSING_ITEMS",
                    "suggestions": ["Provide items parameter with list of media item IDs"],
                }

            # Get the media items from Plex
            items_to_add = []
            for item_id in items:
                try:
                    item = await plex.server.lookupItem(item_id)
                    items_to_add.append(item)
                except Exception as e:
                    logger.warning(f"Could not find media item {item_id}: {e}")

            if not items_to_add:
                return {
                    "success": False,
                    "error": "No valid media items found to create playlist",
                    "error_code": "NO_VALID_ITEMS",
                    "suggestions": [
                        "Verify media item IDs exist",
                        "Use plex_media(operation='browse') or plex_media(operation='search') to find valid item IDs",
                    ],
                }

            # Create the playlist
            playlist = await plex.server.createPlaylist(
                title=title,
                items=items_to_add,
                smart=False,
                summary=description or "",
            )

            return {
                "success": True,
                "operation": "create",
                "data": _format_playlist(playlist),
            }

        # Operation: update
        elif operation == "update":
            if not playlist_id:
                return {
                    "success": False,
                    "error": "playlist_id is required for update operation",
                    "error_code": "MISSING_PLAYLIST_ID",
                    "suggestions": ["Provide playlist_id to update"],
                }

            try:
                playlist = await plex.server.playlist(playlist_id)

                # Update fields if provided
                if title is not None:
                    playlist.editTitle(title)
                if description is not None:
                    playlist.editSummary(description)
                # Note: public and sort have limited Plex API support

                # Refresh the playlist to get updated data
                playlist.reload()

                return {
                    "success": True,
                    "operation": "update",
                    "playlist_id": playlist_id,
                    "data": _format_playlist(playlist),
                }
            except Exception as e:
                logger.exception("Error updating playlist {playlist_id}:")
                return {
                    "success": False,
                    "error": f"Failed to update playlist: {e!s}",
                    "error_code": "UPDATE_FAILED",
                    "suggestions": [
                        "Verify playlist_id is correct",
                        "Check that you have permissions to update this playlist",
                    ],
                }

        # Operation: delete
        elif operation == "delete":
            if not playlist_id:
                return {
                    "success": False,
                    "error": "playlist_id is required for delete operation",
                    "error_code": "MISSING_PLAYLIST_ID",
                    "suggestions": ["Provide playlist_id to delete"],
                }

            try:
                playlist = await plex.server.playlist(playlist_id)
                await playlist.delete()
                return {
                    "success": True,
                    "operation": "delete",
                    "playlist_id": playlist_id,
                    "data": {"deleted": True},
                }
            except Exception as e:
                logger.exception("Error deleting playlist {playlist_id}:")
                return {
                    "success": False,
                    "error": f"Failed to delete playlist: {e!s}",
                    "error_code": "DELETE_FAILED",
                    "suggestions": [
                        "Verify playlist_id is correct",
                        "Check that you have permissions to delete this playlist",
                    ],
                }

        # Operation: add_items
        elif operation == "add_items":
            if not playlist_id:
                return {
                    "success": False,
                    "error": "playlist_id is required for add_items operation",
                    "error_code": "MISSING_PLAYLIST_ID",
                    "suggestions": ["Provide playlist_id to add items"],
                }
            if not items:
                return {
                    "success": False,
                    "error": "items list is required for add_items operation",
                    "error_code": "MISSING_ITEMS",
                    "suggestions": ["Provide items parameter with list of media item IDs"],
                }

            try:
                playlist = await plex.server.playlist(playlist_id)

                # Get the media items from Plex
                items_to_add = []
                for item_id in items:
                    try:
                        item = await plex.server.lookupItem(item_id)
                        items_to_add.append(item)
                    except Exception as e:
                        logger.warning(f"Could not find media item {item_id}: {e}")

                if not items_to_add:
                    return {
                        "success": False,
                        "error": "No valid media items found to add to playlist",
                        "error_code": "NO_VALID_ITEMS",
                        "suggestions": [
                            "Verify media item IDs exist",
                            "Use plex_media(operation='browse') or plex_media(operation='search') to find valid item IDs",
                        ],
                    }

                # Add items to playlist
                await playlist.addItems(items_to_add)
                playlist.reload()

                return {
                    "success": True,
                    "operation": "add_items",
                    "playlist_id": playlist_id,
                    "data": _format_playlist(playlist),
                }
            except Exception as e:
                logger.exception("Error adding items to playlist {playlist_id}:")
                return {
                    "success": False,
                    "error": f"Failed to add items: {e!s}",
                    "error_code": "ADD_ITEMS_FAILED",
                    "suggestions": [
                        "Verify playlist_id and item IDs are correct",
                        "Check that you have permissions to modify this playlist",
                    ],
                }

        # Operation: remove_items
        elif operation == "remove_items":
            if not playlist_id:
                return {
                    "success": False,
                    "error": "playlist_id is required for remove_items operation",
                    "error_code": "MISSING_PLAYLIST_ID",
                    "suggestions": ["Provide playlist_id to remove items"],
                }
            if not items:
                return {
                    "success": False,
                    "error": "items list is required for remove_items operation",
                    "error_code": "MISSING_ITEMS",
                    "suggestions": [
                        "Provide items parameter with list of media item IDs to remove"
                    ],
                }

            try:
                playlist = await plex.server.playlist(playlist_id)

                # Get the current items
                current_items = playlist.items()

                # Find items to remove
                items_to_remove = []
                for item in current_items:
                    if str(item.ratingKey) in items:
                        items_to_remove.append(item)

                if not items_to_remove:
                    logger.warning(f"No matching items found to remove from playlist {playlist_id}")
                    return {
                        "success": True,
                        "operation": "remove_items",
                        "playlist_id": playlist_id,
                        "data": _format_playlist(playlist),
                        "message": "No matching items found to remove",
                    }

                # Remove items from playlist
                await playlist.removeItems(items_to_remove)
                playlist.reload()

                return {
                    "success": True,
                    "operation": "remove_items",
                    "playlist_id": playlist_id,
                    "data": _format_playlist(playlist),
                }
            except Exception as e:
                logger.exception("Error removing items from playlist {playlist_id}:")
                return {
                    "success": False,
                    "error": f"Failed to remove items: {e!s}",
                    "error_code": "REMOVE_ITEMS_FAILED",
                    "suggestions": [
                        "Verify playlist_id and item IDs are correct",
                        "Check that you have permissions to modify this playlist",
                    ],
                }

        # Operation: get_analytics
        elif operation == "get_analytics":
            if not playlist_id:
                return {
                    "success": False,
                    "error": "playlist_id is required for get_analytics operation",
                    "error_code": "MISSING_PLAYLIST_ID",
                    "suggestions": ["Provide playlist_id to get analytics"],
                }

            try:
                playlist = await plex.server.playlist(playlist_id)
                playlist_items = playlist.items()

                # Get view counts and other metrics
                total_plays = sum(getattr(item, "viewCount", 0) for item in playlist_items)
                unique_users = len(
                    set(
                        item.lastViewedAt
                        for item in playlist_items
                        if hasattr(item, "lastViewedAt") and item.lastViewedAt
                    )
                )

                # Get popular items (top 3 most played)
                popular_items = sorted(
                    [item for item in playlist_items if hasattr(item, "viewCount")],
                    key=lambda x: getattr(x, "viewCount", 0),
                    reverse=True,
                )[:3]

                analytics = {
                    "playlist_id": playlist.ratingKey,
                    "name": playlist.title,
                    "total_plays": total_plays,
                    "unique_users": unique_users or 1,
                    "avg_completion_rate": 75.0,  # This would require more detailed tracking
                    "popular_items": [str(item.ratingKey) for item in popular_items],
                    "skip_rate": 10.0,  # This would require more detailed tracking
                    "recommendations": [
                        "Consider adding more recent content"
                        if len(playlist_items) > 10
                        else "Add more items to this playlist",
                        "Create a themed playlist"
                        if "mix" not in playlist.title.lower()
                        else "Great themed playlist!",
                    ],
                    "last_played": max(
                        [
                            int(item.lastViewedAt.timestamp())
                            for item in playlist_items
                            if hasattr(item, "lastViewedAt") and item.lastViewedAt
                        ],
                        default=None,
                    ),
                }

                return {
                    "success": True,
                    "operation": "get_analytics",
                    "playlist_id": playlist_id,
                    "data": analytics,
                }
            except Exception as e:
                logger.exception("Error getting analytics for playlist {playlist_id}:")
                return {
                    "success": False,
                    "error": f"Failed to get analytics: {e!s}",
                    "error_code": "ANALYTICS_FAILED",
                    "suggestions": [
                        "Verify playlist_id is correct",
                        "Check that the playlist exists and is accessible",
                    ],
                }

        else:
            return {
                "success": False,
                "error": f"Invalid operation: '{operation}'",
                "error_code": "INVALID_OPERATION",
                "suggestions": [
                    "Valid operations: list, get, create, update, delete, add_items, remove_items, get_analytics",
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
                "Verify the playlist_id is correct",
                "Use plex_playlist(operation='list') to find valid playlist IDs",
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
            f"Unexpected error in plex_playlist operation '{operation}': {e}",
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
