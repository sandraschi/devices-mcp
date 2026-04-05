"""FastMCP 3.1+ server setup for Plex MCP (Legacy - Use server.py instead).

This module is kept for backward compatibility but is deprecated.
Use plex_mcp.server:main as the entry point instead.
"""

import logging
from typing import Optional

# Import portmanteau tools to register them
# This ensures all @mcp.tool() decorators execute
from .tools import portmanteau  # noqa: F401

# Legacy imports - these may not exist, so we handle gracefully
try:
    from .tools import (
        control_playback,
        get_library_items,
        get_media_info,
        get_server_info,
        get_server_status,
        list_clients,
        list_libraries,
        list_sessions,
        plex_audio_mgr,
        search_media,
    )
except ImportError:
    # Old tools don't exist - use portmanteau tools instead
    control_playback = None
    get_library_items = None
    get_media_info = None
    get_server_info = None
    get_server_status = None
    list_clients = None
    list_libraries = None
    list_sessions = None
    plex_audio_mgr = None
    search_media = None

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Legacy PlexMCP class - deprecated, use server.py instead
# Tools are now registered via @mcp.tool() decorators in portmanteau modules


def run_server(config_path: Optional[str] = None):
    """Run the Plex MCP server (Legacy - redirects to server.py).

    Args:
        config_path: Optional path to a configuration file (ignored, use env vars)

    Note: This function is deprecated. Use plex_mcp.server:main instead.
    """
    import warnings

    warnings.warn(
        "mcp_setup.run_server is deprecated. Use plex_mcp.server:main instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    # Redirect to main server entry point
    from .server import main

    main()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Plex MCP server")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    args = parser.parse_args()

    run_server(config_path=args.config)
