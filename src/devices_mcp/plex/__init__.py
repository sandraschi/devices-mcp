"""PlexMCP - Production Plex Media Server MCP Integration"""

__version__ = "2.0.0"
__author__ = "Sandra Schipal"

# Single source of truth for imports
from .config import get_settings
from .main import main
from .services.plex_service import PlexService

__all__ = ["PlexService", "get_settings", "main"]
