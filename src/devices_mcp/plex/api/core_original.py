"""
Core API endpoints for PlexMCP.

This module contains the core API endpoints for Plex server interaction.
"""

from typing import Any, Dict, List, Optional

# Import services (will be implemented later)
# from ..services.plex_service import PlexService
# Import the shared FastMCP instance from the app module
from ..app import mcp

# Import models
from ..models import MediaItem, MediaLibrary, PlexServerStatus


@mcp.tool()
async def get_plex_status() -> PlexServerStatus:
    """
    Get Plex server status and identity information.

    Returns comprehensive server information including version,
    platform, database size, and MyPlex connection status.

    Returns:
        Complete server status and configuration information

    Raises:
        RuntimeError: If there's an error fetching server status
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        status = await plex.get_server_status()

        return PlexServerStatus(
            name=status.get("friendlyName", "Plex Server"),
            version=status.get("version", "0.0.0"),
            platform=status.get("platform", "Unknown"),
            updated_at=status.get("updatedAt", 0),
            size=status.get("size", 0),
            my_plex_username=status.get("myPlexUsername", ""),
            my_plex_mapping_state=status.get("myPlexMappingState", ""),
            connected=status.get("myPlex", False),
        )
    except Exception as e:
        raise RuntimeError(f"Error fetching Plex server status: {e!s}") from e


@mcp.tool()
async def get_libraries() -> List[MediaLibrary]:
    """
    Get all media libraries available on the Plex server.

    Returns:
        List of all media libraries with detailed information

    Raises:
        RuntimeError: If there's an error fetching libraries from Plex server
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        libraries = await plex.list_libraries()
        return [
            MediaLibrary(
                key=str(lib.get("key", "")),
                title=lib.get("title", ""),
                type=lib.get("type", ""),
                agent=lib.get("agent", ""),
                scanner=lib.get("scanner", ""),
                language=lib.get("language", ""),
                uuid=lib.get("uuid", ""),
                created_at=lib.get("createdAt", 0),
                updated_at=lib.get("updatedAt", 0),
                count=lib.get("count", 0),
            )
            for lib in libraries
        ]
    except Exception as e:
        raise RuntimeError(f"Error fetching libraries from Plex server: {e!s}") from e


@mcp.tool()
async def search_media(query: str, library_id: Optional[str] = None) -> List[MediaItem]:
    """
    Search for media content across libraries or within specific library.

    Args:
        query: Search terms (title, actor, director, etc)
        library_id: Optional library key to search within

    Returns:
        List of matching media items with metadata

    Raises:
        RuntimeError: If there's an error searching for media
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        results = await plex.search_media(query, library_id=library_id)

        return [
            MediaItem(
                key=item.get("key", ""),
                title=item.get("title", "Unknown"),
                type=item.get("type", ""),
                year=item.get("year"),
                summary=item.get("summary", ""),
                rating=item.get("rating"),
                thumb=item.get("thumb", ""),
                art=item.get("art", ""),
                duration=item.get("duration", 0),
                added_at=item.get("addedAt", 0),
                updated_at=item.get("updatedAt", 0),
            )
            for item in results
        ]
    except Exception as e:
        raise RuntimeError(f"Error searching for media: {e!s}") from e


@mcp.tool()
async def get_recently_added(library_id: Optional[str] = None, limit: int = 20) -> List[MediaItem]:
    """
    Get recently added media from all libraries or specific library.

    Args:
        library_id: Optional library key to filter by
        limit: Maximum number of items to return (default 20)

    Returns:
        List of recently added media items

    Raises:
        RuntimeError: If there's an error fetching recently added items
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        recent_items = await plex.get_recently_added(library_id=library_id, limit=limit)

        return [
            MediaItem(
                key=item.get("key", ""),
                title=item.get("title", "Unknown"),
                type=item.get("type", ""),
                year=item.get("year"),
                summary=item.get("summary", ""),
                rating=item.get("rating"),
                thumb=item.get("thumb", ""),
                art=item.get("art", ""),
                duration=item.get("duration", 0),
                added_at=item.get("addedAt", 0),
                updated_at=item.get("updatedAt", 0),
            )
            for item in recent_items
        ]
    except Exception as e:
        raise RuntimeError(f"Error fetching recently added items: {e!s}") from e


@mcp.tool()
async def get_media_info(media_key: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific media item.

    Args:
        media_key: Plex media key/ID

    Returns:
        Detailed media information including metadata and files

    Raises:
        RuntimeError: If there's an error fetching media info
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        media_info = await plex.get_media_info(media_key)

        if not media_info:
            raise RuntimeError(f"Media item {media_key} not found")

        # Extract common media info
        result = {
            "key": media_info.get("key", ""),
            "title": media_info.get("title", "Unknown"),
            "type": media_info.get("type", ""),
            "year": media_info.get("year"),
            "summary": media_info.get("summary", ""),
            "rating": media_info.get("rating"),
            "thumb": media_info.get("thumb", ""),
            "art": media_info.get("art", ""),
            "duration": media_info.get("duration", 0),
            "added_at": media_info.get("addedAt", 0),
            "updated_at": media_info.get("updatedAt", 0),
        }

        # Add detailed metadata if available
        details = {}

        # Handle different media types
        if media_info.get("type") == "movie":
            details.update(
                {
                    "director": media_info.get("director", ""),
                    "studio": media_info.get("studio", ""),
                    "content_rating": media_info.get("contentRating", ""),
                }
            )
        elif media_info.get("type") == "episode":
            details.update(
                {
                    "show_title": media_info.get("grandparentTitle", ""),
                    "season_number": media_info.get("parentIndex", 0),
                    "episode_number": media_info.get("index", 0),
                }
            )

        # Add common details
        details.update(
            {
                "genres": media_info.get("genres", []),
                "actors": [actor.get("name", "") for actor in media_info.get("actors", [])],
                "resolution": media_info.get("media", [{}])[0].get("videoResolution", ""),
                "audio_channels": media_info.get("media", [{}])[0].get("audioChannels", 0),
                "file_size": media_info.get("media", [{}])[0].get("size", 0),
            }
        )

        result["details"] = details
        return result

    except Exception as e:
        raise RuntimeError(f"Error fetching media info: {e!s}") from e


@mcp.tool()
async def scan_library(library_id: str) -> bool:
    """
    Trigger a library scan to update content.

    Forces Plex to scan the specified library for new,
    updated, or removed media files.

    Args:
        library_id: Library key to scan

    Returns:
        True if scan was triggered successfully
    """
    # TODO: Implement actual Plex service call
    # Removed print statement - use logger instead for MCP stdio compatibility
    return True


# No need to export app - tools are registered with the shared mcp instance
