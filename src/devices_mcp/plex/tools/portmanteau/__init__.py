"""
PlexMCP Portmanteau Tools Package

This package contains all portmanteau tools that consolidate related operations
into single, user-friendly interfaces. Each tool uses an `operation` parameter
with Literal types to specify the action to perform.

Portmanteau tools follow the FastMCP 2.13+ standards with:
- Comprehensive multiline docstrings
- AI-friendly error messages
- Proper type hints with Literal operation parameters

NOTE: These tools are being added ALONGSIDE existing individual tools.
Both approaches work simultaneously. Old tools will be deprecated gradually
after thorough testing and user migration.
"""

# Import implemented portmanteau tools
from .audio_mgr import plex_audio_mgr
from .collections import plex_collections
from .help import plex_help
from .integration import plex_integration
from .library import plex_library
from .media import plex_media
from .metadata import plex_metadata
from .organization import plex_organization
from .performance import plex_performance
from .playlist import plex_playlist
from .quality import plex_quality
from .reporting import plex_reporting
from .search import plex_search
from .server import plex_server
from .streaming import plex_streaming
from .user import plex_user

__all__ = [
    "plex_audio_mgr",
    "plex_collections",
    "plex_help",
    "plex_integration",
    "plex_library",
    "plex_media",
    "plex_metadata",
    "plex_organization",
    "plex_performance",
    "plex_playlist",
    "plex_quality",
    "plex_reporting",
    "plex_search",
    "plex_server",
    "plex_streaming",
    "plex_user",
]
