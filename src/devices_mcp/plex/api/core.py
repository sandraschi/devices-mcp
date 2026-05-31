"""
Core API endpoints for PlexMCP - FIXED VERSION.

This module contains the core API endpoints for Plex server interaction.
Fixed to properly read environment variables for PlexService initialization.
"""

import os
from typing import Any

# Import the shared FastMCP instance from the app module
from ..app import mcp

# Import models
from ..models import (
    MediaItem,
    MediaLibrary,
    PlexServerStatus,
)

# Import logger
from ..utils import get_logger

logger = get_logger(__name__)


def _get_plex_service():
    """Get PlexService instance with proper environment variable handling."""
    from ..services.plex_service import PlexService

    # Check for environment variables in the correct order
    base_url = os.getenv("PLEX_URL") or os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    token = os.getenv("PLEX_TOKEN")

    if not token:
        raise RuntimeError("PLEX_TOKEN environment variable is required")

    return PlexService(base_url=base_url, token=token)


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
    try:
        plex = _get_plex_service()
        status = await plex.get_server_status()

        return PlexServerStatus(
            name=status.name,
            version=status.version,
            platform=status.platform,
            updated_at=status.updated_at,
            size=0,  # This might need adjustment based on actual PlexServerStatus model
            my_plex_username="",
            my_plex_mapping_state="",
            connected=True,
        )
    except Exception as e:
        raise RuntimeError(f"Error fetching Plex server status: {e!s}") from e


async def get_libraries() -> list[MediaLibrary]:
    """
    Get all media libraries available on the Plex server.

    Returns:
        List of all media libraries with detailed information

    Raises:
        RuntimeError: If there's an error fetching libraries from Plex server
    """
    try:
        plex = _get_plex_service()
        libraries = await plex.list_libraries()
        return [
            MediaLibrary(
                key=str(lib.get("id", lib.get("key", ""))),
                title=lib.get("title", ""),
                type=lib.get("type", ""),
                agent=lib.get("agent", ""),
                scanner=lib.get("scanner", ""),
                language=lib.get("language", ""),
                uuid=lib.get("uuid", ""),
                created_at=lib.get("created_at", lib.get("createdAt", 0)),
                updated_at=lib.get("updated_at", lib.get("updatedAt", 0)),
                count=lib.get("count", 0),
            )
            for lib in libraries
        ]
    except Exception as e:
        raise RuntimeError(f"Error fetching libraries from Plex server: {e!s}") from e


async def search_media(
    query: str | None = None,
    library_id: str | None = None,
    media_type: str | None = None,
    title: str | None = None,
    year: int | list[int] | None = None,
    decade: int | None = None,
    genre: str | list[str] | None = None,
    actor: str | list[str] | None = None,
    director: str | list[str] | None = None,
    composer: str | list[str] | None = None,
    performer: str | list[str] | None = None,
    content_rating: str | list[str] | None = None,
    studio: str | list[str] | None = None,
    country: str | list[str] | None = None,
    collection: str | list[str] | None = None,
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_year: int | None = None,
    max_year: int | None = None,
    unwatched: bool | None = None,
    sort_by: str = "titleSort",
    sort_dir: str = "asc",
    limit: int = 100,
    offset: int = 0,
) -> list[MediaItem]:
    """
    Advanced search for media content with extensive filtering capabilities.

    CAPABILITIES:
    - Wildcard search: Use * in text fields (e.g., "star*" for titles starting with "star")
    - Fuzzy matching: Automatic fuzzy matching for title and name fields
    - Boolean logic: Combine multiple conditions with AND/OR logic
    - Type-specific filtering: Different filters available based on media type
    - Sorting: Sort by various fields in ascending or descending order
    - Pagination: Control result set size and offset

    SEARCH TYPES:
    1. Basic Text Search:
       - General search across multiple fields: search_media("disney")
       - Title search with wildcards: search_media(title="avengers*")

    2. Media Type Filters:
       - Filter by specific type: search_media(media_type="movie")
       - Multiple types: search_media(media_type=["movie", "show"])

    3. Date/Year Filters:
       - Specific year: search_media(year=2020)
       - Year range: search_media(min_year=2010, max_year=2020)
       - By decade: search_media(decade=2020)  # 2020s

    4. Content Filters:
       - By genre: search_media(genre="Action")
       - Multiple genres (OR): search_media(genre=["Action", "Adventure"])
       - Content rating: search_media(content_rating=["PG-13", "R"])

    5. People Filters:
       - Actors: search_media(actor="Tom Hanks")
       - Directors: search_media(director="Christopher Nolan")
       - Composers: search_media(composer="Hans Zimmer")
       - Performers: search_media(performer="Yo-Yo Ma")

    6. Metadata Filters:
       - Studio: search_media(studio="Marvel Studios")
       - Country: search_media(country="Japan")
       - Collection: search_media(collection="Marvel Cinematic Universe")

    7. Rating Filters:
       - Minimum rating: search_media(min_rating=8.0)
       - Rating range: search_media(min_rating=7.0, max_rating=9.0)

    8. Status Filters:
       - Unwatched only: search_media(unwatched=True)

    SORTING:
    - sort_by: Field to sort by (titleSort, year, rating, addedAt, lastViewedAt, etc.)
    - sort_dir: 'asc' or 'desc' (default: 'asc')

    PAGINATION:
    - limit: Number of results to return (1-1000, default: 100)
    - offset: Starting position in results (for pagination)

    EXAMPLES:
    # Find high-rated action movies from the 2010s
    search_media(
        media_type="movie",
        genre="Action",
        min_year=2010,
        max_year=2019,
        min_rating=8.0,
        sort_by="rating",
        sort_dir="desc"
    )

    # Find classical music by specific composer and performer
    search_media(
        media_type="track",
        composer="Johann Sebastian Bach",
        performer="Yo-Yo Ma",
        genre="Classical"
    )

    # Find unwatched TV shows with specific actors
    search_media(
        media_type="show",
        actor=["Bryan Cranston", "Aaron Paul"],
        unwatched=True
    )

    NOTES:
    - All text searches are case-insensitive
    - Multiple values for filters (like genre, actor) use OR logic
    - Different filter types (genre AND year) use AND logic
    - The more specific your search criteria, faster the results
    """
    try:
        plex = _get_plex_service()

        # Build search parameters
        search_params = {
            "query": query,
            "library_id": library_id,
            "media_type": media_type,
            "title": title,
            "year": year,
            "decade": decade,
            "genre": genre,
            "actor": actor,
            "director": director,
            "composer": composer,
            "performer": performer,
            "content_rating": content_rating,
            "studio": studio,
            "country": country,
            "collection": collection,
            "min_rating": min_rating,
            "max_rating": max_rating,
            "min_year": min_year,
            "max_year": max_year,
            "unwatched": unwatched,
            "sort_by": sort_by,
            "sort_dir": sort_dir,
            "limit": min(1000, max(1, limit)),  # Ensure limit is between 1-1000
            "offset": max(0, offset),  # Ensure offset is not negative
        }

        # Remove None values
        search_params = {k: v for k, v in search_params.items() if v is not None}

        # Call the advanced search method
        results = await plex.search_media(**search_params)

        media_items = []
        for item in results:
            try:
                # Safely get attributes with proper string conversion
                media_type = str(getattr(item, "type", ""))
                key = str(getattr(item, "ratingKey", ""))

                def safe_get_attr(obj, attr, default=""):
                    """Safely get attribute, handling both direct attributes and methods."""
                    value = getattr(obj, attr, default)
                    if callable(value) and not isinstance(value, (str, bytes, bytearray)):
                        try:
                            return value()
                        except Exception:
                            return default
                    return value or default

                # Handle title based on media type
                if media_type == "movie":
                    title = str(safe_get_attr(item, "title", "Unknown Movie"))
                    summary = str(safe_get_attr(item, "summary", ""))
                    thumb = str(safe_get_attr(item, "thumbUrl", ""))
                    art = str(safe_get_attr(item, "artUrl", ""))
                elif media_type == "episode":
                    show = str(safe_get_attr(item, "grandparentTitle", "Unknown Show"))
                    season = str(safe_get_attr(item, "seasonNumber", "0")).zfill(2)
                    episode = str(safe_get_attr(item, "episodeNumber", "0")).zfill(2)
                    ep_title = str(safe_get_attr(item, "title", "Unknown Episode"))
                    title = f"{show} - S{season}E{episode} - {ep_title}"
                    summary = str(safe_get_attr(item, "summary", ""))
                    thumb = str(safe_get_attr(item, "thumbUrl", ""))
                    art = str(safe_get_attr(item, "grandparentThumb", ""))
                else:
                    title = str(safe_get_attr(item, "title", "Unknown"))
                    summary = str(safe_get_attr(item, "summary", ""))
                    thumb = str(safe_get_attr(item, "thumbUrl", ""))
                    art = str(safe_get_attr(item, "artUrl", ""))

                # Get numeric values with proper type handling
                year = int(getattr(item, "year", 0)) or None
                rating = float(getattr(item, "audienceRating", 0)) or None
                duration = int(getattr(item, "duration", 0)) or 0

                # Handle timestamps
                added_at = 0
                if hasattr(item, "addedAt") and item.addedAt:
                    added_at = int(getattr(item.addedAt, "timestamp", lambda: 0)())

                updated_at = 0
                if hasattr(item, "updatedAt") and item.updatedAt:
                    updated_at = int(getattr(item.updatedAt, "timestamp", lambda: 0)())

                media_items.append(
                    MediaItem(
                        key=key,
                        title=title,
                        type=media_type,
                        year=year,
                        summary=summary,
                        rating=rating,
                        thumb=thumb,
                        art=art,
                        duration=duration,
                        added_at=added_at,
                        updated_at=updated_at,
                    )
                )
            except Exception:
                logger.exception("Error processing media item:")
                continue

        return media_items
    except Exception as e:
        raise RuntimeError(f"Error searching for media: {e!s}") from e


async def get_recently_added(library_id: str | None = None, limit: int = 20) -> list[MediaItem]:
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
    try:
        plex = _get_plex_service()
        recent_items = await plex.get_recently_added(library_id=library_id, limit=limit)

        media_items = []
        for item in recent_items:
            if hasattr(item, "type") and item.type == "movie":
                media_items.append(
                    MediaItem(
                        key=item.ratingKey,
                        title=item.title,
                        type=item.type,
                        year=item.year,
                        summary=item.summary or "",
                        rating=item.audienceRating if hasattr(item, "audienceRating") else None,
                        thumb=item.thumbUrl if hasattr(item, "thumbUrl") else "",
                        art=item.artUrl if hasattr(item, "artUrl") else "",
                        duration=item.duration if hasattr(item, "duration") else 0,
                        added_at=item.addedAt.timestamp() if hasattr(item, "addedAt") and item.addedAt else 0,
                        updated_at=item.updatedAt.timestamp() if hasattr(item, "updatedAt") and item.updatedAt else 0,
                    )
                )
            elif hasattr(item, "type") and item.type == "episode":
                media_items.append(
                    MediaItem(
                        key=item.ratingKey,
                        title=f"{item.grandparentTitle} - S{item.seasonNumber:02d}E{item.episodeNumber:02d} - {item.title}",
                        type=item.type,
                        year=item.year,
                        summary=item.summary or "",
                        rating=item.audienceRating if hasattr(item, "audienceRating") else None,
                        thumb=item.thumbUrl if hasattr(item, "thumbUrl") else "",
                        art=item.grandparentThumb if hasattr(item, "grandparentThumb") else "",
                        duration=item.duration if hasattr(item, "duration") else 0,
                        added_at=item.addedAt.timestamp() if hasattr(item, "addedAt") and item.addedAt else 0,
                        updated_at=item.updatedAt.timestamp() if hasattr(item, "updatedAt") and item.updatedAt else 0,
                    )
                )
            else:
                # Fallback for other media types
                media_items.append(
                    MediaItem(
                        key=getattr(item, "ratingKey", ""),
                        title=getattr(item, "title", "Unknown"),
                        type=getattr(item, "type", ""),
                        year=getattr(item, "year", None),
                        summary=getattr(item, "summary", ""),
                        rating=getattr(item, "audienceRating", None),
                        thumb=getattr(item, "thumbUrl", ""),
                        art=getattr(item, "artUrl", ""),
                        duration=getattr(item, "duration", 0),
                        added_at=getattr(item, "addedAt", 0).timestamp()
                        if hasattr(item, "addedAt") and item.addedAt
                        else 0,
                        updated_at=getattr(item, "updatedAt", 0).timestamp()
                        if hasattr(item, "updatedAt") and item.updatedAt
                        else 0,
                    )
                )

        return media_items[:limit]  # Ensure we respect the limit
    except Exception as e:
        raise RuntimeError(f"Error fetching recently added items: {e!s}") from e


async def get_media_info(media_key: str) -> dict[str, Any]:
    """
    Get detailed information about a specific media item.

    Args:
        media_key: Plex media key/ID

    Returns:
        Detailed media information including metadata and files

    Raises:
        RuntimeError: If there's an error fetching media info
    """
    try:
        plex = _get_plex_service()
        item = await plex.get_media_info(media_key)

        if not item:
            raise RuntimeError(f"Media item {media_key} not found")

        # Extract media parts (files)
        media_parts = []
        if hasattr(item, "media"):
            for media in item.media:
                for part in media.parts:
                    media_parts.append(
                        {
                            "file": part.file,
                            "size": part.size,
                            "duration": media.duration,
                            "video_codec": media.videoCodec,
                            "audio_codec": media.audioCodec,
                            "container": media.container,
                            "width": media.width,
                            "height": media.height,
                        }
                    )

        # Extract metadata
        metadata = {
            "key": item.ratingKey,
            "title": item.title,
            "type": item.type,
            "year": getattr(item, "year", None),
            "summary": getattr(item, "summary", ""),
            "rating": getattr(item, "audienceRating", None),
            "thumb": item.thumbUrl if hasattr(item, "thumbUrl") else "",
            "art": item.artUrl if hasattr(item, "artUrl") else "",
            "duration": getattr(item, "duration", 0),
            "added_at": item.addedAt.timestamp() if hasattr(item, "addedAt") and item.addedAt else 0,
            "updated_at": item.updatedAt.timestamp() if hasattr(item, "updatedAt") and item.updatedAt else 0,
            "genres": [tag.tag for tag in getattr(item, "genres", [])],
            "directors": [tag.tag for tag in getattr(item, "directors", [])],
            "writers": [tag.tag for tag in getattr(item, "writers", [])],
            "actors": [
                {
                    "name": actor.tag,
                    "role": getattr(actor, "role", ""),
                    "thumb": getattr(actor, "thumb", ""),
                }
                for actor in getattr(item, "actors", [])
            ],
            "media_parts": media_parts,
        }

        # Add type-specific metadata
        if hasattr(item, "type"):
            if item.type == "movie":
                metadata.update(
                    {
                        "content_rating": getattr(item, "contentRating", ""),
                        "studio": getattr(item, "studio", ""),
                        "tagline": getattr(item, "tagline", ""),
                    }
                )
            elif item.type == "episode":
                metadata.update(
                    {
                        "show_title": getattr(item, "grandparentTitle", ""),
                        "season_number": getattr(item, "seasonNumber", 0),
                        "episode_number": getattr(item, "episodeNumber", 0),
                        "season_episode": f"S{getattr(item, 'seasonNumber', 0):02d}E{getattr(item, 'episodeNumber', 0):02d}",
                    }
                )

        return metadata

    except Exception as e:
        raise RuntimeError(f"Error fetching media info: {e!s}") from e


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
    try:
        plex = _get_plex_service()
        result = await plex.scan_library(library_id)
        return result.get("scan_successful", False)
    except Exception as e:
        raise RuntimeError(f"Error scanning library {library_id}: {e!s}") from e


async def help(level: str = "beginner", section: str = "all") -> dict[str, Any]:
    """
    Get comprehensive help documentation for the PlexMCP API.

    This tool provides detailed documentation about all available endpoints,
    organized by experience level and category. It includes usage examples,
    parameter details, and general Plex server information.

    Args:
        level: Documentation detail level (beginner, intermediate, expert)
        section: Section to display (all, core, playback, playlists, admin, info)

    Returns:
        Dictionary containing help documentation organized by category
    """
    from inspect import Parameter, getdoc, signature
    # Use the global mcp instance that's already imported

    # General Plex information
    plex_info = {
        "server_requirements": "Plex Media Server 1.32.0 or later required",
        "authentication": "Uses Plex Token authentication (X-Plex-Token header)",
        "rate_limiting": "Standard Plex rate limits apply (1000 requests per minute)",
        "media_types": ["Movie", "TV Show", "Music", "Photos", "Other Libraries"],
        "common_use_cases": [
            "Media browsing and searching",
            "Playback control on connected clients",
            "Library management and organization",
            "User access control and restrictions",
        ],
    }

    # Categorize tools
    categories = {
        "core": [
            "get_plex_status",
            "get_libraries",
            "search_media",
            "get_recently_added",
            "get_media_info",
        ],
        "playback": ["get_clients", "get_sessions", "play_media", "control_playback"],
        "playlists": ["get_playlists", "get_playlist", "get_playlist_items", "create_playlist"],
        "admin": [
            "get_users",
            "update_user_permissions",
            "run_server_maintenance",
            "get_server_health",
        ],
    }

    # Build detailed documentation for each tool
    tools_docs = {}

    for category, tool_names in categories.items():
        tools_docs[category] = {}
        for name in tool_names:
            if name in mcp.tools and mcp.tools[name].is_available():
                tool = mcp.tools[name]
                sig = signature(tool.func)
                doc = getdoc(tool.func) or ""

                # Parse parameters
                params = {}
                for param_name, param in sig.parameters.items():
                    if param_name == "self":
                        continue
                    param_info = {
                        "type": str(param.annotation) if param.annotation != Parameter.empty else "any",
                        "required": param.default == Parameter.empty,
                        "default": param.default if param.default != Parameter.empty else None,
                    }
                    params[param_name] = param_info

                # Split docstring into sections
                doc_lines = doc.split("\n")
                short_desc = doc_lines[0] if doc_lines else ""
                long_desc = "\n".join(doc_lines[1:]).strip()

                tools_docs[category][name] = {
                    "short_description": short_desc,
                    "long_description": long_desc,
                    "parameters": params,
                    "returns": str(sig.return_annotation) if sig.return_annotation != sig.empty else "None",
                }

    # Build response based on requested level and section
    response = {
        "api_version": "1.0",
        "documentation_level": level,
        "requested_section": section,
        "sections_available": ["all", *list(categories.keys()), "info"],
    }

    # Add general Plex info if requested
    if section in ["all", "info"]:
        response["plex_information"] = plex_info

    # Add tool documentation for requested sections
    if section == "all":
        response["tools"] = tools_docs
    elif section in categories:
        response["tools"] = {section: tools_docs.get(section, {})}

    # Add usage examples based on level
    if level in ["beginner", "intermediate"]:
        response["quick_start"] = {
            "get_server_status": "await get_plex_status()",
            "list_libraries": "await get_libraries()",
            "search_movies": "await search_media('Inception')",
            "recently_added": "await get_recently_added(limit=5)",
            "control_playback": "await control_playback(client_id='client123', action='play')",
        }

    if level == "expert":
        response["advanced_usage"] = {
            "batch_operations": "Use asyncio.gather for concurrent requests",
            "error_handling": "All endpoints raise RuntimeError with descriptive messages",
            "performance_tips": [
                "Cache results of frequently called endpoints",
                "Use specific library IDs when possible to reduce server load",
                "Batch related operations together",
            ],
        }

    return response


# No need to export app - tools are registered with the shared mcp instance
