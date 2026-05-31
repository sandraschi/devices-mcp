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
    "AnimeSeasonInfo",
    "BandwidthAnalysis",
    "CastRequest",
    "EuropeanContent",
    "MediaItem",
    "MediaLibrary",
    "PlaybackControlResult",
    "PlaylistAnalytics",
    "PlaylistCreateRequest",
    "PlexClient",
    # Playlists
    "PlexPlaylist",
    # Core
    "PlexServerStatus",
    # Playback
    "PlexSession",
    # Quality
    "QualityProfile",
    "RemotePlaybackRequest",
    "ServerMaintenanceResult",
    "TranscodingStatus",
    # Admin
    "UserPermissions",
    # Vienna/Austrian context
    "WienerRecommendation",
]
