"""
PlexMCP Models Package

This package contains all Pydantic models for the PlexMCP application,
organized into logical modules for better maintainability.
"""

# Core models
# Admin models
from .admin import ServerMaintenanceResult, UserPermissions
from .core import MediaItem, MediaLibrary, PlexServerStatus

# Playback models
from .playback import (
    CastRequest,
    PlaybackControlResult,
    PlexClient,
    PlexSession,
    RemotePlaybackRequest,
)

# Playlist models
from .playlists import PlaylistAnalytics, PlaylistCreateRequest, PlexPlaylist

# Quality models
from .quality import BandwidthAnalysis, QualityProfile, TranscodingStatus

# Vienna/Austrian context models
from .vienna import AnimeSeasonInfo, EuropeanContent, WienerRecommendation

__all__ = [
    # Core
    "PlexServerStatus",
    "MediaLibrary",
    "MediaItem",
    # Playback
    "PlexSession",
    "PlexClient",
    "RemotePlaybackRequest",
    "CastRequest",
    "PlaybackControlResult",
    # Playlists
    "PlexPlaylist",
    "PlaylistCreateRequest",
    "PlaylistAnalytics",
    # Quality
    "QualityProfile",
    "TranscodingStatus",
    "BandwidthAnalysis",
    # Admin
    "UserPermissions",
    "ServerMaintenanceResult",
    # Vienna/Austrian context
    "WienerRecommendation",
    "EuropeanContent",
    "AnimeSeasonInfo",
]
