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
    "add_library",
    "add_library_location",
    "add_to_playlist",
    "analyze_library",
    "clean_bundles",
    "clean_library_bundles",
    "control_playback",
    # Playlist management
    "create_playlist",
    "create_quality_profile",
    # User management
    "create_user",
    "delete_library",
    "delete_playlist",
    "delete_quality_profile",
    "delete_user",
    "empty_trash",
    "fix_media_match",
    "get_bandwidth_usage",
    "get_library",
    "get_media_info",
    "get_playlist",
    "get_playlist_analytics",
    "get_server_info",
    # Server tools
    "get_server_status",
    "get_throttling_status",
    # Quality and transcoding
    "get_transcode_settings",
    "get_transcoding_status",
    "get_user",
    "list_clients",
    "list_libraries",
    "list_playlists",
    "list_quality_profiles",
    # Session tools
    "list_sessions",
    "list_users",
    "optimize_database",
    "optimize_library",
    # Media organization
    "organize_library",
    "plex_audio_mgr",
    "refresh_library",
    "refresh_metadata",
    "remove_from_playlist",
    "remove_library_location",
    # Library management
    "scan_library",
    # Media tools
    "search_media",
    "set_stream_quality",
    "set_throttling",
    "update_library",
    "update_playlist",
    "update_transcode_settings",
    "update_user",
    "update_user_permissions",
]
