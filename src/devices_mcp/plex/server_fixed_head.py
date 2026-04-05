"""
PlexMCP - FastMCP 2.1 Server for Plex Media Server Management

Austrian efficiency for Sandra's media streaming needs.
Provides 22 tools: 10 core + 3 playlist + 2 remote + 2 performance + 2 admin + 3 Austrian efficiency
"""

import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP
from rich.console import Console

# Import our utility modules
from .utils import get_logger

# Set up logger
logger = get_logger(__name__)

# Robust import handling for both package and direct execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Try relative imports first (when run as package)
    from .config import PlexConfig
    from .plex_manager import PlexAPIError, PlexManager
except ImportError:
    try:
        # Try absolute imports (when run directly)
        from plex_mcp.config import PlexConfig  # noqa: F401
        from plex_mcp.plex_manager import PlexAPIError, PlexManager  # noqa: F401
    except ImportError:
        # Final fallback - direct imports from same directory
        pass

# Load environment variables from multiple possible paths
import pathlib

possible_env_paths = [
    pathlib.Path(__file__).parent.parent.parent / ".env",  # repo root
    pathlib.Path.cwd() / ".env",  # current working directory
    pathlib.Path("D:/Dev/repos/plexmcp/.env"),  # absolute path fallback
]

for env_path in possible_env_paths:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break
else:
    load_dotenv()  # fallback

# Initialize console for logging (redirect to stderr for MCP compatibility)
console = Console(file=sys.stderr)

# Initialize FastMCP server
mcp = FastMCP("PlexMCP 🎬")
