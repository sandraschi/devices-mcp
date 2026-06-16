"""
PlexMCP Library Management Portmanteau Tool

Consolidates all library-related operations into a single comprehensive interface.
FastMCP 3.1 compliant with conversational tool returns and sampling capabilities.
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
async def plex_library(
    operation: Literal[
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
    library_id: str | None = None,
    name: str | None = None,
    library_type: Literal["movie", "show", "music", "photo"] | None = None,
    path: str | None = None,
    agent: str | None = None,
    scanner: str | None = None,
    language: str | None = "en",
    thumb: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Comprehensive library management operations for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 12+ separate tools (one per operation), this tool consolidates related
    library management operations into a single interface. This design:
    - Prevents tool explosion (12+ tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with library management tasks
    - Enables consistent library interface across all operations
    - Follows FastMCP 3.1+ best practices with conversational returns and sampling

    SUPPORTED OPERATIONS:
    - list: List all media libraries
    - get: Get detailed information about a specific library
    - create: Create a new media library
    - update: Update library settings
    - delete: Delete a library
    - scan: Scan library for new/changed media
    - refresh: Refresh all metadata for library
    - optimize: Optimize library database
    - empty_trash: Empty library trash
    - add_location: Add a location to a library
    - remove_location: Remove a location from a library
    - clean_bundles: Clean old bundles for a library or all libraries

    OPERATIONS DETAIL:

    list: List all media libraries
    - Parameters: None required
    - Returns: List of all libraries with metadata
    - Example: plex_library(operation="list")
    - Use when: You want to see all available libraries

    get: Get detailed information about a specific library
    - Parameters: library_id (required)
    - Returns: Detailed library information
    - Example: plex_library(operation="get", library_id="1")
    - Use when: You need details about a specific library

    create: Create a new media library
    - Parameters: name (required), library_type (required), path (required), agent (optional), scanner (optional), language (optional)
    - Returns: Created library details or instructions if not supported
    - Example: plex_library(operation="create", name="Movies", library_type="movie", path="/media/movies")
    - Use when: Setting up a new library
    - Note: Plex API may not support programmatic library creation - may return instructions

    update: Update library settings
    - Parameters: library_id (required), name (optional), agent (optional), scanner (optional), language (optional), thumb (optional)
    - Returns: Updated library confirmation
    - Example: plex_library(operation="update", library_id="1", name="4K Movies")
    - Use when: Changing library configuration

    delete: Delete a library
    - Parameters: library_id (required)
    - Returns: Deletion confirmation
    - Example: plex_library(operation="delete", library_id="1")
    - Use when: Removing a library (WARNING: Cannot be undone)

    scan: Scan library for new/changed media
    - Parameters: library_id (required), force (optional, default: False)
    - Returns: Scan status
    - Example: plex_library(operation="scan", library_id="1", force=True)
    - Use when: You've added new media files

    refresh: Refresh all metadata for library
    - Parameters: library_id (required)
    - Returns: Refresh status
    - Example: plex_library(operation="refresh", library_id="1")
    - Use when: Metadata needs updating

    optimize: Optimize library database
    - Parameters: library_id (required)
    - Returns: Optimization status
    - Example: plex_library(operation="optimize", library_id="1")
    - Use when: Library performance is slow

    empty_trash: Empty library trash
    - Parameters: library_id (required)
    - Returns: Trash empty confirmation
    - Example: plex_library(operation="empty_trash", library_id="1")
    - Use when: Cleaning up deleted items

    add_location: Add a location to a library
    - Parameters: library_id (required), path (required)
    - Returns: Success confirmation
    - Example: plex_library(operation="add_location", library_id="1", path="/media/new-location")
    - Use when: Adding a new media folder to an existing library

    remove_location: Remove a location from a library
    - Parameters: library_id (required), path (required)
    - Returns: Success confirmation
    - Example: plex_library(operation="remove_location", library_id="1", path="/media/old-location")
    - Use when: Removing a media folder from a library

    clean_bundles: Clean old bundles for a library or all libraries
    - Parameters: library_id (optional - if not provided, cleans all libraries)
    - Returns: Cleanup results
    - Example: plex_library(operation="clean_bundles", library_id="1")
    - Use when: Freeing up disk space by removing old bundle files

    Prerequisites:
        - Plex Media Server running and accessible
        - Valid PLEX_TOKEN environment variable set
        - Admin/owner permissions for create/update/delete operations
        - Valid media paths for create/add_location operations

    Args:
        operation (str): The library operation to perform. Required. Must be one of: "list", "get", "create", "update", "delete", "scan", "refresh", "optimize", "empty_trash", "add_location", "remove_location", "clean_bundles"
        library_id (str | None): Library identifier. Required for: get, create, update, delete, scan, refresh, optimize, empty_trash, add_location, remove_location. Optional for: clean_bundles.
        name (str | None): Library name. Required for: create. Optional for: update.
        library_type (str | None): Library type. Required for: create. Valid: "movie", "show", "music", "photo".
        path (str | None): Media folder path. Required for: create, add_location, remove_location. Optional for: update.
        agent (str | None): Metadata agent. Optional for: create, update.
        scanner (str | None): Media scanner. Optional for: create, update.
        language (str): Library language code. Default: "en". Optional for: create, update.
        thumb (str | None): Thumbnail URL. Optional for: create, update.
        force (bool): Force operation. Optional for: scan. Default: False. If True, forces a full scan.

    Returns:
        Dictionary following FastMCP 3.1 conversational response patterns:
        ```json
        {
          "success": true,
          "operation": "list",
          "message": "Successfully retrieved 3 media libraries from your Plex server",
          "data": [...],
          "count": 3,
          "next_steps": ["Use 'plex_library get' to see details", "Use 'plex_media' to browse content"]
        }
        ```

        **Success Response Structure:**
        - success (bool): Operation success status
        - operation (str): Library operation that was performed
        - message (str): Conversational response for natural AI interaction
        - data: Operation-specific result data
        - count: Number of items returned (for list operation)
        - next_steps: List of suggested next actions
        - error: Error message if success is False
        - error_code: Specific error code for programmatic handling
        - suggestions: List of suggested fixes (on error)

    Examples:
        # List all libraries
        result = await plex_library(operation="list")
        # Returns: {'success': True, 'operation': 'list', 'data': [...], 'count': 5}

        # Get library details
        result = await plex_library(operation="get", library_id="1")
        # Returns: {'success': True, 'operation': 'get', 'data': {...}}

        # Create new library
        result = await plex_library(
            operation="create",
            name="4K Movies",
            library_type="movie",
            path="/media/4k-movies"
        )
        # Returns: {'success': True, 'operation': 'create', 'data': {...}}

        # Update library
        result = await plex_library(operation="update", library_id="1", name="4K Movies")
        # Returns: {'success': True, 'operation': 'update', 'data': {...}}

        # Scan library
        result = await plex_library(operation="scan", library_id="1", force=True)
        # Returns: {'success': True, 'operation': 'scan', 'scan_started': True}

        # Add location to library
        result = await plex_library(operation="add_location", library_id="1", path="/media/new-folder")
        # Returns: {'success': True, 'operation': 'add_location'}

        # Clean bundles
        result = await plex_library(operation="clean_bundles", library_id="1")
        # Returns: {'success': True, 'operation': 'clean_bundles', 'data': {'cleaned': True}}

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Set PLEX_TOKEN environment variable with your auth token
        - "library_id required": Provide valid library ID for operations that require it
        - "Library not found": Use plex_library(operation="list") to find valid library IDs
        - "Permission denied": Admin access required for create/update/delete operations
        - "Invalid path": Media path doesn't exist or isn't accessible
        - "Operation not supported": Some operations may not be fully supported by Plex API

    See Also:
        - plex_media: For browsing and searching library contents
        - plex_metadata: For individual item metadata operations
        - plex_performance: For database optimization and performance
    """
    try:
        plex = _get_plex_service()

        # Operation: list
        if operation == "list":
            libraries = await plex.get_libraries()
            return {
                "success": True,
                "operation": "list",
                "data": libraries,
                "count": len(libraries),
            }

        # Operation: get
        if operation == "get":
            if not library_id:
                return {
                    "success": False,
                    "message": "library_id is required for get operation",
                    "error": "library_id is required for get operation",
                    "error_code": "MISSING_LIBRARY_ID",
                    "suggestions": ["Use plex_library('list') to find available library IDs"],
                }

            library = await plex.get_library(library_id)
            if library is None:
                return {
                    "success": False,
                    "message": f"Library {library_id} not found",
                    "error_code": "LIBRARY_NOT_FOUND",
                    "suggestions": [
                        "Use plex_library(operation='list') to find available library IDs",
                        "Verify the library_id is correct",
                    ],
                }
            return {"success": True, "operation": "get", "data": library}

        # Operation: scan
        if operation == "scan":
            if not library_id:
                return {
                    "success": False,
                    "message": "library_id is required for scan operation",
                    "error": "library_id is required for scan operation",
                    "error_code": "MISSING_LIBRARY_ID",
                    "suggestions": ["Provide library_id to scan"],
                }

            result = await plex.scan_library(library_id, force=force)
            return {
                "success": result.get("scan_successful", False),
                "message": result.get("message", "Scan completed"),
                "next_steps": result.get("next_steps", []),
                "operation": "scan",
                "library_id": library_id,
                "force": force,
                "data": result,
            }

        # Operation: refresh
        if operation == "refresh":
            if not library_id:
                return {
                    "success": False,
                    "message": "library_id is required for refresh operation",
                    "error": "library_id is required for refresh operation",
                    "error_code": "MISSING_LIBRARY_ID",
                    "suggestions": ["Provide library_id to refresh"],
                }

            result = await plex.refresh_library_metadata(library_id)
            return {
                "success": result,
                "operation": "refresh",
                "library_id": library_id,
                "data": {"refreshed": result},
            }

        # Operation: empty_trash
        if operation == "empty_trash":
            if not library_id:
                return {
                    "success": False,
                    "message": "library_id is required for empty_trash operation",
                    "error": "library_id is required for empty_trash operation",
                    "error_code": "MISSING_LIBRARY_ID",
                    "suggestions": ["Provide library_id to empty trash"],
                }

            result = await plex.empty_trash(library_id)
            return {
                "success": result,
                "operation": "empty_trash",
                "library_id": library_id,
                "data": {"trash_emptied": result},
            }

        # Operation: create
        if operation == "create":
            if not name:
                return {
                    "success": False,
                    "message": "name is required for create operation",
                    "error": "name is required for create operation",
                    "error_code": "MISSING_NAME",
                    "suggestions": ["Provide name parameter for the new library"],
                }
            if not library_type:
                return {
                    "success": False,
                    "message": "library_type is required for create operation",
                    "error": "library_type is required for create operation",
                    "error_code": "MISSING_LIBRARY_TYPE",
                    "suggestions": ["Provide library_type: movie, show, music, or photo"],
                }
            if not path:
                return {
                    "success": False,
                    "message": "path is required for create operation",
                    "error": "path is required for create operation",
                    "error_code": "MISSING_PATH",
                    "suggestions": ["Provide path parameter for the media folder"],
                }

            result = await plex.add_library(
                name=name,
                libtype=library_type,
                agent=agent or "com.plexapp.agents.imdb",
                scanner=scanner or "Plex Movie Scanner",
                language=language or "en",
                location=path,
                thumb=thumb,
            )
            if result is None:
                return {
                    "success": False,
                    "message": "Library creation not fully supported via Plex API",
                    "error": "Library creation not fully supported via Plex API",
                    "error_code": "NOT_SUPPORTED",
                    "suggestions": [
                        "Use Plex Web App to create libraries manually",
                        "The Plex API has limited support for programmatic library creation",
                    ],
                }
            return {
                "success": True,
                "operation": "create",
                "data": result,
            }

        # Operation: update
        if operation == "update":
            if not library_id:
                return {
                    "success": False,
                    "message": "library_id is required for update operation",
                    "error": "library_id is required for update operation",
                    "error_code": "MISSING_LIBRARY_ID",
                    "suggestions": ["Provide library_id to update"],
                }

            update_kwargs = {}
            if name:
                update_kwargs["name"] = name
            if agent:
                update_kwargs["agent"] = agent
            if scanner:
                update_kwargs["scanner"] = scanner
            if language:
                update_kwargs["language"] = language
            if thumb:
                update_kwargs["thumb"] = thumb

            if not update_kwargs:
                return {
                    "success": False,
                    "message": "At least one update field (name, agent, scanner, language, thumb) is required",
                    "error": "At least one update field (name, agent, scanner, language, thumb) is required",
                    "error_code": "MISSING_UPDATE_FIELDS",
                    "suggestions": ["Provide at least one field to update"],
                }

            result = await plex.update_library(library_id, **update_kwargs)
            if result is None:
                return {
                    "success": False,
                    "message": f"Failed to update library {library_id}",
                    "error_code": "UPDATE_FAILED",
                    "suggestions": [
                        "Verify library_id is correct",
                        "Check that you have admin permissions",
                        "Verify the library exists",
                    ],
                }
            return {
                "success": True,
                "operation": "update",
                "library_id": library_id,
                "data": result,
            }

        # Operation: delete
        if operation == "delete":
            if not library_id:
                return {
                    "success": False,
                    "message": "library_id is required for delete operation",
                    "error": "library_id is required for delete operation",
                    "error_code": "MISSING_LIBRARY_ID",
                    "suggestions": ["Provide library_id to delete"],
                }

            result = await plex.delete_library(library_id)
            return {
                "success": result,
                "operation": "delete",
                "library_id": library_id,
                "data": {"deleted": result},
            }

        # Operation: optimize
        if operation == "optimize":
            if not library_id:
                return {
                    "success": False,
                    "message": "library_id is required for optimize operation",
                    "error": "library_id is required for optimize operation",
                    "error_code": "MISSING_LIBRARY_ID",
                    "suggestions": ["Provide library_id to optimize"],
                }

            result = await plex.optimize_library(library_id)
            return {
                "success": result,
                "operation": "optimize",
                "library_id": library_id,
                "data": {"optimized": result},
            }

        # Operation: add_location
        if operation == "add_location":
            if not library_id:
                return {
                    "success": False,
                    "message": "library_id is required for add_location operation",
                    "error": "library_id is required for add_location operation",
                    "error_code": "MISSING_LIBRARY_ID",
                    "suggestions": ["Provide library_id to add location"],
                }
            if not path:
                return {
                    "success": False,
                    "message": "path is required for add_location operation",
                    "error": "path is required for add_location operation",
                    "error_code": "MISSING_PATH",
                    "suggestions": ["Provide path parameter for the new location"],
                }

            result = await plex.add_library_location(library_id, path)
            return {
                "success": result,
                "operation": "add_location",
                "library_id": library_id,
                "path": path,
                "data": {"location_added": result},
            }

        # Operation: remove_location
        if operation == "remove_location":
            if not library_id:
                return {
                    "success": False,
                    "message": "library_id is required for remove_location operation",
                    "error": "library_id is required for remove_location operation",
                    "error_code": "MISSING_LIBRARY_ID",
                    "suggestions": ["Provide library_id to remove location"],
                }
            if not path:
                return {
                    "success": False,
                    "message": "path is required for remove_location operation",
                    "error": "path is required for remove_location operation",
                    "error_code": "MISSING_PATH",
                    "suggestions": ["Provide path parameter for the location to remove"],
                }

            result = await plex.remove_library_location(library_id, path)
            return {
                "success": result,
                "operation": "remove_location",
                "library_id": library_id,
                "path": path,
                "data": {"location_removed": result},
            }

        # Operation: clean_bundles
        if operation == "clean_bundles":
            result = await plex.clean_bundles(library_id=library_id)
            return {
                "success": result.get("cleaned", False),
                "message": result.get("message", "Clean bundles completed"),
                "next_steps": result.get("next_steps", []),
                "operation": "clean_bundles",
                "library_id": library_id,
                "data": result,
            }

        return {
            "success": False,
            "message": f"Invalid operation: '{operation}'",
            "error_code": "INVALID_OPERATION",
            "suggestions": [
                "Valid operations: list, get, create, update, delete, scan, refresh, optimize, empty_trash, add_location, remove_location, clean_bundles",
                f"You provided: '{operation}'",
            ],
        }

    except Exception as e:
        logger.exception("Error in plex_library operation '{operation}':")
        return {
            "success": False,
            "message": str(e),
            "error": str(e),
            "error_code": "EXECUTION_ERROR",
            "operation": operation,
            "suggestions": [
                "Check Plex server is running and accessible",
                "Verify PLEX_TOKEN is valid",
                "Check server logs for detailed error information",
            ],
        }
