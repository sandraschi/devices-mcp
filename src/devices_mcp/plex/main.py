#!/usr/bin/env python3
"""
Devices bundle — Plex MCP CLI entry.

Delegates to ``plex.server`` so the same ``mcp`` instance gets portmanteau tools as in ``server.py``.
"""


def main() -> None:
    """Start Plex MCP (stdio / http / sse) via shared app."""
    from .config import get_settings, setup_logging

    setup_logging()
    get_settings()

    from .server import main as server_main

    server_main()


if __name__ == "__main__":
    main()
