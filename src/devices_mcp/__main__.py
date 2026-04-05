#!/usr/bin/env python3
"""
Main entry point for the Devices MCP server.
"""

import asyncio
import logging
import sys

# Suppress FastMCP internal logging to prevent INFO logs from appearing as errors in Cursor
# FastMCP writes to stderr, and Cursor interprets stderr as errors
for logger_name in [
    "mcp",
    "mcp.server",
    "mcp.server.lowlevel",
    "mcp.server.lowlevel.server",
    "fastmcp",
]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

from .core.server import main as server_main


def main():
    """Run the Devices MCP server."""
    try:
        asyncio.run(server_main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user")
        sys.exit(0)
    except Exception:
        logging.exception("Error running server")
        sys.exit(1)


if __name__ == "__main__":
    main()
