#!/usr/bin/env python3
"""
Devices MCP Server v2 - Fixed asyncio handling for Claude Desktop integration
Provides camera control capabilities through MCP protocol
"""

import logging
import os
import sys
import warnings

# Defer Tapo import to avoid PyO3 initialization issues
# Will be imported in main() after Python interpreter is ready
Tapo = None

# Suppress warnings to prevent noise in logs
os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Configure enhanced logging (to stderr - won't corrupt MCP stdout JSON-RPC)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stderr),
    ],
)

logger = logging.getLogger(__name__)

# Apply patch for ring_doorbell imports (optional - Ring integration)
# Done AFTER logging is configured so messages are visible
try:
    from . import patch_ring_doorbell

    patch_ring_doorbell.patch_ring_doorbell()
except Exception as e:
    logger.warning(f"Ring patch skipped: {e}")

# Re-export Tapo for tests
# PLW0127: Self-assignment is intentional for re-export pattern
Tapo = Tapo

# Import and re-export TapoCameraServer for tests


def main():
    """Main entry point with unified transport handling (FastMCP 3.1+)"""
    import asyncio

    from .transport import create_argument_parser, resolve_transport

    logger.info("=== Devices MCP SERVER STARTUP ===")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Command line args: {sys.argv}")

    # Use standardized parser with Tapo-specific additions
    parser = create_argument_parser("devices-mcp")
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Use direct stdio mode (legacy, prefer --stdio for Claude Desktop)",
    )
    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info(f"Parsed arguments: {vars(args)}")

    # Resolve transport (handles --stdio, --http, --sse, env vars)
    # --direct is legacy alias for --stdio
    if args.direct:
        args.stdio = True

    transport = resolve_transport(args)
    logger.info(f"Resolved transport: {transport.upper()}")

    try:

        async def run_server():
            """Initialize and run the Devices MCP server"""
            logger.info("Initializing DevicesMCPServer...")
            from devices_mcp.core.server import DevicesMCPServer

            server = await DevicesMCPServer.get_instance()
            logger.info("DevicesMCPServer initialized successfully")

            # Map to legacy server.run() parameters
            # TODO: Migrate TapoCameraServer.run() to use transport.py directly
            if transport == "stdio":
                logger.info("Starting server in STDIO mode...")
                await server.run(
                    host=args.host or "127.0.0.1", port=args.port or 8000, stdio=True, direct=True
                )
            elif transport in ("http", "sse"):
                logger.info(f"Starting server in {transport.upper()} mode...")
                await server.run(
                    host=args.host or "127.0.0.1", port=args.port or 8000, stdio=False, direct=False
                )

        logger.info("Starting Devices MCP Server...")
        asyncio.run(run_server())

    except KeyboardInterrupt:
        logger.info("=== SERVER SHUTDOWN REQUESTED (Ctrl+C) ===")
        sys.exit(0)
    except Exception:
        logger.exception("=== SERVER FAILED TO START ===")
        logger.exception("Error type:")
        sys.exit(1)

    logger.info("=== MAIN FUNCTION COMPLETE ===")


if __name__ == "__main__":
    main()
