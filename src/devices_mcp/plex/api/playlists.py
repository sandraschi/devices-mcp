"""
Playlist-related API endpoints for PlexMCP.

This module contains API endpoints for managing Plex playlists.
"""

# Import the shared FastMCP instance from the package level
# Import models
from ..models import MediaItem, PlaylistAnalytics, PlaylistCreateRequest, PlexPlaylist


async def create_playlist(request: PlaylistCreateRequest) -> PlexPlaylist:
    """
    Create a new playlist (manual or smart) with Austrian efficiency.

    Supports both manual playlists (with specific items) and smart playlists
    (with automatic rules). Smart playlists update automatically based on criteria.

    Args:
        request: Playlist creation request

    Returns:
        Created playlist information

    Examples:
        Manual: create_playlist("Movie Night", items=["12345", "67890"])
        Smart: create_playlist("Top Action", smart_rules={"genre": "action", "rating": ">8"})
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()

        # Create the playlist using PlexService
        playlist = await plex.create_playlist(
            name=request.name,
            items=request.items or [],
            smart_rules=request.smart_rules,
            library_id=request.library_id,
            summary=request.summary,
        )

        if not playlist:
            raise RuntimeError("Failed to create playlist")

        # Get timestamps safely
        updated_at = 0
        if hasattr(playlist, "updatedAt") and playlist.updatedAt:
            updated_at = int(playlist.updatedAt.timestamp())

        created_at = 0
        if hasattr(playlist, "addedAt") and playlist.addedAt:
            created_at = int(playlist.addedAt.timestamp())

        return PlexPlaylist(
            key=getattr(playlist, "ratingKey", ""),
            title=getattr(playlist, "title", request.name),
            type=getattr(playlist, "playlistType", "video"),
            summary=getattr(playlist, "summary", request.summary or ""),
            duration=getattr(playlist, "duration", 0),
            item_count=getattr(playlist, "leafCount", len(request.items) if request.items else 0),
            smart=bool(request.smart_rules),
            created_at=created_at,
            updated_at=updated_at,
            owner=getattr(playlist, "username", "current_user"),
        )

    except Exception as e:
        raise RuntimeError(f"Error creating playlist: {e!s}") from e


async def get_playlists(playlist_type: str | None = None, user_playlists: bool = True) -> list[PlexPlaylist]:
    """
    Get all playlists from the Plex server.

    Args:
        playlist_type: Optional filter by type (video, audio, photo)
        user_playlists: Include user-created playlists (default: True)

    Returns:
        List of playlists with metadata

    Raises:
        RuntimeError: If there's an error fetching playlists
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        playlists = await plex.get_playlists()

        result = []
        for playlist in playlists:
            # Skip non-user playlists if requested
            if not user_playlists and not getattr(playlist, "user_created", False):
                continue

            # Filter by type if specified
            playlist_type_attr = getattr(playlist, "playlistType", "video")
            if playlist_type and playlist_type_attr.lower() != playlist_type.lower():
                continue

            # Get the timestamp safely
            updated_at = 0
            if hasattr(playlist, "updatedAt") and playlist.updatedAt:
                updated_at = int(playlist.updatedAt.timestamp())

            created_at = 0
            if hasattr(playlist, "addedAt") and playlist.addedAt:
                created_at = int(playlist.addedAt.timestamp())

            result.append(
                PlexPlaylist(
                    key=getattr(playlist, "ratingKey", ""),
                    title=getattr(playlist, "title", "Untitled Playlist"),
                    type=playlist_type_attr,
                    summary=getattr(playlist, "summary", ""),
                    duration=getattr(playlist, "duration", 0),
                    item_count=getattr(playlist, "leafCount", 0),
                    smart=getattr(playlist, "smart", False),
                    updated_at=updated_at,
                    created_at=created_at,
                    owner=getattr(playlist, "username", "system"),
                )
            )

        return result

    except Exception as e:
        raise RuntimeError(f"Error fetching playlists: {e!s}") from e


async def get_playlist(playlist_id: str) -> PlexPlaylist:
    """
    Get detailed information about a specific playlist.

    Args:
        playlist_id: ID of the playlist to retrieve

    Returns:
        Playlist details including items

    Raises:
        RuntimeError: If there's an error fetching the playlist
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        playlist = await plex.get_playlist(playlist_id)

        if not playlist:
            raise RuntimeError(f"Playlist {playlist_id} not found")

        # Get timestamps safely
        updated_at = 0
        if hasattr(playlist, "updatedAt") and playlist.updatedAt:
            updated_at = int(playlist.updatedAt.timestamp())

        created_at = 0
        if hasattr(playlist, "addedAt") and playlist.addedAt:
            created_at = int(playlist.addedAt.timestamp())

        return PlexPlaylist(
            key=getattr(playlist, "ratingKey", ""),
            title=getattr(playlist, "title", "Untitled Playlist"),
            type=getattr(playlist, "playlistType", "video"),
            summary=getattr(playlist, "summary", ""),
            duration=getattr(playlist, "duration", 0),
            item_count=getattr(playlist, "leafCount", 0),
            smart=getattr(playlist, "smart", False),
            created_at=created_at,
            updated_at=updated_at,
            owner=getattr(playlist, "username", "system"),
        )

    except Exception as e:
        raise RuntimeError(f"Error fetching playlist: {e!s}") from e


async def get_playlist_items(playlist_id: str) -> list[MediaItem]:
    """
    Get all items in a playlist.

    Args:
        playlist_id: ID of the playlist

    Returns:
        List of media items in the playlist

    Raises:
        RuntimeError: If there's an error fetching playlist items
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        items = await plex.get_playlist_items(playlist_id)

        media_items = []
        for item in items:
            # Handle different media types
            if hasattr(item, "type"):
                if item.type == "movie":
                    media_items.append(
                        MediaItem(
                            key=item.ratingKey,
                            title=item.title,
                            type=item.type,
                            year=getattr(item, "year", None),
                            summary=getattr(item, "summary", ""),
                            rating=getattr(item, "audienceRating", None),
                            thumb=item.thumbUrl if hasattr(item, "thumbUrl") else "",
                            art=item.artUrl if hasattr(item, "artUrl") else "",
                            duration=getattr(item, "duration", 0),
                            added_at=item.addedAt.timestamp() if hasattr(item, "addedAt") and item.addedAt else 0,
                            updated_at=item.updatedAt.timestamp()
                            if hasattr(item, "updatedAt") and item.updatedAt
                            else 0,
                        )
                    )
                elif item.type == "episode":
                    media_items.append(
                        MediaItem(
                            key=item.ratingKey,
                            title=f"{getattr(item, 'grandparentTitle', '')} - S{getattr(item, 'seasonNumber', 0):02d}E{getattr(item, 'episodeNumber', 0):02d} - {getattr(item, 'title', '')}",
                            type=item.type,
                            year=getattr(item, "year", None),
                            summary=getattr(item, "summary", ""),
                            rating=getattr(item, "audienceRating", None),
                            thumb=item.thumbUrl if hasattr(item, "thumbUrl") else "",
                            art=item.grandparentThumb if hasattr(item, "grandparentThumb") else "",
                            duration=getattr(item, "duration", 0),
                            added_at=item.addedAt.timestamp() if hasattr(item, "addedAt") and item.addedAt else 0,
                            updated_at=item.updatedAt.timestamp()
                            if hasattr(item, "updatedAt") and item.updatedAt
                            else 0,
                        )
                    )
                else:
                    # Fallback for other media types
                    media_items.append(
                        MediaItem(
                            key=getattr(item, "ratingKey", ""),
                            title=getattr(item, "title", "Unknown Item"),
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

        return media_items

    except Exception as e:
        raise RuntimeError(f"Error fetching playlist items: {e!s}") from e


async def analyze_playlist(playlist_id: str) -> PlaylistAnalytics:
    """
    Analyze playlist usage and provide recommendations.

    Args:
        playlist_id: ID of the playlist to analyze

    Returns:
        Analytics and recommendations for the playlist
    """
    # TODO: Implement actual analysis logic
    return PlaylistAnalytics(
        playlist_id=playlist_id,
        name=f"Sample Playlist {playlist_id[-1]}",
        total_plays=42,
        unique_users=3,
        avg_completion_rate=75.5,
        popular_items=["item1", "item3", "item5"],
        skip_rate=15.2,
        recommendations=[
            "Consider adding more recent content",
            "Try grouping similar items together",
        ],
        last_played=1625184000,
    )


# No need to export app - tools are registered with the shared mcp instance
