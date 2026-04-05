"""Entry point for running the web server as a module."""

import argparse
import logging
import sys
from pathlib import Path

# Add src directory to path so webapp can import from MCP package
repo_root = Path(__file__).parent.parent.parent
src_path = repo_root / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Import server_new directly to avoid relative import issues
from .server_new import WebServer

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Devices MCP Web Server")
        parser.add_argument("--host", default="0.0.0.0", help="Host to bind the server to")
        parser.add_argument(
            "--port",
            type=int,
            default=10716,
            help="Port to bind the server to",
        )
        parser.add_argument("--debug", action="store_true", help="Enable debug mode")

        args = parser.parse_args()

        # Setup basic logging
        logging.basicConfig(
            level=logging.INFO if not args.debug else logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        logger.info("=" * 80)
        logger.info("Devices MCP Web Server - Starting")
        logger.info(f"Python: {sys.version.split()[0]}")
        logger.info(f"Platform: {sys.platform}")
        logger.info(f"Working directory: {Path.cwd()}")
        logger.info(f"Host: {args.host}")
        logger.info(f"Port: {args.port}")
        logger.info("=" * 80)

        # Create and run the server
        server = WebServer()
        server.run(host=args.host, port=args.port)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
