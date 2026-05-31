"""
Plex Media Service

Provides high-level access to Plex media server functionality including:
- Library management
- Media search and discovery
- Playback control
- Playlist management
- User sessions
- Server monitoring
"""

import asyncio
from datetime import datetime
from enum import StrEnum
from typing import Any

from plexapi import utils
from plexapi.exceptions import BadConfig, NotFound, Unauthorized
from plexapi.playqueue import PlayQueue
from plexapi.server import CONFIG, PlexServer
from plexapi.video import Episode, Movie, Playlist, Season, Show
from pydantic import BaseModel

# RequestMethod is typically from plexapi.utils
RequestMethod = getattr(utils, "RequestMethod", None)
if RequestMethod is None:
    # Fallback: use string literals if RequestMethod enum doesn't exist
    class RequestMethod:
        DELETE = "DELETE"
        POST = "POST"
        GET = "GET"
        PUT = "PUT"


from ..models.media import LibrarySection as LibrarySectionModel
from ..models.media import MediaItem, MediaType
from .base import BaseService, ServiceError, service_method

# Configure PlexAPI to be more verbose with debug info
CONFIG.logger = None  # We'll use our own logging


class StreamQuality(StrEnum):
    """Stream quality presets."""

    ORIGINAL = "original"
    QUALITY_4K = "4k"
    QUALITY_1080P = "1080p"
    QUALITY_720P = "720p"
    QUALITY_480P = "480p"
    QUALITY_240P = "240p"


class StreamProtocol(StrEnum):
    """Streaming protocols."""

    HTTP = "http"
    HLS = "hls"
    DASH = "dash"
    WEBSOCKET = "websocket"


class StreamDecision(StrEnum):
    """Transcode decision options."""

    TRANSCODE = "transcode"
    DIRECT_PLAY = "direct_play"
    DIRECT_STREAM = "direct_stream"


class StreamPart(BaseModel):
    """Represents a part of a stream (e.g., a single file in a multi-part movie)."""

    id: str
    file: str
    size: int
    duration: int
    container: str
    video_profile: str
    audio_profile: str
    video_decision: StreamDecision
    audio_decision: StreamDecision
    width: int | None
    height: int | None
    bitrate: int
    video_codec: str
    audio_codec: str
    audio_channels: int
    selected: bool = False


class StreamInfo(BaseModel):
    """Detailed information about a media stream."""

    id: str
    key: str
    protocol: StreamProtocol
    address: str
    port: int
    uri: str
    status: str
    session: str | None
    session_key: str | None
    source_title: str
    decision: StreamDecision
    speed: float
    progress: float
    duration: int
    remaining: int
    context: dict[str, Any]
    video_decision: StreamDecision
    audio_decision: StreamDecision
    quality: str
    max_quality: str
    min_quality: str
    quality_profile: str
    video_codec: str
    audio_codec: str
    audio_channels: int
    width: int
    height: int
    container: str
    video_resolution: str
    video_framerate: str
    aspect_ratio: float
    audio_channels: int
    audio_channel_layout: str
    audio_profile: str
    video_profile: str
    protocol_capabilities: list[str]
    stream_type: str
    decision_encoding: str
    decision_quality: str


class PlexMediaService(BaseService):
    """Service for interacting with Plex media server.

    Provides comprehensive access to Plex server functionality including:
    - Media library management
    - Playback control and streaming
    - Playlist management
    - User and session management
    - Server monitoring and statistics
    """

    def __init__(self, base_url: str, token: str, timeout: int = 30):
        """Initialize the Plex media service.

        Args:
            base_url: Base URL of the Plex server (e.g., 'http://localhost:32400')
            token: Plex authentication token
            timeout: Request timeout in seconds
        """
        super().__init__(logger_name="PlexMediaService")
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self._plex: PlexServer | None = None
        self._sessions: dict[str, Any] = {}
        self._play_queues: dict[str, PlayQueue] = {}
        self._last_updated: datetime | None = None

    async def _initialize(self) -> None:
        """Initialize connection to Plex server."""
        try:
            self.logger.info(f"Connecting to Plex server at {self.base_url}")
            self._plex = await asyncio.to_thread(
                PlexServer,
                baseurl=self.base_url,
                token=self.token,
                timeout=self.timeout,
                session=True,  # Enable session support
            )
            self.logger.info(f"Connected to Plex server: {self._plex.friendlyName}")
            # Initial session refresh
            await self._refresh_sessions()
        except Unauthorized as e:
            raise ServiceError(
                "Failed to authenticate with Plex server. Invalid token.",
                code="auth_error",
                status_code=401,
            ) from e
        except BadConfig as e:
            raise ServiceError(f"Invalid Plex server configuration: {e!s}", code="config_error", status_code=400) from e
        except Exception as e:
            raise ServiceError(
                f"Failed to connect to Plex server: {e!s}",
                code="connection_error",
                status_code=503,
            ) from e

    async def _refresh_sessions(self, force: bool = False) -> None:
        """Refresh active sessions from the Plex server.

        Args:
            force: If True, force refresh even if recently updated
        """
        if not self._plex:
            return

        # Only refresh if forced or if we haven't updated in the last 5 seconds
        now = datetime.utcnow()
        if not force and self._last_updated and (now - self._last_updated).total_seconds() < 5:
            return

        try:
            sessions = await asyncio.to_thread(lambda: self._plex.sessions())
            self._sessions = {s.sessionKey: s for s in sessions}
            self._last_updated = now
        except Exception:
            self.logger.exception("Failed to refresh sessions:")

    # ========================================================================
    # Playback Control Methods
    # ========================================================================

    @service_method(log_execution=True)
    async def play_media(
        self,
        media_id: str,
        client_id: str | None = None,
        offset: int = 0,
        play_queue_id: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Start playing media on a client.

        Args:
            media_id: ID of the media to play
            client_id: ID of the client to play on (default: auto-select)
            offset: Start position in milliseconds
            play_queue_id: Optional play queue ID to use
            **kwargs: Additional playback options

        Returns:
            Dictionary with playback information
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Get the media item
            media = await asyncio.to_thread(self._plex.fetchItem, int(media_id))

            # Create or get play queue
            if play_queue_id and play_queue_id in self._play_queues:
                queue = self._play_queues[play_queue_id]
            else:
                queue = await asyncio.to_thread(
                    self._plex.createPlayQueue,
                    media,
                    startItem=media,
                    **{k: v for k, v in kwargs.items() if k in ["shuffle", "repeat", "continuous"]},
                )
                if play_queue_id:
                    self._play_queues[play_queue_id] = queue

            # Get client
            clients = await self.get_clients()
            client = None
            if client_id:
                client = next((c for c in clients if c.client_identifier == client_id), None)
                if not client:
                    raise ServiceError(f"Client not found: {client_id}", code="client_not_found")
            elif clients:
                client = clients[0]
            else:
                raise ServiceError("No clients available", code="no_clients")

            # Start playback
            play_queue = await asyncio.to_thread(
                self._plex.createPlayQueue,
                media,
                **{k: v for k, v in kwargs.items() if k in ["shuffle", "repeat", "continuous"]},
            )

            await asyncio.to_thread(
                client.playMedia,
                media,
                playQueueID=play_queue.playQueueID,
                offset=offset,
                **{k: v for k, v in kwargs.items() if k in ["key", "containerKey"]},
            )

            return {
                "status": "playing",
                "media_id": media_id,
                "client": client.title,
                "play_queue_id": play_queue.playQueueID,
                "offset": offset,
            }

        except Exception as e:
            self.logger.exception("Failed to play media:")
            raise ServiceError(f"Failed to play media: {e!s}", code="playback_error") from e

    @service_method(log_execution=True)
    async def pause_playback(self, client_id: str) -> dict[str, Any]:
        """Pause playback on a client.

        Args:
            client_id: ID of the client to control

        Returns:
            Dictionary with playback status
        """
        return await self._send_playback_command(client_id, "pause")

    @service_method(log_execution=True)
    async def stop_playback(self, client_id: str) -> dict[str, Any]:
        """Stop playback on a client.

        Args:
            client_id: ID of the client to control

        Returns:
            Dictionary with playback status
        """
        return await self._send_playback_command(client_id, "stop")

    @service_method(log_execution=True)
    async def seek_to(self, client_id: str, position: int) -> dict[str, Any]:
        """Seek to a specific position in the current media.

        Args:
            client_id: ID of the client to control
            position: Position in milliseconds to seek to

        Returns:
            Dictionary with playback status
        """
        return await self._send_playback_command(client_id, "seekTo", offset=position)

    @service_method(log_execution=True)
    async def step_forward(self, client_id: str) -> dict[str, Any]:
        """Step forward in the current media.

        Args:
            client_id: ID of the client to control

        Returns:
            Dictionary with playback status
        """
        return await self._send_playback_command(client_id, "stepForward")

    @service_method(log_execution=True)
    async def step_back(self, client_id: str) -> dict[str, Any]:
        """Step back in the current media.

        Args:
            client_id: ID of the client to control

        Returns:
            Dictionary with playback status
        """
        return await self._send_playback_command(client_id, "stepBack")

    @service_method(log_execution=True)
    async def skip_next(self, client_id: str) -> dict[str, Any]:
        """Skip to the next item in the play queue.

        Args:
            client_id: ID of the client to control

        Returns:
            Dictionary with playback status
        """
        return await self._send_playback_command(client_id, "skipNext")

    @service_method(log_execution=True)
    async def skip_previous(self, client_id: str) -> dict[str, Any]:
        """Skip to the previous item in the play queue.

        Args:
            client_id: ID of the client to control

        Returns:
            Dictionary with playback status
        """
        return await self._send_playback_command(client_id, "skipPrevious")

    @service_method(log_execution=True)
    async def set_volume(self, client_id: str, level: int, muted: bool = False) -> dict[str, Any]:
        """Set the volume level on a client.

        Args:
            client_id: ID of the client to control
            level: Volume level (0-100)
            muted: Whether to mute the volume

        Returns:
            Dictionary with volume status
        """
        return await self._send_playback_command(
            client_id, "setParameters", volume=min(100, max(0, level)), mute=1 if muted else 0
        )

    @service_method(log_execution=True)
    async def set_stream_quality(
        self,
        client_id: str,
        quality: StreamQuality = StreamQuality.QUALITY_1080P,
        max_bitrate: int | None = None,
    ) -> dict[str, Any]:
        """Set the streaming quality for a client.

        Args:
            client_id: ID of the client to configure
            quality: Stream quality preset
            max_bitrate: Maximum bitrate in kbps

        Returns:
            Dictionary with quality settings
        """
        quality_map = {
            StreamQuality.QUALITY_4K: {"maxVideoBitrate": 20000, "videoQuality": 100},
            StreamQuality.QUALITY_1080P: {"maxVideoBitrate": 8000, "videoQuality": 90},
            StreamQuality.QUALITY_720P: {"maxVideoBitrate": 4000, "videoQuality": 60},
            StreamQuality.QUALITY_480P: {"maxVideoBitrate": 2000, "videoQuality": 30},
            StreamQuality.QUALITY_240P: {"maxVideoBitrate": 1000, "videoQuality": 10},
            StreamQuality.ORIGINAL: {"maxVideoBitrate": 100000, "videoQuality": 100},
        }

        settings = quality_map.get(quality, quality_map[StreamQuality.QUALITY_1080P])
        if max_bitrate:
            settings["maxVideoBitrate"] = max_bitrate

        return await self._send_playback_command(client_id, "setParameters", **settings)

    async def _send_playback_command(self, client_id: str, command: str, **params) -> dict[str, Any]:
        """Send a playback command to a client.

        Args:
            client_id: ID of the client to control
            command: Command to send (play, pause, stop, etc.)
            **params: Additional command parameters

        Returns:
            Dictionary with command result

        Raises:
            ServiceError: If the command fails
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Get the client
            clients = await self.get_clients()
            client = next((c for c in clients if c.client_identifier == client_id), None)
            if not client:
                raise ServiceError(f"Client not found: {client_id}", code="client_not_found")

            # Send the command
            result = await asyncio.to_thread(getattr(client, f"{command}"), **params)

            return {
                "status": "success",
                "client_id": client_id,
                "command": command,
                "result": result,
            }

        except Exception as e:
            self.logger.exception("Playback command failed:")
            raise ServiceError(f"Playback command failed: {e!s}", code="playback_command_failed") from e

    # ========================================================================
    # Playlist Management Methods
    # ========================================================================

    @service_method(log_execution=True)
    async def get_playlists(
        self,
        playlist_type: str = "audio",
        user: str | int | None = None,
        sort: str = "titleSort",
    ) -> list[dict[str, Any]]:
        """Get all playlists from the Plex server.

        Args:
            playlist_type: Type of playlists to retrieve ('audio', 'video', 'photo')
            user: Username or ID of the user to get playlists for (default: all users)
            sort: Field to sort playlists by (default: titleSort)

        Returns:
            List of playlist dictionaries
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            playlists = await asyncio.to_thread(self._plex.playlists, playlistType=playlist_type, sort=sort)

            # Filter by user if specified
            if user is not None:
                playlists = [
                    p for p in playlists if str(p.username).lower() == str(user).lower() or str(p.userID) == str(user)
                ]

            return [
                {
                    "id": str(p.ratingKey),
                    "title": p.title,
                    "type": p.playlistType,
                    "summary": p.summary,
                    "thumb": p.thumb,
                    "duration": p.duration,
                    "duration_str": str(datetime.timedelta(seconds=p.duration // 1000)) if p.duration else None,
                    "created_at": p.addedAt.isoformat() if p.addedAt else None,
                    "updated_at": p.updatedAt.isoformat() if p.updatedAt else None,
                    "item_count": p.leafCount,
                    "user": p.username,
                    "user_id": p.userID,
                }
                for p in playlists
            ]

        except Exception as e:
            self.logger.exception("Failed to get playlists:")
            raise ServiceError(f"Failed to get playlists: {e!s}", code="playlist_error") from e

    @service_method(log_execution=True)
    async def get_playlist(self, playlist_id: str, include_items: bool = True) -> dict[str, Any]:
        """Get a specific playlist by ID.

        Args:
            playlist_id: ID of the playlist to retrieve
            include_items: Whether to include playlist items in the response

        Returns:
            Dictionary with playlist details and items
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            playlist = await asyncio.to_thread(self._plex.fetchItem, int(playlist_id))

            if not isinstance(playlist, Playlist):
                raise ServiceError(f"Item {playlist_id} is not a playlist", code="not_a_playlist")

            result = {
                "id": str(playlist.ratingKey),
                "title": playlist.title,
                "type": playlist.playlistType,
                "summary": playlist.summary,
                "thumb": playlist.thumb,
                "duration": playlist.duration,
                "duration_str": str(datetime.timedelta(seconds=playlist.duration // 1000))
                if playlist.duration
                else None,
                "created_at": playlist.addedAt.isoformat() if playlist.addedAt else None,
                "updated_at": playlist.updatedAt.isoformat() if playlist.updatedAt else None,
                "item_count": playlist.leafCount,
                "user": playlist.username,
                "user_id": playlist.userID,
            }

            if include_items:
                items = await asyncio.to_thread(playlist.items)
                result["items"] = [self._format_media_item(item) for item in items]

            return result

        except NotFound:
            raise ServiceError(f"Playlist not found: {playlist_id}", code="not_found", status_code=404) from None
        except Exception as e:
            self.logger.exception("Failed to get playlist:")
            raise ServiceError(f"Failed to get playlist: {e!s}", code="playlist_error") from e

    @service_method(log_execution=True)
    async def create_playlist(
        self,
        title: str,
        items: list[str | int],
        playlist_type: str = "audio",
        summary: str | None = None,
        smart: bool = False,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a new playlist.

        Args:
            title: Title of the new playlist
            items: List of media item IDs to include in the playlist
            playlist_type: Type of playlist ('audio', 'video', 'photo')
            summary: Optional description for the playlist
            smart: Whether to create a smart playlist (requires Plex Pass)
            **kwargs: Additional playlist parameters

        Returns:
            Dictionary with the created playlist details
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Convert item IDs to media objects
            media_items = []
            for item_id in items:
                try:
                    item = await asyncio.to_thread(self._plex.fetchItem, int(item_id))
                    media_items.append(item)
                except Exception as e:
                    self.logger.warning(f"Skipping invalid item {item_id}: {e}")

            if not media_items:
                raise ServiceError("No valid items provided for playlist", code="no_valid_items")

            # Create the playlist
            if smart:
                # Smart playlist creation (Plex Pass required)
                playlist = await asyncio.to_thread(
                    self._plex.createPlaylist,
                    title=title,
                    items=media_items,
                    section_type=playlist_type,
                    summary=summary,
                    smart=smart,
                    **kwargs,
                )
            else:
                # Regular playlist
                playlist = await asyncio.to_thread(self._plex.createPlaylist, title=title, items=media_items, **kwargs)

            return await self.get_playlist(playlist.ratingKey)

        except Exception as e:
            self.logger.exception("Failed to create playlist:")
            raise ServiceError(f"Failed to create playlist: {e!s}", code="playlist_creation_failed") from e

    @service_method(log_execution=True)
    async def update_playlist(
        self,
        playlist_id: str,
        title: str | None = None,
        summary: str | None = None,
        items: list[str | int] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Update an existing playlist.

        Args:
            playlist_id: ID of the playlist to update
            title: New title for the playlist
            summary: New summary/description for the playlist
            items: New list of media item IDs (replaces all existing items)
            **kwargs: Additional playlist parameters

        Returns:
            Dictionary with the updated playlist details
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Get the existing playlist
            playlist = await asyncio.to_thread(self._plex.fetchItem, int(playlist_id))

            if not isinstance(playlist, Playlist):
                raise ServiceError(f"Item {playlist_id} is not a playlist", code="not_a_playlist")

            # Update title if provided
            if title is not None:
                await asyncio.to_thread(setattr, playlist, "title", title)

            # Update summary if provided
            if summary is not None:
                await asyncio.to_thread(setattr, playlist, "summary", summary)

            # Update items if provided
            if items is not None:
                media_items = []
                for item_id in items:
                    try:
                        item = await asyncio.to_thread(self._plex.fetchItem, int(item_id))
                        media_items.append(item)
                    except Exception as e:
                        self.logger.warning(f"Skipping invalid item {item_id}: {e}")

                if media_items:
                    await asyncio.to_thread(playlist.addItems, media_items)

            # Save changes
            await asyncio.to_thread(playlist.save)

            return await self.get_playlist(playlist_id)

        except NotFound:
            raise ServiceError(f"Playlist not found: {playlist_id}", code="not_found", status_code=404) from None
        except Exception as e:
            self.logger.exception("Failed to update playlist:")
            raise ServiceError(f"Failed to update playlist: {e!s}", code="playlist_update_failed") from e

    @service_method(log_execution=True)
    async def delete_playlist(self, playlist_id: str) -> dict[str, Any]:
        """Delete a playlist.

        Args:
            playlist_id: ID of the playlist to delete

        Returns:
            Dictionary with deletion status
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Get the playlist first to return details
            playlist = await self.get_playlist(playlist_id, include_items=False)

            # Delete the playlist
            await asyncio.to_thread(self._plex.query, f"/playlists/{playlist_id}", method=RequestMethod.DELETE)

            return {
                "status": "deleted",
                "playlist_id": playlist_id,
                "title": playlist["title"],
                "item_count": playlist["item_count"],
            }

        except NotFound:
            raise ServiceError(f"Playlist not found: {playlist_id}", code="not_found", status_code=404) from None
        except Exception as e:
            self.logger.exception("Failed to delete playlist:")
            raise ServiceError(f"Failed to delete playlist: {e!s}", code="playlist_deletion_failed") from e

    @service_method(log_execution=True)
    async def add_to_playlist(self, playlist_id: str, items: list[str | int], append: bool = True) -> dict[str, Any]:
        """Add items to an existing playlist.

        Args:
            playlist_id: ID of the playlist to add to
            items: List of media item IDs to add
            append: If True, append to the end; if False, insert at the beginning

        Returns:
            Dictionary with the updated playlist details
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Get the playlist
            playlist = await asyncio.to_thread(self._plex.fetchItem, int(playlist_id))

            if not isinstance(playlist, Playlist):
                raise ServiceError(f"Item {playlist_id} is not a playlist", code="not_a_playlist")

            # Convert item IDs to media objects
            media_items = []
            for item_id in items:
                try:
                    item = await asyncio.to_thread(self._plex.fetchItem, int(item_id))
                    media_items.append(item)
                except Exception as e:
                    self.logger.warning(f"Skipping invalid item {item_id}: {e}")

            if not media_items:
                raise ServiceError("No valid items to add to playlist", code="no_valid_items")

            # Add items to playlist
            if append:
                await asyncio.to_thread(playlist.addItems, media_items)
            else:
                # Get existing items
                existing_items = await asyncio.to_thread(playlist.items)
                # Add new items at the beginning
                all_items = media_items + existing_items
                # Clear and re-add all items
                await asyncio.to_thread(playlist.removeItems, existing_items)
                await asyncio.to_thread(playlist.addItems, all_items)

            return await self.get_playlist(playlist_id)

        except NotFound:
            raise ServiceError(f"Playlist not found: {playlist_id}", code="not_found", status_code=404) from None
        except Exception as e:
            self.logger.exception("Failed to add items to playlist:")
            raise ServiceError(f"Failed to add items to playlist: {e!s}", code="playlist_update_failed") from e

    @service_method(log_execution=True)
    async def remove_from_playlist(self, playlist_id: str, items: list[str | int]) -> dict[str, Any]:
        """Remove items from a playlist.

        Args:
            playlist_id: ID of the playlist to modify
            items: List of media item IDs to remove

        Returns:
            Dictionary with the updated playlist details
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Get the playlist
            playlist = await asyncio.to_thread(self._plex.fetchItem, int(playlist_id))

            if not isinstance(playlist, Playlist):
                raise ServiceError(f"Item {playlist_id} is not a playlist", code="not_a_playlist")

            # Get current items
            current_items = await asyncio.to_thread(playlist.items)

            # Find items to remove
            items_to_remove = []
            for item in current_items:
                if str(item.ratingKey) in items or item.ratingKey in items:
                    items_to_remove.append(item)

            if not items_to_remove:
                self.logger.warning("No matching items found to remove from playlist")
                return await self.get_playlist(playlist_id)

            # Remove items
            await asyncio.to_thread(playlist.removeItems, items_to_remove)

            return await self.get_playlist(playlist_id)

        except NotFound:
            raise ServiceError(f"Playlist not found: {playlist_id}", code="not_found", status_code=404) from None
        except Exception as e:
            self.logger.exception("Failed to remove items from playlist:")
            raise ServiceError(f"Failed to remove items from playlist: {e!s}", code="playlist_update_failed") from e

    # ========================================================================
    # Client and Session Management Methods
    # ========================================================================

    @service_method(log_execution=True)
    async def get_clients(self) -> list[dict[str, Any]]:
        """Get all available Plex clients.

        Returns:
            List of client dictionaries with their details
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            clients = await asyncio.to_thread(lambda: self._plex.clients())

            return [
                {
                    "id": client.clientIdentifier,
                    "name": client.title,
                    "product": client.product,
                    "platform": client.platform,
                    "version": client.version,
                    "address": client.address,
                    "port": client.port,
                    "protocol": client.protocol,
                    "device_class": client.deviceClass,
                    "protocol_capabilities": client.protocolCapabilities,
                    "protocol_version": client.protocolVersion,
                    "provides": client.provides,
                    "token": client.token,
                    "is_secure": client.isSecureConnection,
                    "last_seen": client.lastSeenAt.isoformat()
                    if hasattr(client, "lastSeenAt") and client.lastSeenAt
                    else None,
                }
                for client in clients
            ]

        except Exception as e:
            self.logger.exception("Failed to get clients:")
            raise ServiceError(f"Failed to get clients: {e!s}", code="client_error") from e

    @service_method(log_execution=True)
    async def get_sessions(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """Get current active sessions on the Plex server.

        Args:
            force_refresh: If True, force refresh the session cache

        Returns:
            List of active session dictionaries
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Refresh sessions if needed
            await self._refresh_sessions(force=force_refresh)

            sessions = []
            for session in self._sessions.values():
                try:
                    session_info = {
                        "session_key": session.sessionKey,
                        "user": {
                            "id": session.user.id,
                            "name": session.user.title,
                            "thumb": session.user.thumb,
                        }
                        if hasattr(session, "user")
                        else None,
                        "player": {
                            "id": session.player.machineIdentifier,
                            "name": session.player.title,
                            "product": session.player.product,
                            "platform": session.player.platform,
                            "state": session.player.state,
                            "local": session.player.local,
                            "address": session.player.address,
                            "device": session.player.device,
                            "model": session.player.model,
                            "device_class": session.player.deviceClass,
                        }
                        if hasattr(session, "player")
                        else None,
                        "media": [],
                    }

                    # Add media information
                    if hasattr(session, "media"):
                        for media in session.media:
                            media_info = {
                                "id": media.ratingKey,
                                "title": media.title,
                                "type": media.type,
                                "duration": media.duration,
                                "view_offset": media.viewOffset,
                                "progress": (media.viewOffset / media.duration) * 100 if media.duration > 0 else 0,
                                "container": media.container,
                                "video_resolution": media.videoResolution,
                                "video_codec": media.videoCodec,
                                "audio_codec": media.audioCodec,
                                "audio_channels": media.audioChannels,
                                "bitrate": media.bitrate,
                                "width": media.width,
                                "height": media.height,
                                "aspect_ratio": media.aspectRatio,
                                "selected": media.selected,
                                "part": [],
                            }

                            # Add part information
                            for part in media.parts:
                                part_info = {
                                    "id": part.id,
                                    "key": part.key,
                                    "duration": part.duration,
                                    "file": part.file,
                                    "size": part.size,
                                    "container": part.container,
                                    "has_thumbnail": part.hasThumbnail,
                                    "stream": [],
                                }

                                # Add stream information
                                for stream in part.streams:
                                    stream_info = {
                                        "id": stream.id,
                                        "stream_type": stream.streamType,
                                        "codec": stream.codec,
                                        "index": stream.index,
                                        "channels": stream.channels if hasattr(stream, "channels") else None,
                                        "language": stream.language if hasattr(stream, "language") else None,
                                        "language_code": stream.languageCode
                                        if hasattr(stream, "languageCode")
                                        else None,
                                        "selected": stream.selected,
                                        "title": stream.title if hasattr(stream, "title") else None,
                                        "display_title": stream.displayTitle
                                        if hasattr(stream, "displayTitle")
                                        else None,
                                    }

                                    # Add video-specific fields
                                    if hasattr(stream, "width"):
                                        stream_info.update(
                                            {
                                                "width": stream.width,
                                                "height": stream.height,
                                                "pixel_aspect_ratio": stream.pixelAspectRatio,
                                                "frame_rate": stream.frameRate,
                                                "bitrate": stream.bitrate,
                                                "color_space": stream.colorSpace
                                                if hasattr(stream, "colorSpace")
                                                else None,
                                                "color_range": stream.colorRange
                                                if hasattr(stream, "colorRange")
                                                else None,
                                                "color_primaries": stream.colorPrimaries
                                                if hasattr(stream, "colorPrimaries")
                                                else None,
                                                "color_trc": stream.colorTrc if hasattr(stream, "colorTrc") else None,
                                                "ref_frames": stream.refFrames
                                                if hasattr(stream, "refFrames")
                                                else None,
                                            }
                                        )

                                    # Add audio-specific fields
                                    if hasattr(stream, "audioChannelLayout"):
                                        stream_info.update(
                                            {
                                                "audio_channel_layout": stream.audioChannelLayout,
                                                "sampling_rate": stream.samplingRate
                                                if hasattr(stream, "samplingRate")
                                                else None,
                                                "bit_depth": stream.bitDepth if hasattr(stream, "bitDepth") else None,
                                                "bitrate_mode": stream.bitrateMode
                                                if hasattr(stream, "bitrateMode")
                                                else None,
                                                "dialog_norm": stream.dialogNorm
                                                if hasattr(stream, "dialogNorm")
                                                else None,
                                            }
                                        )

                                    # Add subtitle-specific fields
                                    if hasattr(stream, "subtitleFormat"):
                                        stream_info.update(
                                            {
                                                "subtitle_format": stream.subtitleFormat,
                                                "forced": stream.forced if hasattr(stream, "forced") else False,
                                                "hearing_impaired": stream.hearingImpaired
                                                if hasattr(stream, "hearingImpaired")
                                                else False,
                                            }
                                        )

                                    part_info["stream"].append(stream_info)

                                media_info["part"].append(part_info)

                            session_info["media"].append(media_info)

                    sessions.append(session_info)

                except Exception:
                    self.logger.exception("Error processing session:")

            return sessions

        except Exception as e:
            self.logger.exception("Failed to get sessions:")
            raise ServiceError(f"Failed to get sessions: {e!s}", code="session_error") from e

    @service_method(log_execution=True)
    async def get_session(self, session_key: str) -> dict[str, Any] | None:
        """Get details for a specific session.

        Args:
            session_key: The session key to look up

        Returns:
            Dictionary with session details or None if not found
        """
        sessions = await self.get_sessions()
        return next((s for s in sessions if s["session_key"] == session_key), None)

    @service_method(log_execution=True)
    async def terminate_session(self, session_key: str) -> dict[str, Any]:
        """Terminate a specific session.

        Args:
            session_key: The session key to terminate

        Returns:
            Dictionary with termination status
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # First verify the session exists
            session = await self.get_session(session_key)
            if not session:
                raise ServiceError(f"Session not found: {session_key}", code="session_not_found", status_code=404)

            # Terminate the session
            await asyncio.to_thread(
                self._plex.query,
                f"/status/sessions/terminate?sessionId={session_key}",
                method=RequestMethod.POST,
            )

            return {
                "status": "terminated",
                "session_key": session_key,
                "user": session.get("user", {}).get("name") if session.get("user") else None,
                "player": session.get("player", {}).get("name") if session.get("player") else None,
            }

        except Exception as e:
            self.logger.exception("Failed to terminate session:")
            raise ServiceError(f"Failed to terminate session: {e!s}", code="session_termination_failed") from e

    @service_method(log_execution=True)
    async def terminate_all_sessions(self, user_id: str | int | None = None) -> dict[str, Any]:
        """Terminate all active sessions, optionally filtered by user.

        Args:
            user_id: Optional user ID to filter sessions by

        Returns:
            Dictionary with termination results
        """
        sessions = await self.get_sessions()

        if user_id is not None:
            sessions = [s for s in sessions if s.get("user", {}).get("id") == str(user_id)]

        results = {
            "total_sessions": len(sessions),
            "terminated_sessions": 0,
            "failed_sessions": 0,
            "sessions": [],
        }

        for session in sessions:
            try:
                await self.terminate_session(session["session_key"])
                results["sessions"].append(
                    {
                        "session_key": session["session_key"],
                        "status": "terminated",
                        "user": session.get("user", {}).get("name") if session.get("user") else None,
                        "player": session.get("player", {}).get("name") if session.get("player") else None,
                    }
                )
                results["terminated_sessions"] += 1
            except Exception as e:
                self.logger.exception("Failed to terminate session {session.get('session_key')}:")
                results["sessions"].append(
                    {
                        "session_key": session["session_key"],
                        "status": "failed",
                        "error": str(e),
                        "user": session.get("user", {}).get("name") if session.get("user") else None,
                        "player": session.get("player", {}).get("name") if session.get("player") else None,
                    }
                )
                results["failed_sessions"] += 1

        return results

    # ========================================================================
    # Media Search and Library Management Methods
    # ========================================================================

    @service_method(log_execution=True)
    async def search_media(
        self,
        query: str,
        libtype: str | list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
        sort: str | None = None,
        **filters,
    ) -> dict[str, Any]:
        """Search for media across all libraries.

        Args:
            query: Search query string
            libtype: Filter by media type (e.g., 'movie', 'show', 'season', 'episode', 'artist', 'album', 'track', 'photo')
            limit: Maximum number of results to return (default: 50)
            offset: Offset for pagination (default: 0)
            sort: Field to sort results by (e.g., 'titleSort', 'addedAt', 'lastViewedAt')
            **filters: Additional filters (e.g., year=2020, unwatched=True)

        Returns:
            Dictionary with search results and metadata
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Prepare search parameters
            search_params = {
                "query": query,
                "maxresults": min(limit, 200),  # Limit max results to 200 per request
                "limit": limit,
                "offset": offset,
            }

            # Add libtype filter if specified
            if libtype:
                if isinstance(libtype, str):
                    search_params["libtype"] = libtype
                elif isinstance(libtype, (list, tuple)):
                    search_params["libtype"] = ",".join(libtype)

            # Add sort parameter if specified
            if sort:
                search_params["sort"] = sort

            # Add additional filters
            search_params.update({k.replace("_", ""): v for k, v in filters.items() if v is not None})

            # Execute search
            results = await asyncio.to_thread(self._plex.search, **search_params)

            # Format results
            formatted_results = []
            for item in results[offset : offset + limit]:
                try:
                    formatted_item = self._format_media_item(item)
                    formatted_results.append(formatted_item)
                except Exception as e:
                    self.logger.warning(f"Error formatting search result {item.ratingKey}: {e}")

            return {
                "query": query,
                "total_results": len(results),
                "returned_results": len(formatted_results),
                "offset": offset,
                "limit": limit,
                "results": formatted_results,
            }

        except Exception as e:
            self.logger.exception("Search failed:")
            raise ServiceError(f"Search failed: {e!s}", code="search_failed") from e

    @service_method(log_execution=True)
    async def get_recently_added(
        self,
        libtype: str | None = None,
        limit: int = 20,
        offset: int = 0,
        section_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Get recently added media items.

        Args:
            libtype: Filter by media type (e.g., 'movie', 'show', 'artist')
            limit: Maximum number of items to return (default: 20)
            offset: Offset for pagination (default: 0)
            section_id: Optional library section ID to filter by

        Returns:
            Dictionary with recently added items and metadata
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Get the library section if specified
            if section_id is not None:
                library = await asyncio.to_thread(self._plex.library.sectionByID, int(section_id))
                if libtype and library.type != libtype:
                    return {
                        "total_results": 0,
                        "returned_results": 0,
                        "offset": offset,
                        "limit": limit,
                        "section_id": section_id,
                        "section_name": library.title,
                        "section_type": library.type,
                        "results": [],
                    }
            else:
                library = self._plex.library

            # Get recently added items
            items = await asyncio.to_thread(
                library.recentlyAdded,
                maxresults=min(limit + offset, 100),  # Limit to 100 items max per request
            )

            # Apply offset and limit
            paginated_items = items[offset : offset + limit]

            # Format results
            formatted_results = [self._format_media_item(item) for item in paginated_items]

            return {
                "total_results": len(items),
                "returned_results": len(formatted_results),
                "offset": offset,
                "limit": limit,
                "section_id": section_id,
                "section_name": library.title if section_id is not None else None,
                "section_type": library.type if section_id is not None else None,
                "results": formatted_results,
            }

        except Exception as e:
            self.logger.exception("Failed to get recently added items:")
            raise ServiceError(f"Failed to get recently added items: {e!s}", code="recently_added_failed") from e

    @service_method(log_execution=True)
    async def get_on_deck(
        self, limit: int = 20, offset: int = 0, section_id: str | int | None = None
    ) -> dict[str, Any]:
        """Get items that are currently on deck (in progress).

        Args:
            limit: Maximum number of items to return (default: 20)
            offset: Offset for pagination (default: 0)
            section_id: Optional library section ID to filter by

        Returns:
            Dictionary with on deck items and metadata
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Get the library section if specified
            if section_id is not None:
                library = await asyncio.to_thread(self._plex.library.sectionByID, int(section_id))
                on_deck = await asyncio.to_thread(library.onDeck)
            else:
                on_deck = await asyncio.to_thread(self._plex.library.onDeck)
                library = self._plex.library

            # Apply offset and limit
            paginated_items = on_deck[offset : offset + limit]

            # Format results
            formatted_results = [self._format_media_item(item) for item in paginated_items]

            return {
                "total_results": len(on_deck),
                "returned_results": len(formatted_results),
                "offset": offset,
                "limit": limit,
                "section_id": section_id,
                "section_name": library.title if section_id is not None else None,
                "section_type": library.type if section_id is not None else None,
                "results": formatted_results,
            }

        except Exception as e:
            self.logger.exception("Failed to get on deck items:")
            raise ServiceError(f"Failed to get on deck items: {e!s}", code="on_deck_failed") from e

    @service_method(log_execution=True)
    async def get_recently_played(
        self,
        libtype: str | None = None,
        limit: int = 20,
        offset: int = 0,
        section_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Get recently played media items.

        Args:
            libtype: Filter by media type (e.g., 'movie', 'episode', 'track')
            limit: Maximum number of items to return (default: 20)
            offset: Offset for pagination (default: 0)
            section_id: Optional library section ID to filter by

        Returns:
            Dictionary with recently played items and metadata
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Get the library section if specified
            if section_id is not None:
                library = await asyncio.to_thread(self._plex.library.sectionByID, int(section_id))
                if libtype and library.type != libtype:
                    return {
                        "total_results": 0,
                        "returned_results": 0,
                        "offset": offset,
                        "limit": limit,
                        "section_id": section_id,
                        "section_name": library.title,
                        "section_type": library.type,
                        "results": [],
                    }
                recently_played = await asyncio.to_thread(library.recentlyViewed, libtype=libtype)
            else:
                library = self._plex.library
                recently_played = await asyncio.to_thread(library.recentlyViewed, libtype=libtype)

            # Apply offset and limit
            paginated_items = recently_played[offset : offset + limit]

            # Format results
            formatted_results = [self._format_media_item(item) for item in paginated_items]

            return {
                "total_results": len(recently_played),
                "returned_results": len(formatted_results),
                "offset": offset,
                "limit": limit,
                "section_id": section_id,
                "section_name": library.title if section_id is not None else None,
                "section_type": library.type if section_id is not None else None,
                "results": formatted_results,
            }

        except Exception as e:
            self.logger.exception("Failed to get recently played items:")
            raise ServiceError(f"Failed to get recently played items: {e!s}", code="recently_played_failed") from e

    @service_method(log_execution=True)
    async def get_media_metadata(self, item_id: str) -> dict[str, Any]:
        """Get detailed metadata for a media item.

        Args:
            item_id: ID of the media item

        Returns:
            Dictionary with detailed metadata
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Get the item
            item = await asyncio.to_thread(self._plex.fetchItem, int(item_id))

            # Format the item with detailed metadata
            result = self._format_media_item(item, include_metadata=True)

            # Add additional metadata based on item type
            if hasattr(item, "media"):
                result["media"] = [self._format_media_part(part) for part in item.media]

            # Add chapters if available
            if hasattr(item, "chapters"):
                result["chapters"] = [
                    {
                        "id": ch.id,
                        "title": ch.title,
                        "start": ch.start,
                        "end": ch.end,
                        "thumb": ch.thumb,
                    }
                    for ch in item.chapters()
                ]

            # Add related items if available
            if hasattr(item, "related"):
                try:
                    related = await asyncio.to_thread(item.related)
                    result["related"] = [
                        {
                            "id": rel.ratingKey,
                            "title": rel.title,
                            "type": rel.type,
                            "thumb": rel.thumb,
                            "year": rel.year if hasattr(rel, "year") else None,
                        }
                        for rel in related[:10]  # Limit to 10 related items
                    ]
                except Exception as e:
                    self.logger.warning(f"Failed to get related items: {e}")

            return result

        except NotFound:
            raise ServiceError(f"Media item not found: {item_id}", code="not_found", status_code=404) from None
        except Exception as e:
            self.logger.exception("Failed to get media metadata:")
            raise ServiceError(f"Failed to get media metadata: {e!s}", code="metadata_failed") from e

    def _format_media_item(self, item, include_metadata: bool = False) -> dict[str, Any]:
        """Format a Plex media item into a dictionary.

        Args:
            item: The Plex media item to format
            include_metadata: Whether to include detailed metadata

        Returns:
            Formatted dictionary with item details
        """
        if not item:
            return {}

        # Base item information
        formatted = {
            "id": str(item.ratingKey),
            "type": item.type,
            "title": item.title,
            "title_sort": getattr(item, "titleSort", None),
            "original_title": getattr(item, "originalTitle", None),
            "summary": getattr(item, "summary", None),
            "tagline": getattr(item, "tagline", None),
            "thumb": item.thumb if hasattr(item, "thumb") else None,
            "art": getattr(item, "art", None),
            "banner": getattr(item, "banner", None),
            "theme": getattr(item, "theme", None),
            "duration": getattr(item, "duration", None),
            "duration_str": str(datetime.timedelta(seconds=item.duration // 1000))
            if hasattr(item, "duration") and item.duration
            else None,
            "year": getattr(item, "year", None),
            "content_rating": getattr(item, "contentRating", None),
            "rating": getattr(item, "rating", None),
            "audience_rating": getattr(item, "audienceRating", None),
            "user_rating": getattr(item, "userRating", None),
            "view_count": getattr(item, "viewCount", 0),
            "last_viewed_at": item.lastViewedAt.isoformat()
            if hasattr(item, "lastViewedAt") and item.lastViewedAt
            else None,
            "added_at": item.addedAt.isoformat() if hasattr(item, "addedAt") and item.addedAt else None,
            "updated_at": item.updatedAt.isoformat() if hasattr(item, "updatedAt") and item.updatedAt else None,
            "originally_available_at": item.originallyAvailableAt.isoformat()
            if hasattr(item, "originallyAvailableAt") and item.originallyAvailableAt
            else None,
            "guid": getattr(item, "guid", None),
            "library_section_id": getattr(item, "librarySectionID", None),
            "library_section_title": getattr(item, "librarySectionTitle", None),
            "library_section_key": getattr(item, "librarySectionKey", None),
            "view_offset": getattr(item, "viewOffset", 0),
            "is_watched": getattr(item, "isWatched", False),
            "is_favorite": getattr(item, "isFavorite", False),
            "is_locked": getattr(item, "isLocked", False),
            "has_preview": getattr(item, "hasPreviewThumbnails", False),
            "has_credits": getattr(item, "hasCreditsMarker", False),
            "has_chapters": getattr(item, "hasChapters", False),
            "has_time_tracking": getattr(item, "hasTimeTracking", False),
            "progress": (item.viewOffset / item.duration * 100)
            if hasattr(item, "viewOffset") and hasattr(item, "duration") and item.duration > 0
            else 0,
        }

        # Add type-specific fields
        if hasattr(item, "type"):
            if item.type == "movie":
                formatted.update(
                    {
                        "studio": getattr(item, "studio", None),
                        "tagline": getattr(item, "tagline", None),
                        "edition_title": getattr(item, "editionTitle", None),
                        "chapters": [
                            {"id": ch.id, "title": ch.title, "start": ch.start, "end": ch.end} for ch in item.chapters()
                        ]
                        if hasattr(item, "chapters")
                        else [],
                    }
                )
            elif item.type == "show":
                formatted.update(
                    {
                        "studio": getattr(item, "studio", None),
                        "network": getattr(item, "network", None),
                        "episode_count": getattr(item, "leafCount", 0),
                        "season_count": getattr(item, "childCount", 0),
                        "unwatched_episodes": getattr(item, "unwatchedLeafCount", 0),
                        "seasons": [
                            {
                                "id": s.ratingKey,
                                "title": s.title,
                                "index": s.index,
                                "thumb": s.thumb,
                            }
                            for s in item.seasons()
                        ]
                        if hasattr(item, "seasons") and include_metadata
                        else [],
                    }
                )
            elif item.type == "season":
                formatted.update(
                    {
                        "show_title": getattr(item, "parentTitle", None),
                        "show_id": getattr(item, "parentRatingKey", None),
                        "index": getattr(item, "index", 0),
                        "episode_count": getattr(item, "leafCount", 0),
                        "unwatched_episodes": getattr(item, "unwatchedLeafCount", 0),
                        "episodes": [
                            {
                                "id": e.ratingKey,
                                "title": e.title,
                                "index": e.index,
                                "thumb": e.thumb,
                            }
                            for e in item.episodes()
                        ]
                        if hasattr(item, "episodes") and include_metadata
                        else [],
                    }
                )
            elif item.type == "episode":
                formatted.update(
                    {
                        "show_title": getattr(item, "grandparentTitle", None),
                        "show_id": getattr(item, "grandparentRatingKey", None),
                        "season_title": getattr(item, "parentTitle", None),
                        "season_id": getattr(item, "parentRatingKey", None),
                        "season_number": getattr(item, "parentIndex", 0),
                        "episode_number": getattr(item, "index", 0),
                        "absolute_episode_number": getattr(item, "absoluteIndex", None),
                        "originally_available_at": item.originallyAvailableAt.isoformat()
                        if hasattr(item, "originallyAvailableAt") and item.originallyAvailableAt
                        else None,
                    }
                )
            elif item.type == "artist":
                formatted.update(
                    {
                        "album_count": getattr(item, "childCount", 0),
                        "track_count": getattr(item, "leafCount", 0),
                        "genres": [g.tag for g in item.genres] if hasattr(item, "genres") else [],
                        "albums": [
                            {"id": a.ratingKey, "title": a.title, "year": a.year, "thumb": a.thumb}
                            for a in item.albums()
                        ]
                        if hasattr(item, "albums") and include_metadata
                        else [],
                    }
                )
            elif item.type == "album":
                formatted.update(
                    {
                        "artist_title": getattr(item, "parentTitle", None),
                        "artist_id": getattr(item, "parentRatingKey", None),
                        "year": getattr(item, "year", None),
                        "track_count": getattr(item, "leafCount", 0),
                        "genres": [g.tag for g in item.genres] if hasattr(item, "genres") else [],
                        "tracks": [
                            {"id": t.ratingKey, "title": t.title, "track_number": t.trackNumber} for t in item.tracks()
                        ]
                        if hasattr(item, "tracks") and include_metadata
                        else [],
                    }
                )
            elif item.type == "track":
                formatted.update(
                    {
                        "artist_title": getattr(item, "grandparentTitle", None),
                        "artist_id": getattr(item, "grandparentRatingKey", None),
                        "album_title": getattr(item, "parentTitle", None),
                        "album_id": getattr(item, "parentRatingKey", None),
                        "track_number": getattr(item, "trackNumber", 0),
                        "disc_number": getattr(item, "discNumber", 1),
                        "duration": getattr(item, "duration", 0),
                        "duration_str": str(datetime.timedelta(seconds=item.duration // 1000))
                        if hasattr(item, "duration") and item.duration
                        else None,
                        "genres": [g.tag for g in item.genres] if hasattr(item, "genres") else [],
                        "mood": [m.tag for m in item.moods] if hasattr(item, "moods") else [],
                        "media": [self._format_media_part(part) for part in item.media]
                        if hasattr(item, "media")
                        else [],
                    }
                )
            elif item.type == "photo":
                formatted.update(
                    {
                        "width": getattr(item, "width", 0),
                        "height": getattr(item, "height", 0),
                        "orientation": getattr(item, "orientation", 0),
                        "taken_at": item.originallyAvailableAt.isoformat()
                        if hasattr(item, "originallyAvailableAt") and item.originallyAvailableAt
                        else None,
                        "camera_make": getattr(item, "cameraMake", None),
                        "camera_model": getattr(item, "cameraModel", None),
                        "lens": getattr(item, "lens", None),
                        "aperture": getattr(item, "aperture", None),
                        "exposure": getattr(item, "exposure", None),
                        "focal_length": getattr(item, "focalLength", None),
                        "iso": getattr(item, "iso", None),
                    }
                )

        # Add media info if available
        if hasattr(item, "media") and include_metadata:
            formatted["media"] = [self._format_media_part(part) for part in item.media]

        # Add metadata if requested
        if include_metadata:
            # Add collections
            if hasattr(item, "collections"):
                try:
                    formatted["collections"] = [{"id": c.id, "tag": c.tag} for c in item.collections]
                except Exception as e:
                    self.logger.warning(f"Failed to get collections: {e}")

            # Add genres
            if hasattr(item, "genres"):
                try:
                    formatted["genres"] = [{"id": g.id, "tag": g.tag} for g in item.genres]
                except Exception as e:
                    self.logger.warning(f"Failed to get genres: {e}")

            # Add directors
            if hasattr(item, "directors"):
                try:
                    formatted["directors"] = [{"id": d.id, "tag": d.tag} for d in item.directors]
                except Exception as e:
                    self.logger.warning(f"Failed to get directors: {e}")

            # Add writers
            if hasattr(item, "writers"):
                try:
                    formatted["writers"] = [{"id": w.id, "tag": w.tag} for w in item.writers]
                except Exception as e:
                    self.logger.warning(f"Failed to get writers: {e}")

            # Add actors
            if hasattr(item, "actors"):
                try:
                    formatted["actors"] = [
                        {"id": a.id, "tag": a.tag, "role": a.role, "thumb": a.thumb} for a in item.actors
                    ]
                except Exception as e:
                    self.logger.warning(f"Failed to get actors: {e}")

            # Add similar items
            if hasattr(item, "similar"):
                try:
                    formatted["similar"] = [{"id": s.id, "tag": s.tag} for s in item.similar]
                except Exception as e:
                    self.logger.warning(f"Failed to get similar items: {e}")

            # Add extras if available
            if hasattr(item, "extras"):
                try:
                    formatted["extras"] = [{"id": e.ratingKey, "title": e.title, "type": e.type} for e in item.extras()]
                except Exception as e:
                    self.logger.warning(f"Failed to get extras: {e}")

            # Add chapters if available
            if hasattr(item, "chapters"):
                try:
                    formatted["chapters"] = [
                        {"id": ch.id, "title": ch.title, "start": ch.start, "end": ch.end} for ch in item.chapters()
                    ]
                except Exception as e:
                    self.logger.warning(f"Failed to get chapters: {e}")

        return formatted

    def _format_media_part(self, part) -> dict[str, Any]:
        """Format a Plex media part into a dictionary.

        Args:
            part: The Plex media part to format

        Returns:
            Formatted dictionary with part details
        """
        if not part:
            return {}

        return {
            "id": getattr(part, "id", None),
            "key": getattr(part, "key", None),
            "duration": getattr(part, "duration", 0),
            "file": getattr(part, "file", ""),
            "size": getattr(part, "size", 0),
            "container": getattr(part, "container", None),
            "has_thumbnail": getattr(part, "hasThumbnail", False),
            "has_preview": getattr(part, "hasPreviewThumbnails", False),
            "video_profile": getattr(part, "videoProfile", None),
            "streams": [self._format_stream(stream) for stream in part.streams] if hasattr(part, "streams") else [],
        }

    def _format_stream(self, stream) -> dict[str, Any]:
        """Format a Plex media stream into a dictionary.

        Args:
            stream: The Plex media stream to format

        Returns:
            Formatted dictionary with stream details
        """
        if not stream:
            return {}

        formatted = {
            "id": getattr(stream, "id", None),
            "stream_type": getattr(stream, "streamType", None),
            "codec": getattr(stream, "codec", None),
            "codec_id": getattr(stream, "codecID", None),
            "index": getattr(stream, "index", 0),
            "language": getattr(stream, "language", None),
            "language_code": getattr(stream, "languageCode", None),
            "language_tag": getattr(stream, "languageTag", None),
            "selected": getattr(stream, "selected", False),
            "channels": getattr(stream, "channels", None),
            "bitrate": getattr(stream, "bitrate", None),
            "bit_depth": getattr(stream, "bitDepth", None),
            "bitrate_mode": getattr(stream, "bitrateMode", None),
            "cabac": getattr(stream, "cabac", None),
            "chroma_location": getattr(stream, "chromaLocation", None),
            "chroma_subsampling": getattr(stream, "chromaSubsampling", None),
            "color_primaries": getattr(stream, "colorPrimaries", None),
            "color_range": getattr(stream, "colorRange", None),
            "color_space": getattr(stream, "colorSpace", None),
            "color_trc": getattr(stream, "colorTrc", None),
            "frame_rate": getattr(stream, "frameRate", None),
            "has_scaling_matrix": getattr(stream, "hasScalingMatrix", None),
            "height": getattr(stream, "height", None),
            "level": getattr(stream, "level", None),
            "pixel_aspect_ratio": getattr(stream, "pixelAspectRatio", None),
            "pixel_format": getattr(stream, "pixelFormat", None),
            "profile": getattr(stream, "profile", None),
            "ref_frames": getattr(stream, "refFrames", None),
            "scan_type": getattr(stream, "scanType", None),
            "width": getattr(stream, "width", None),
            "display_title": getattr(stream, "displayTitle", None),
            "extended_display_title": getattr(stream, "extendedDisplayTitle", None),
        }

        # Audio stream specific fields
        if hasattr(stream, "audioChannelLayout"):
            formatted.update(
                {
                    "audio_channel_layout": getattr(stream, "audioChannelLayout", None),
                    "sampling_rate": getattr(stream, "samplingRate", None),
                    "dialog_norm": getattr(stream, "dialogNorm", None),
                }
            )

        # Subtitle stream specific fields
        if hasattr(stream, "subtitleFormat"):
            formatted.update(
                {
                    "subtitle_format": getattr(stream, "subtitleFormat", None),
                    "forced": getattr(stream, "forced", False),
                    "hearing_impaired": getattr(stream, "hearingImpaired", False),
                    "srt": getattr(stream, "srt", None),
                }
            )

        return formatted

    async def _shutdown(self) -> None:
        """Clean up resources."""
        self._plex = None
        self._sessions.clear()
        self._play_queues.clear()
        self._last_updated = None

    @service_method(log_execution=True)
    async def get_library_sections(self) -> list[LibrarySectionModel]:
        """Get all library sections.

        Returns:
            List of library sections
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            sections = await asyncio.to_thread(
                lambda: [
                    LibrarySectionModel(
                        id=section.key,
                        title=section.title,
                        type=section.type,
                        agent=section.agent,
                        scanner=section.scanner,
                        language=section.language,
                        updated_at=section.updatedAt.timestamp() if section.updatedAt else None,
                        created_at=section.addedAt.timestamp() if section.addedAt else None,
                        scanned_at=section.scannedAt.timestamp() if section.scannedAt else None,
                        content=section.content if hasattr(section, "content") else None,
                        content_changed_at=section.contentChangedAt.timestamp() if section.contentChangedAt else None,
                    )
                    for section in self._plex.library.sections()
                ]
            )
            return sections
        except Exception as e:
            self.logger.exception("Failed to get library sections:")
            raise ServiceError(f"Failed to get library sections: {e!s}", code="library_error") from e

    @service_method(log_execution=True)
    async def search_media_by_type(
        self,
        query: str,
        media_type: MediaType | None = None,
        section_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[MediaItem]:
        """Search for media items with type filtering.

        Args:
            query: Search query
            media_type: Optional media type filter
            section_id: Optional library section ID to search within
            limit: Maximum number of results to return
            offset: Offset for pagination

        Returns:
            List of matching media items
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Convert MediaType enum to Plex's expected format
            libtype = media_type.value if media_type else None

            # Get the specific library section if specified
            section = None
            if section_id:
                section = await asyncio.to_thread(lambda: self._plex.library.sectionByID(int(section_id)))

            # Perform the search
            results = await asyncio.to_thread(
                lambda: (section.search if section else self._plex.library.search)(
                    title=query, libtype=libtype, maxresults=limit, container_start=offset
                )
            )

            # Convert Plex API objects to our model
            return [self._plex_item_to_media_item(item) for item in results]

        except Exception as e:
            self.logger.exception("Search failed:")
            raise ServiceError(f"Search failed: {e!s}", code="search_error") from e

    def _plex_item_to_media_item(self, item) -> MediaItem:
        """Convert a Plex API item to our MediaItem model."""
        # Common fields
        media_item = MediaItem(
            id=item.ratingKey,
            title=item.title,
            type=self._get_media_type(item),
            summary=item.summary,
            thumb=item.thumbUrl if hasattr(item, "thumbUrl") else None,
            art=item.artUrl if hasattr(item, "artUrl") else None,
            added_at=item.addedAt.timestamp() if item.addedAt else None,
            updated_at=item.updatedAt.timestamp() if item.updatedAt else None,
            year=item.year,
            rating=item.audienceRating or item.rating,
            duration=item.duration / 60000,  # Convert ms to minutes
            genres=[tag.tag for tag in getattr(item, "genres", [])],
            directors=[tag.tag for tag in getattr(item, "directors", [])],
            writers=[tag.tag for tag in getattr(item, "writers", [])],
            actors=[{"name": tag.tag, "role": tag.role} for tag in getattr(item, "actors", [])],
            media_info={
                "video_resolution": item.media[0].videoResolution if item.media else None,
                "video_codec": item.media[0].videoCodec if item.media else None,
                "audio_codec": item.media[0].audioCodec if item.media and item.media[0].parts else None,
                "container": item.media[0].container if item.media else None,
                "bitrate": item.media[0].bitrate if item.media else None,
            }
            if hasattr(item, "media") and item.media
            else {},
        )

        # Type-specific fields
        if isinstance(item, Movie):
            media_item.media_type = MediaType.MOVIE
            media_item.original_title = getattr(item, "originalTitle", None)
            media_item.tagline = getattr(item, "tagline", None)
            media_item.content_rating = getattr(item, "contentRating", None)
            media_item.studio = getattr(item, "studio", None)
            media_item.chapter_source = getattr(item, "chapterSource", None)

        elif isinstance(item, (Show, Season, Episode)):
            media_item.media_type = (
                MediaType.SHOW
                if isinstance(item, Show)
                else MediaType.SEASON
                if isinstance(item, Season)
                else MediaType.EPISODE
            )

            if isinstance(item, (Show, Season)):
                media_item.child_count = getattr(item, "childCount", None)
                media_item.leaf_count = getattr(item, "leafCount", None)
                media_item.viewed_leaf_count = getattr(item, "viewedLeafCount", None)

            if isinstance(item, (Season, Episode)):
                media_item.show_title = getattr(item, "show", {}).title if hasattr(item, "show") else None
                media_item.season_number = getattr(item, "seasonNumber", None)

                if isinstance(item, Episode):
                    media_item.episode_number = getattr(item, "index", None)
                    media_item.season_episode = getattr(item, "seasonEpisode", None)

        return media_item

    def _get_media_type(self, item) -> MediaType:
        """Determine the media type from a Plex API item."""
        if isinstance(item, Movie):
            return MediaType.MOVIE
        if isinstance(item, Show):
            return MediaType.SHOW
        if isinstance(item, Season):
            return MediaType.SEASON
        if isinstance(item, Episode):
            return MediaType.EPISODE
        if hasattr(item, "type") and item.type == "artist":
            return MediaType.ARTIST
        if hasattr(item, "type") and item.type == "album":
            return MediaType.ALBUM
        if hasattr(item, "type") and item.type == "track":
            return MediaType.TRACK
        if hasattr(item, "type") and item.type == "photo":
            return MediaType.PHOTO
        return MediaType.OTHER

    @service_method(log_execution=True)
    async def refresh_library(self, section_id: str | None = None) -> dict[str, Any]:
        """Refresh a library section or all sections.

        Args:
            section_id: Optional section ID to refresh. If None, refreshes all sections.

        Returns:
            Dictionary with refresh status
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            if section_id:
                section = await asyncio.to_thread(lambda: self._plex.library.sectionByID(int(section_id)))
                await asyncio.to_thread(section.update)
                return {
                    "status": "success",
                    "section_id": section_id,
                    "section_name": section.title,
                }
            await asyncio.to_thread(self._plex.library.update)
            return {"status": "success", "message": "All sections refreshed"}

        except Exception as e:
            self.logger.exception("Failed to refresh library:")
            raise ServiceError(f"Failed to refresh library: {e!s}", code="refresh_error") from e

    @service_method(log_execution=True)
    async def get_recently_added_by_type(
        self,
        media_type: MediaType | None = None,
        limit: int = 20,
        section_id: str | None = None,
    ) -> list[MediaItem]:
        """Get recently added media items with type filtering.

        Args:
            media_type: Optional media type filter
            limit: Maximum number of items to return
            section_id: Optional section ID to filter by

        Returns:
            List of recently added media items
        """
        if not self._plex:
            raise ServiceError("Plex server not connected", code="not_connected")

        try:
            # Get the specific library section if specified
            section = None
            if section_id:
                section = await asyncio.to_thread(lambda: self._plex.library.sectionByID(int(section_id)))

            # Get recently added items
            if media_type:
                libtype = media_type.value
                items = await asyncio.to_thread(
                    lambda: (section if section else self._plex.library).recentlyAdded(
                        libtype=libtype, maxresults=limit
                    )
                )
            else:
                items = []
                for libtype in ["movie", "show", "season", "episode"]:
                    try:
                        section_items = await asyncio.to_thread(
                            lambda lt: (section if section else self._plex.library).recentlyAdded(
                                libtype=lt, maxresults=limit
                            ),
                            libtype,
                        )
                        items.extend(section_items)
                    except Exception as e:
                        self.logger.warning(f"Could not get recently added {libtype}: {e}")

                # Sort by addedAt and limit results
                items.sort(key=lambda x: x.addedAt, reverse=True)
                items = items[:limit]

            return [self._plex_item_to_media_item(item) for item in items]

        except Exception as e:
            self.logger.exception("Failed to get recently added items:")
            raise ServiceError(f"Failed to get recently added items: {e!s}", code="recently_added_error") from e


# Example usage:
# service = PlexMediaService("http://localhost:32400", "your-plex-token")
# await service.initialize()
# recently_added = await service.get_recently_added(limit=10)
# for item in recently_added:
