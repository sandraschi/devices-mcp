import logging
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def add_src_to_path():
    """Add the src directory to the Python path."""
    src_dir = str(Path(__file__).parent.absolute() / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    logger.info(f"Added to path: {src_dir}")


def check_imports():
    """Check if we can import the required modules."""
    modules = [
        "devices_mcp.tools.camera",
        "devices_mcp.tools.system",
        "devices_mcp.tools.ptz",
        "devices_mcp.tools.media",
        "devices_mcp.tools.grafana",
    ]

    for module in modules:
        try:
            __import__(module)
            logger.info(f"✅ {module} imports successfully")
        except Exception:
            logger.exception("❌ Failed to import module")
            import traceback

            traceback.print_exc()


def check_tool_registration():
    """Check if tools are properly registered."""
    try:
        from devices_mcp.tools import tools_registry

        logger.info("\n=== Registered Tools ===")
        if not tools_registry:
            logger.warning("No tools registered!")
        else:
            for name, tool in tools_registry.items():
                logger.info(f"- {name}: {tool.__module__}.{tool.__name__}")
    except Exception:
        logger.exception("Failed to check tool registration")


def main():
    add_src_to_path()
    logger.info("=== Checking Imports ===")
    check_imports()
    check_tool_registration()


if __name__ == "__main__":
    main()
