"""
Playlist service implementation for PlexMCP.

This module contains the PlaylistService class which handles all playlist-related
operations for the Plex Media Server.
"""

import logging

from plexapi.exceptions import BadRequest, NotFound

from ..models import MediaItem, PlaylistAnalytics, PlaylistCreateRequest, PlexPlaylist
from .base import BaseService, ServiceError

logger = logging.getLogger(__name__)


class PlaylistService(BaseService):
    """Service for managing Plex playlists."""

    def __init__(self, plex_service):
        """Initialize the playlist service.

        Args:
            plex_service: Instance of PlexService for Plex server interaction
        """
        super().__init__()
        self.plex_service = plex_service
        self.plex = None

    async def _initialize(self) -> None:
        """Initialize the service."""
        await self.plex_service.initialize()
        self.plex = self.plex_service.plex

    async def create_playlist(self, request: PlaylistCreateRequest) -> PlexPlaylist:
        """Create a new playlist (manual or smart).

        Args:
            request: Playlist creation request

        Returns:
            Created playlist information
        """
        await self.initialize()

        try:
            # For smart playlists (using filters)
            if request.smart_rules:
                # In a real implementation, we would convert smart_rules to Plex's filter format
                # This is a simplified example
                logger.warning("Smart playlist creation is not fully implemented")

                # Create an empty playlist and add filtered items
                playlist = self.plex.createPlaylist(title=request.name, items=[], smart=bool(request.smart_rules))

                # TODO: Apply smart rules to populate the playlist
                # This would involve querying the library with the specified filters

            # For manual playlists
            elif request.items:
                # Get the media items
                items = []
                for item_key in request.items:
                    try:
                        item = self.plex.fetchItem(item_key)
                        items.append(item)
                    except Exception as e:
                        logger.warning(f"Failed to find media item {item_key}: {e!s}")

                if not items:
                    raise ServiceError("No valid media items found", code="no_valid_items")

                # Create the playlist
                playlist = self.plex.createPlaylist(title=request.name, items=items, smart=False)
            else:
                # Create an empty playlist
                playlist = self.plex.createPlaylist(title=request.name, items=[], smart=False)

            # Update playlist metadata if provided
            if request.summary:
                playlist.edit(summary=request.summary)

            return self._convert_to_playlist_model(playlist)

        except BadRequest as e:
            error_msg = f"Invalid playlist creation request: {e!s}"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="invalid_request") from e
        except Exception as e:
            error_msg = f"Failed to create playlist: {e!s}"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="playlist_creation_failed") from e

    async def get_playlists(self, playlist_type: str | None = None, user_playlists: bool = True) -> list[PlexPlaylist]:
        """Get all playlists from the Plex server.

        Args:
            playlist_type: Optional filter by type (video, audio, photo)
            user_playlists: If True, only return playlists created by the current user

        Returns:
            List of playlists
        """
        await self.initialize()

        try:
            playlists = []
            for playlist in self.plex.playlists():
                # Filter by type if specified
                if playlist_type and playlist.playlistType != playlist_type:
                    continue

                # Filter by owner if needed
                if user_playlists and not self._is_user_playlist(playlist):
                    continue

                playlists.append(self._convert_to_playlist_model(playlist))

            return playlists

        except Exception as e:
            error_msg = f"Failed to get playlists: {e!s}"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="get_playlists_failed") from e

    async def get_playlist(self, playlist_id: str) -> PlexPlaylist:
        """Get a specific playlist by ID.

        Args:
            playlist_id: ID of the playlist to retrieve

        Returns:
            Playlist information and items
        """
        await self.initialize()

        try:
            playlist = self.plex.fetchItem(playlist_id)
            return self._convert_to_playlist_model(playlist)

        except NotFound as e:
            error_msg = f"Playlist {playlist_id} not found"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="not_found") from e
        except Exception as e:
            error_msg = f"Failed to get playlist {playlist_id}: {e!s}"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="get_playlist_failed") from e

    async def get_playlist_items(self, playlist_id: str) -> list[MediaItem]:
        """Get all items in a playlist.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of media items in the playlist
        """
        await self.initialize()

        try:
            playlist = self.plex.fetchItem(playlist_id)
            return [self.plex_service._convert_to_media_item(item) for item in playlist.items()]

        except NotFound as e:
            error_msg = f"Playlist {playlist_id} not found"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="not_found") from e
        except Exception as e:
            error_msg = f"Failed to get playlist items for {playlist_id}: {e!s}"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="get_playlist_items_failed") from e

    async def analyze_playlist(self, playlist_id: str) -> PlaylistAnalytics:
        """Analyze a playlist and provide recommendations.

        Args:
            playlist_id: ID of the playlist to analyze

        Returns:
            Playlist analytics and recommendations
        """
        await self.initialize()

        try:
            # Get the playlist
            playlist = self.plex.fetchItem(playlist_id)
            items = playlist.items()

            # Calculate basic statistics
            total_duration = sum((item.duration or 0) for item in items) / 1000  # Convert to seconds
            avg_rating = sum((item.userRating or 0) for item in items) / len(items) if items else 0

            # Generate some mock recommendations
            recommendations = []
            if len(items) < 10:
                recommendations.append("Consider adding more items to this playlist")
            if total_duration > 4 * 3600:  # More than 4 hours
                recommendations.append("This is a long playlist - consider splitting it into multiple parts")

            # Get most common genres (simplified)
            genres = {}
            for item in items:
                for genre in getattr(item, "genres", []):
                    genres[genre.tag] = genres.get(genre.tag, 0) + 1

            most_common_genre = max(genres.items(), key=lambda x: x[1])[0] if genres else None

            # Honesty: play-history statistics (plays, users, completion,
            # skip rate, last played) require Plex play-history integration
            # which is NOT implemented. Previously they were random numbers
            # (fake green). Real-derived fields stay; the rest are explicit 0
            # with a simulated=True flag.
            return PlaylistAnalytics(
                playlist_id=playlist_id,
                name=playlist.title,
                total_plays=0,
                unique_users=0,
                avg_completion_rate=0.0,
                popular_items=[item.title for item in items[:3]],
                skip_rate=0.0,
                recommendations=recommendations,
                last_played=None,
                genre_breakdown=genres,
                most_common_genre=most_common_genre,
                total_duration_seconds=total_duration,
                avg_rating=avg_rating,
                simulated=True,
                note="Play-history stats not implemented - plays/users/completion/skip/last-played are 0/None, not measured values.",
            )

        except NotFound as e:
            error_msg = f"Playlist {playlist_id} not found"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="not_found") from e
        except Exception as e:
            error_msg = f"Failed to analyze playlist {playlist_id}: {e!s}"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="analyze_playlist_failed") from e

    # Helper methods
    def _is_user_playlist(self, playlist) -> bool:
        """Check if a playlist was created by the current user."""
        # This is a simplified check - in a real implementation, you'd compare with the current user
        return not playlist.title.startswith("Plex ")

    def _convert_to_playlist_model(self, playlist) -> PlexPlaylist:
        """Convert a Plex API playlist to our PlexPlaylist model."""
        return PlexPlaylist(
            key=playlist.ratingKey,
            title=playlist.title,
            type=playlist.playlistType,
            summary=getattr(playlist, "summary", ""),
            duration=sum(item.duration for item in playlist.items()) if hasattr(playlist, "items") else 0,
            item_count=len(playlist.items()) if hasattr(playlist, "items") else 0,
            smart=getattr(playlist, "smart", False),
            created_at=int(playlist.addedAt.timestamp()) if hasattr(playlist, "addedAt") else 0,
            updated_at=int(playlist.updatedAt.timestamp()) if hasattr(playlist, "updatedAt") else 0,
            owner=getattr(playlist, "username", "system"),
        )
