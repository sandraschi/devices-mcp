"""Plex library management tools for FastMCP 2.10.1."""

import logging
import os
from typing import Any

from pydantic import BaseModel, Field

from ..app import mcp
from ..models.media import LibrarySection, MediaItem

logger = logging.getLogger(__name__)


def _get_plex_service():
    from ..services.plex_service import PlexService

    base_url = os.getenv("PLEX_URL") or os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    token = os.getenv("PLEX_TOKEN")
    if not token:
        raise RuntimeError("PLEX_TOKEN environment variable is required")
    return PlexService(base_url=base_url, token=token)


class ScanLibraryRequest(BaseModel):
    """Request model for scanning a library."""

    library_id: str = Field(..., description="ID of the library to scan")
    force: bool = Field(False, description="Force a full scan")


@mcp.tool()
async def scan_library(request: ScanLibraryRequest) -> dict[str, Any]:
    """Scan a library for new or updated files.

    Args:
        request: Scan parameters

    Returns:
        Dictionary with scan results
    """
    plex = _get_plex_service()
    try:
        result = await plex.scan_library(library_id=request.library_id, force=request.force)
        logger.info(f"Successfully scanned library {request.library_id} (force={request.force})")
        return result
    except Exception:
        logger.exception("Error scanning library {request.library_id}:")
        raise


class RefreshLibraryRequest(BaseModel):
    """Request model for refreshing a library."""

    library_id: str = Field(..., description="ID of the library to refresh")


@mcp.tool()
async def refresh_library(request: RefreshLibraryRequest) -> bool:
    """Refresh metadata for a library.

    Args:
        request: Refresh parameters

    Returns:
        True if refresh was successful, False otherwise
    """
    plex = _get_plex_service()
    try:
        success = await plex.refresh_library_metadata(library_id=request.library_id)
        if success:
            logger.info(f"Successfully refreshed metadata for library {request.library_id}")
        else:
            logger.warning(f"Failed to refresh metadata for library {request.library_id}")
        return success
    except Exception:
        logger.exception("Error refreshing library {request.library_id}:")
        return False


class OptimizeLibraryRequest(BaseModel):
    """Request model for optimizing a library."""

    library_id: str = Field(..., description="ID of the library to optimize")


@mcp.tool()
async def optimize_library(request: OptimizeLibraryRequest) -> bool:
    """Optimize a library database.

    Args:
        request: Optimization parameters

    Returns:
        True if optimization was successful, False otherwise
    """
    plex = _get_plex_service()
    try:
        success = await plex.optimize_library(library_id=request.library_id)
        if success:
            logger.info(f"Successfully optimized library {request.library_id}")
        else:
            logger.warning(f"Failed to optimize library {request.library_id}")
        return success
    except Exception:
        logger.exception("Error optimizing library {request.library_id}:")
        return False


class GetLibraryRequest(BaseModel):
    """Request model for getting library information."""

    library_id: str = Field(..., description="ID of the library to retrieve")


@mcp.tool()
async def get_library(request: GetLibraryRequest) -> LibrarySection | None:
    """Get information about a specific library.

    Args:
        request: Library retrieval parameters

    Returns:
        Library information if found, None otherwise
    """
    plex = _get_plex_service()
    try:
        library = await plex.get_library(library_id=request.library_id)
        if not library:
            logger.warning(f"Library {request.library_id} not found")
            return None
        return LibrarySection(**library)
    except Exception:
        logger.exception("Error getting library {request.library_id}:")
        return None


@mcp.tool()
async def list_libraries() -> list[LibrarySection]:
    """List all libraries.

    Returns:
        List of all libraries

    Raises:
        RuntimeError: If there's an error fetching libraries from Plex server
    """
    plex = _get_plex_service()
    try:
        libraries = await plex.list_libraries()
        if not libraries:
            raise RuntimeError("No libraries found on Plex server")
        return [LibrarySection(**lib) for lib in libraries]
    except Exception as e:
        error_msg = f"Failed to list libraries: {e!s}"
        logger.exception(error_msg)
        raise RuntimeError(error_msg) from e


class AddLibraryRequest(BaseModel):
    """Request model for adding a new library."""

    name: str = Field(..., description="Name of the new library")
    type: str = Field(..., description="Type of library (movie, show, music, photo)")
    agent: str = Field(..., description="Metadata agent to use")
    scanner: str = Field(..., description="Scanner to use")
    language: str = Field("en", description="Language for metadata")
    location: str = Field(..., description="Path to the library content")
    thumb: str | None = Field(None, description="URL to a thumbnail image")


@mcp.tool()
async def add_library(request: AddLibraryRequest) -> LibrarySection | None:
    """Add a new library.

    Args:
        request: Library creation parameters

    Returns:
        The created library information if successful, None otherwise
    """
    plex = _get_plex_service()
    return await plex.add_library(
        name=request.name,
        type=request.type,
        agent=request.agent,
        scanner=request.scanner,
        language=request.language,
        location=request.location,
        thumb=request.thumb,
    )


class UpdateLibraryRequest(BaseModel):
    """Request model for updating a library."""

    library_id: str = Field(..., description="ID of the library to update")
    name: str | None = Field(None, description="New name for the library")
    agent: str | None = Field(None, description="New metadata agent")
    scanner: str | None = Field(None, description="New scanner")
    language: str | None = Field(None, description="New language for metadata")
    thumb: str | None = Field(None, description="New thumbnail URL")


@mcp.tool()
async def update_library(request: UpdateLibraryRequest) -> LibrarySection | None:
    """Update a library's settings.

    Args:
        request: Library update parameters

    Returns:
        The updated library information if successful, None otherwise
    """
    plex = _get_plex_service()
    return await plex.update_library(
        library_id=request.library_id,
        name=request.name,
        agent=request.agent,
        scanner=request.scanner,
        language=request.language,
        thumb=request.thumb,
    )


class DeleteLibraryRequest(BaseModel):
    """Request model for deleting a library."""

    library_id: str = Field(..., description="ID of the library to delete")


@mcp.tool()
async def delete_library(request: DeleteLibraryRequest) -> bool:
    """Delete a library.

    Args:
        request: Library deletion parameters

    Returns:
        True if deletion was successful, False otherwise
    """
    plex = _get_plex_service()
    return await plex.delete_library(library_id=request.library_id)


class AddLibraryLocationRequest(BaseModel):
    """Request model for adding a location to a library."""

    library_id: str = Field(..., description="ID of the library")
    path: str = Field(..., description="Path to add to the library")


@mcp.tool()
async def add_library_location(request: AddLibraryLocationRequest) -> bool:
    """Add a location to a library.

    Args:
        request: Location addition parameters

    Returns:
        True if addition was successful, False otherwise
    """
    plex = _get_plex_service()
    return await plex.add_library_location(library_id=request.library_id, path=request.path)


class RemoveLibraryLocationRequest(BaseModel):
    """Request model for removing a location from a library."""

    library_id: str = Field(..., description="ID of the library")
    path: str = Field(..., description="Path to remove from the library")


@mcp.tool()
async def remove_library_location(request: RemoveLibraryLocationRequest) -> bool:
    """Remove a location from a library.

    Args:
        request: Location removal parameters

    Returns:
        True if removal was successful, False otherwise
    """
    plex = _get_plex_service()
    return await plex.remove_library_location(library_id=request.library_id, path=request.path)


class GetLibraryItemsRequest(BaseModel):
    """Request model for getting library items."""

    library_id: str = Field(..., description="ID of the library")
    limit: int = Field(100, description="Maximum number of items to return")
    offset: int = Field(0, description="Offset for pagination")
    sort: str | None = Field(None, description="Sort field")
    filter: dict[str, Any] | None = Field(None, description="Filter criteria")


@mcp.tool()
async def get_library_items(request: GetLibraryItemsRequest) -> list[MediaItem]:
    """Get items from a library.

    Args:
        request: Item retrieval parameters

    Returns:
        List of media items in the library
    """
    plex = _get_plex_service()
    return await plex.get_library_items(
        library_id=request.library_id,
        limit=request.limit,
        offset=request.offset,
        sort=request.sort,
        filter=request.filter,
    )


class EmptyTrashRequest(BaseModel):
    """Request model for emptying the trash."""

    library_id: str = Field(..., description="ID of the library")


@mcp.tool()
async def empty_trash(request: EmptyTrashRequest) -> bool:
    """Empty the trash for a library.

    Args:
        request: Empty trash parameters

    Returns:
        True if successful, False otherwise
    """
    plex = _get_plex_service()
    return await plex.empty_library_trash(library_id=request.library_id)


class CleanBundlesRequest(BaseModel):
    """Request model for cleaning bundles."""

    library_id: str | None = Field(None, description="ID of the library (optional)")


@mcp.tool()
async def clean_bundles(request: CleanBundlesRequest) -> dict[str, Any]:
    """Clean old bundles for a library or all libraries.

    Args:
        request: Clean bundles parameters

    Returns:
        Dictionary with cleanup results
    """
    plex = _get_plex_service()
    return await plex.clean_library_bundles(library_id=request.library_id)
