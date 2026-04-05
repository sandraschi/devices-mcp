"""
PlexMCP - FastMCP 3.1 Server for Plex Media Server Management

FastMCP 3.1 compliant with conversational tool returns and sampling capabilities.
Austrian efficiency for Sandra's media streaming needs.
"""

# Import the shared FastMCP instance
from .app import mcp

# Set up logger
from .utils import get_logger

logger = get_logger(__name__)

# Import portmanteau tools to register them with the MCP server
# The @mcp.tool() decorators execute when modules are imported
from .tools import portmanteau  # noqa: F401

# Import and register agentic workflow tools (FastMCP 3.1 sampling features)
from .tools.agentic import register_agentic_tools

register_agentic_tools()

# NOTE: Old individual tools (server, media, sessions, users, playlists, organization, quality, library)
# are deprecated and will be removed in a future version.
# Use portmanteau tools instead:
# - plex_library (replaces library.py)
# - plex_media (replaces media.py)
# - plex_user (replaces users.py)
# - plex_playlist (replaces playlists.py)
# - plex_streaming (replaces sessions.py)
# - plex_performance (replaces quality.py, server.py)
# - plex_metadata (replaces organization.py)
# - plex_organization (replaces organization.py)
# - plex_server (replaces server.py)
# - plex_integration (replaces api/vienna.py)
# - plex_search (new advanced search)
# - plex_reporting (new reporting/analytics)
# - plex_collections (new collections management)
# - plex_quality (replaces quality profile tools)
# - plex_help (new help/discovery)


def main():
    """
    Main entry point for PlexMCP server with FastMCP 3.1 conversational features.

    Supports both HTTP and STDIO (JSON-RPC) modes based on command line arguments.
    When run without arguments, defaults to STDIO mode (FastMCP 3.1 default).

    FEATURES:
    - Conversational tool returns for natural AI interaction
    - Sampling capabilities for agentic workflows
    - Portmanteau tools for comprehensive media management

    For STDIO mode (default in FastMCP 3.1): python -m plex_mcp.server
    For HTTP mode: python -m plex_mcp.server --http
    """
    import argparse

    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="PlexMCP - Austrian efficiency for media streaming"
    )
    parser.add_argument(
        "--stdio", action="store_true", help="Run in STDIO (JSON-RPC) mode (default)"
    )
    parser.add_argument("--http", action="store_true", help="Run in HTTP mode")
    parser.add_argument("--sse", action="store_true", help="Run in SSE mode (deprecated)")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (HTTP/SSE mode only)")
    parser.add_argument(
        "--port", type=int, default=10763, help="Port to listen on (HTTP/SSE mode only)"
    )
    parser.add_argument("--path", default="/mcp", help="Path for HTTP mode")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    args = parser.parse_args()

    # Determine transport mode - default to stdio if no transport specified
    if args.http:
        transport_mode = "http"
    elif args.sse:
        transport_mode = "sse"
    else:
        transport_mode = "stdio"  # Default in FastMCP 2.10+

    # Log startup to stderr for visibility
    logger.info("Starting FastMCP 2.10+ Server - Austrian efficiency for media streaming!")
    logger.info(f"Transport: {transport_mode.upper()}")

    # Run server with FastMCP 2.10+ syntax
    try:
        if transport_mode == "stdio":
            # STDIO mode (default) - no additional parameters needed
            logger.info("Running in STDIO mode - Ready for Claude Desktop!")
            mcp.run()  # stdio is default in FastMCP 2.10+

        elif transport_mode == "http":
            # HTTP mode (streamable HTTP)
            logger.info(f"Running in HTTP mode on http://{args.host}:{args.port}{args.path}")
            mcp.run(transport="http", host=args.host, port=args.port, path=args.path)

        elif transport_mode == "sse":
            # SSE mode (deprecated but still supported)
            logger.info(f"Running in SSE mode on http://{args.host}:{args.port} (deprecated)")
            mcp.run(transport="sse", host=args.host, port=args.port)

    except Exception:
        logger.exception("Failed to start server:")
        raise


if __name__ == "__main__":
    main()
