"""
PlexMCP API Package

This package contains all API endpoints for the PlexMCP application,
organized into logical modules for better maintainability.

Note: The FastMCP instance is created in the parent server module.
API modules import it from there to register their tools.
"""

# Re-export API modules for convenience
from . import admin, core, playback, playlists, vienna

__all__ = ["admin", "core", "playback", "playlists", "vienna"]
