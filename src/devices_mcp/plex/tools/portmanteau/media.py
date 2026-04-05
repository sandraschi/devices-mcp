"""
PlexMCP Media Management Portmanteau Tool

Consolidates all media-related operations into a single comprehensive interface.
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
async def plex_media(
    operation: Literal["browse", "search", "get_details", "get_recent", "update_metadata"],
    library_id: Optional[str] = None,
    media_key: Optional[str] = None,
    query: Optional[str] = None,
    media_type: Optional[str] = None,
    limit: int = 100,
    genre: Optional[str] = None,
    year: Optional[int] = None,
    actor: Optional[str] = None,
    director: Optional[str] = None,
    min_rating: Optional[float] = None,
    unwatched: Optional[bool] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Comprehensive media management operations for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 5+ separate tools (one per operation), this tool consolidates related
    media operations into a single interface. This design:
    - Prevents tool explosion (5+ tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with media management tasks
    - Enables consistent media interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - browse: Browse library contents with optional filtering
    - search: Advanced search across libraries with multiple filters
    - get_details: Get comprehensive details about a specific media item
    - get_recent: Get recently added media items
    - update_metadata: Update metadata for a media item

    OPERATIONS DETAIL:

    browse: Browse library contents with optional filtering
    - Parameters: library_id (required), limit (optional), media_type (optional)
    - Returns: List of media items from specified library
    - Example: plex_media("browse", library_id="1", limit=50)
    - Use when: You want to browse a specific library's contents

    search: Advanced search across libraries with multiple filters
    - Parameters: query (optional), library_id (optional), media_type, genre, year, actor, director, min_rating, unwatched, limit
    - Returns: List of media items matching search criteria
    - Example: plex_media("search", query="Inception", genre="Sci-Fi", min_rating=8.0)
    - Use when: You need to find specific content with criteria

    get_details: Get comprehensive details about a specific media item
    - Parameters: media_key (required)
    - Returns: Detailed media information including metadata, cast, files
    - Example: plex_media("get_details", media_key="12345")
    - Use when: You need full information about a specific item

    get_recent: Get recently added media items
    - Parameters: library_id (optional), limit (optional)
    - Returns: List of recently added media items
    - Example: plex_media("get_recent", limit=20)
    - Use when: You want to see what's new in your library

    update_metadata: Update metadata for a media item
    - Parameters: media_key (required), metadata (required)
    - Returns: Success confirmation with updated metadata
    - Example: plex_media("update_metadata", media_key="12345", metadata={"title": "New Title"})
    - Use when: You need to correct or enhance media information

    Prerequisites:
        - Plex Media Server running and accessible
        - Valid PLEX_TOKEN environment variable set
        - PLEX_SERVER_URL configured (or defaults to http://localhost:32400)
        - At least one media library configured in Plex

    Args:
        operation (str): The media operation to perform. Required. Must be one of: "browse", "search", "get_details", "get_recent", "update_metadata"
        library_id (str | None): Library identifier. Required for: browse. Optional for: search, get_recent. Use plex_library("list") to find IDs.
        media_key (str | None): Media item key/ID. Required for: get_details, update_metadata. Obtained from browse/search results.
        query (str | None): Search query text. Optional for: search. Searches title, description, tags, etc.
        media_type (str | None): Media type filter. Optional for: browse, search. Valid: "movie", "show", "episode", "album", "track", "photo".
        limit (int): Maximum results to return (1-1000). Default: 100. Optional for: browse, search, get_recent.
        genre (str | None): Genre filter. Optional for: search. Examples: "Action", "Comedy", "Drama", "Sci-Fi".
        year (int | None): Year filter. Optional for: search. Can be single year or list.
        actor (str | None): Actor name filter. Optional for: search.
        director (str | None): Director name filter. Optional for: search.
        min_rating (float | None): Minimum rating filter (0-10). Optional for: search.
        unwatched (bool | None): Unwatched items only filter. Optional for: search.
        metadata (dict | None): Metadata updates. Required for: update_metadata. Dictionary with fields to update.

    Returns:
        Dictionary containing:
            - success: Boolean indicating operation success
            - operation: The operation that was performed
            - data: Operation-specific result data
                - For browse/search/get_recent: List of MediaItem objects
                - For get_details: Detailed media information dictionary
                - For update_metadata: Updated metadata confirmation
            - count: Number of items returned (for browse/search/get_recent)
            - error: Error message if success is False
            - error_code: Specific error code for programmatic handling
            - suggestions: List of suggested fixes (on error)

    Usage:
        This tool is the primary interface for all media-related operations in PlexMCP.
        It uses the portmanteau pattern to consolidate related operations, making it
        easier to discover and use media functionality.

        Common scenarios:
        - Browse a movie library to see all available films
        - Search for specific content using multiple filters
        - Get detailed information for a specific movie/show
        - Check what was recently added to your libraries
        - Update incorrect or missing metadata

    Examples:
        # Browse movie library
        result = await plex_media("browse", library_id="1", limit=50)
        # Returns: {'success': True, 'data': [...], 'count': 50}

        # Advanced search with multiple criteria
        result = await plex_media(
            operation="search",
            query="star wars",
            genre="Sci-Fi",
            min_rating=7.0,
            year=2015,
            limit=10
        )
        # Returns: {'success': True, 'data': [...], 'count': 10}

        # Get detailed information
        result = await plex_media("get_details", media_key="12345")
        # Returns: {'success': True, 'data': {...}}

        # Get recently added items
        result = await plex_media("get_recent", limit=20)
        # Returns: {'success': True, 'data': [...], 'count': 20}

        # Update metadata
        result = await plex_media(
            operation="update_metadata",
            media_key="12345",
            metadata={"title": "Corrected Title", "year": 2020}
        )
        # Returns: {'success': True, 'data': {...}}

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Set PLEX_TOKEN environment variable with your auth token
        - "Library not found": Use plex_library("list") to find valid library IDs
        - "Media item not found": Verify media_key is correct from browse/search results
        - "Connection failed": Check PLEX_SERVER_URL and ensure server is running
        - "Invalid operation": Operation must be one of the 5 supported operations
        - "Missing required parameter": Each operation has specific required parameters

    See Also:
        - plex_library: For library management operations
        - plex_search: For advanced search-only operations
        - plex_metadata: For bulk metadata operations
    """
    try:
        plex = _get_plex_service()

        # Operation: browse
        if operation == "browse":
            if not library_id:
                return {
                    "success": False,
                    "error": "library_id is required for browse operation",
                    "error_code": "MISSING_LIBRARY_ID",
                    "suggestions": [
                        "Use plex_library('list') to find available library IDs",
                        "Provide library_id parameter: plex_media('browse', library_id='1')",
                    ],
                    "related_tools": ["plex_library"],
                }

            items = await plex.get_library_items(library_id, limit=limit)
            return {
                "success": True,
                "operation": "browse",
                "data": [item.dict() for item in items] if hasattr(items[0], "dict") else items,
                "count": len(items),
            }

        # Operation: search
        if operation == "search":
            search_params = {
                "query": query,
                "library_id": library_id,
                "media_type": media_type,
                "genre": genre,
                "year": year,
                "actor": actor,
                "director": director,
                "min_rating": min_rating,
                "unwatched": unwatched,
                "limit": min(1000, max(1, limit)),
            }

            # Remove None values
            search_params = {k: v for k, v in search_params.items() if v is not None}

            items = await plex.search_media(**search_params)
            return {
                "success": True,
                "operation": "search",
                "data": [item.dict() if hasattr(item, "dict") else item for item in items],
                "count": len(items),
                "search_criteria": search_params,
            }

        # Operation: get_details
        if operation == "get_details":
            if not media_key:
                return {
                    "success": False,
                    "error": "media_key is required for get_details operation",
                    "error_code": "MISSING_MEDIA_KEY",
                    "suggestions": [
                        "Get media_key from browse or search results",
                        "Example: plex_media('get_details', media_key='12345')",
                    ],
                    "related_tools": ["plex_media with browse or search operation"],
                }

            details = await plex.get_media_info(media_key)
            return {"success": True, "operation": "get_details", "data": details}

        # Operation: get_recent
        if operation == "get_recent":
            items = await plex.get_recently_added(library_id=library_id, limit=limit)
            return {
                "success": True,
                "operation": "get_recent",
                "data": [item.dict() if hasattr(item, "dict") else item for item in items],
                "count": len(items),
            }

        # Operation: update_metadata
        if operation == "update_metadata":
            if not media_key:
                return {
                    "success": False,
                    "error": "media_key is required for update_metadata operation",
                    "error_code": "MISSING_MEDIA_KEY",
                    "suggestions": ["Get media_key from browse or search results"],
                }

            if not metadata:
                return {
                    "success": False,
                    "error": "metadata dictionary is required for update_metadata operation",
                    "error_code": "MISSING_METADATA",
                    "suggestions": [
                        "Provide metadata dict: {'title': 'New Title', 'year': 2020}",
                        "Available fields: title, year, summary, rating, genres, etc.",
                    ],
                }

            # Update metadata via plex service
            updated = await plex.update_media_metadata(media_key, metadata)
            return {
                "success": True,
                "operation": "update_metadata",
                "data": updated,
                "media_key": media_key,
                "updated_fields": list(metadata.keys()),
            }

        return {
            "success": False,
            "error": f"Invalid operation: '{operation}'",
            "error_code": "INVALID_OPERATION",
            "suggestions": [
                "Valid operations: browse, search, get_details, get_recent, update_metadata",
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
                "Verify the ID/key is correct",
                "Use plex_media('browse') or plex_media('search') to find valid items",
                "Check that the library/item still exists",
            ]
        elif "connection" in error_msg.lower():
            suggestions = [
                "Verify Plex Media Server is running",
                "Check PLEX_SERVER_URL is correct (default: http://localhost:32400)",
                "Test server access in web browser",
            ]

        return {
            "success": False,
            "error": error_msg,
            "error_code": "RUNTIME_ERROR",
            "operation": operation,
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.exception("Unexpected error in plex_media operation '{operation}':")
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
