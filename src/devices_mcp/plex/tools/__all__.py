"""Plex MCP tools package."""

# Import all tool modules to register the tools

# Re-export the tools for easy importing
# Server tools
# Library management tools
from .library import (
    add_library,
    add_library_location,
    delete_library,
    empty_trash,
    get_library,
    list_libraries,
    optimize_library,
    refresh_library,
    remove_library_location,
    scan_library,
    update_library,
)
from .library import (
    clean_bundles as clean_library_bundles,
)

# Media tools
from .media import get_media_info, search_media

# Media organization tools
from .organization import (
    analyze_library,
    clean_bundles,
    fix_media_match,
    optimize_database,
    organize_library,
    refresh_metadata,
)

# Playlist management tools
from .playlists import (
    add_to_playlist,
    create_playlist,
    delete_playlist,
    get_playlist,
    get_playlist_analytics,
    list_playlists,
    remove_from_playlist,
    update_playlist,
)

# Audio management tools
from .portmanteau.audio_mgr import plex_audio_mgr

# Quality and transcoding tools
from .quality import (
    create_quality_profile,
    delete_quality_profile,
    get_bandwidth_usage,
    get_throttling_status,
    get_transcode_settings,
    get_transcoding_status,
    list_quality_profiles,
    set_stream_quality,
    set_throttling,
    update_transcode_settings,
)
from .server import get_server_info, get_server_status

# Session tools
from .sessions import control_playback, list_clients, list_sessions

# User management tools
from .users import (
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
    update_user_permissions,
)

__all__ = [
    # Server tools
    "get_server_status",
    "get_server_info",
    # Media tools
    "search_media",
    "get_media_info",
    # Session tools
    "list_sessions",
    "list_clients",
    "control_playback",
    "plex_audio_mgr",
    # User management
    "create_user",
    "update_user",
    "delete_user",
    "list_users",
    "get_user",
    "update_user_permissions",
    # Playlist management
    "create_playlist",
    "get_playlist",
    "list_playlists",
    "update_playlist",
    "delete_playlist",
    "add_to_playlist",
    "remove_from_playlist",
    "get_playlist_analytics",
    # Media organization
    "organize_library",
    "analyze_library",
    "fix_media_match",
    "refresh_metadata",
    "clean_bundles",
    "optimize_database",
    # Quality and transcoding
    "get_transcode_settings",
    "update_transcode_settings",
    "get_transcoding_status",
    "get_bandwidth_usage",
    "set_stream_quality",
    "get_throttling_status",
    "set_throttling",
    "list_quality_profiles",
    "create_quality_profile",
    "delete_quality_profile",
    # Library management
    "scan_library",
    "refresh_library",
    "optimize_library",
    "get_library",
    "list_libraries",
    "add_library",
    "update_library",
    "delete_library",
    "add_library_location",
    "remove_library_location",
    "empty_trash",
    "clean_library_bundles",
]
