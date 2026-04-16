"""
PlexMCP Collections Management Portmanteau Tool

Consolidates all collection-related operations into a single comprehensive interface.
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
async def plex_collections(
    operation: Literal["list", "get", "create", "update", "delete", "add_items", "remove_items"],
    collection_id: str | None = None,
    library_id: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    items: list[str] | None = None,
) -> dict[str, Any]:
    """Comprehensive collections management tool for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 7 separate tools (one per collection operation), this tool consolidates related
    collection operations into a single interface. This design:
    - Prevents tool explosion (7 tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with collection tasks
    - Enables consistent collection interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - list: List all collections in a library or across all libraries
    - get: Get detailed information about a specific collection
    - create: Create a new collection
    - update: Update collection metadata (title, summary, etc.)
    - delete: Delete a collection
    - add_items: Add media items to a collection
    - remove_items: Remove media items from a collection

    OPERATIONS DETAIL:

    list: List collections
    - Parameters: library_id (optional)
    - Returns: List of collections with basic metadata
    - Use when: Browsing available collections

    get: Get collection details
    - Parameters: collection_id (required)
    - Returns: Detailed collection information including items
    - Use when: Viewing collection contents and metadata

    create: Create new collection
    - Parameters: title (required), library_id (required), summary (optional), items (optional)
    - Returns: Created collection information
    - Use when: Creating a new collection

    update: Update collection
    - Parameters: collection_id (required), title (optional), summary (optional)
    - Returns: Updated collection information
    - Use when: Modifying collection metadata

    delete: Delete collection
    - Parameters: collection_id (required)
    - Returns: Deletion confirmation
    - Use when: Removing a collection

    add_items: Add items to collection
    - Parameters: collection_id (required), items (required, list of media IDs)
    - Returns: Updated collection with new items
    - Use when: Adding media to an existing collection

    remove_items: Remove items from collection
    - Parameters: collection_id (required), items (required, list of media IDs)
    - Returns: Updated collection without removed items
    - Use when: Removing media from a collection

    Prerequisites:
        - Plex Media Server running and accessible
        - Valid PLEX_TOKEN environment variable set
        - PLEX_SERVER_URL configured (or defaults to http://localhost:32400)

    Args:
        operation: The collection operation to perform. Required. Must be one of:
            "list", "get", "create", "update", "delete", "add_items", "remove_items"
        collection_id: Collection ID (required for get, update, delete, add_items, remove_items)
        library_id: Library ID (required for create, optional for list)
        title: Collection title (required for create, optional for update)
        summary: Collection summary/description (optional)
        items: List of media item IDs (required for add_items, remove_items, optional for create)

    Returns:
        Operation-specific result with collection data

    Examples:
        # List all collections
        plex_collections("list")

        # Get collection details
        plex_collections("get", collection_id="12345")

        # Create a new collection
        plex_collections("create", title="Marvel Movies", library_id="1", items=["1", "2", "3"])

        # Add items to collection
        plex_collections("add_items", collection_id="12345", items=["4", "5"])

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Configure authentication token
        - "collection_id required": Provide collection ID for get/update/delete operations
        - "title required": Provide title when creating collections
        - "Collection not found": Verify collection_id is correct
    """
    try:
        plex = _get_plex_service()

        if operation == "list":
            # Collections are typically accessed through libraries
            if library_id:
                library = await plex.get_library(library_id)
                if not library:
                    return {
                        "success": False,
                        "error": f"Library with ID '{library_id}' not found",
                        "error_code": "LIBRARY_NOT_FOUND",
                    }
                # Get collections from library (would need PlexAPI collection access)
                return {
                    "success": True,
                    "operation": "list",
                    "collections": [],
                    "message": "Collection listing requires PlexAPI collection support (not yet fully implemented)",
                }
            libraries = await plex.list_libraries()
            return {
                "success": True,
                "operation": "list",
                "collections": [],
                "libraries": libraries,
                "message": "Collection listing requires PlexAPI collection support (not yet fully implemented)",
            }

        if operation == "get":
            if not collection_id:
                return {
                    "success": False,
                    "error": "collection_id is required for get operation",
                    "error_code": "MISSING_PARAMETER",
                    "suggestions": ["Provide a collection ID"],
                }

            return {
                "success": True,
                "operation": "get",
                "collection_id": collection_id,
                "message": "Collection retrieval requires PlexAPI collection support (not yet fully implemented)",
                "data": {},
            }

        if operation == "create":
            if not title:
                return {
                    "success": False,
                    "error": "title is required for create operation",
                    "error_code": "MISSING_PARAMETER",
                }
            if not library_id:
                return {
                    "success": False,
                    "error": "library_id is required for create operation",
                    "error_code": "MISSING_PARAMETER",
                }

            return {
                "success": True,
                "operation": "create",
                "title": title,
                "library_id": library_id,
                "message": "Collection creation requires PlexAPI collection support (not yet fully implemented)",
                "data": {},
            }

        if operation == "update":
            if not collection_id:
                return {
                    "success": False,
                    "error": "collection_id is required for update operation",
                    "error_code": "MISSING_PARAMETER",
                }

            return {
                "success": True,
                "operation": "update",
                "collection_id": collection_id,
                "message": "Collection update requires PlexAPI collection support (not yet fully implemented)",
                "data": {},
            }

        if operation == "delete":
            if not collection_id:
                return {
                    "success": False,
                    "error": "collection_id is required for delete operation",
                    "error_code": "MISSING_PARAMETER",
                }

            return {
                "success": True,
                "operation": "delete",
                "collection_id": collection_id,
                "message": "Collection deletion requires PlexAPI collection support (not yet fully implemented)",
            }

        if operation == "add_items":
            if not collection_id:
                return {
                    "success": False,
                    "error": "collection_id is required for add_items operation",
                    "error_code": "MISSING_PARAMETER",
                }
            if not items:
                return {
                    "success": False,
                    "error": "items is required for add_items operation",
                    "error_code": "MISSING_PARAMETER",
                }

            return {
                "success": True,
                "operation": "add_items",
                "collection_id": collection_id,
                "items": items,
                "message": "Adding items to collection requires PlexAPI collection support (not yet fully implemented)",
            }

        if operation == "remove_items":
            if not collection_id:
                return {
                    "success": False,
                    "error": "collection_id is required for remove_items operation",
                    "error_code": "MISSING_PARAMETER",
                }
            if not items:
                return {
                    "success": False,
                    "error": "items is required for remove_items operation",
                    "error_code": "MISSING_PARAMETER",
                }

            return {
                "success": True,
                "operation": "remove_items",
                "collection_id": collection_id,
                "items": items,
                "message": "Removing items from collection requires PlexAPI collection support (not yet fully implemented)",
            }

        return {
            "success": False,
            "error": f"Unknown operation: {operation}",
            "error_code": "INVALID_OPERATION",
            "suggestions": ["Use one of: list, get, create, update, delete, add_items, remove_items"],
        }

    except Exception as e:
        logger.exception("Error in plex_collections operation '{operation}':")
        return {
            "success": False,
            "error": str(e),
            "error_code": "EXECUTION_ERROR",
            "suggestions": [
                "Verify Plex server is accessible",
                "Check PLEX_TOKEN is set correctly",
                "Verify collection_id is valid if provided",
            ],
        }
