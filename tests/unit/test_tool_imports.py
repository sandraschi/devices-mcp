"""
Test script to verify tool imports and registration.
"""

import logging
import sys
from pathlib import Path

import pytest

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def add_src_to_path():
    """Add the src directory to the Python path."""
    src_dir = str(Path(__file__).parent.absolute() / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    logger.info(f"Added to path: {src_dir}")


@pytest.mark.skip(reason="# TODO: Fix test_import - currently has assert False")
def test_import(module_name):
    """Test importing a module and print the result."""
    try:
        __import__(module_name)
        logger.info(f"✅ Successfully imported: {module_name}")
        assert True
    except ImportError:
        logger.exception(f"❌ Failed to import {module_name}")
        import traceback

        traceback.print_exc()
        assert False
    except Exception:
        logger.exception(f"⚠️ Error importing {module_name}")
        import traceback

        traceback.print_exc()
        assert False


def main():
    """Main function to test imports."""
    add_src_to_path()

    # Test importing the tools package
    test_import("devices_mcp.tools")

    # Test importing tool modules
    modules_to_test = [
        "devices_mcp.tools.camera",
        "devices_mcp.tools.system",
        "devices_mcp.tools.ptz",
        "devices_mcp.tools.media",
        "devices_mcp.tools.grafana",
    ]

    for module in modules_to_test:
        test_import(module)

    # Test tool registration
    try:
        from devices_mcp.tools import get_all_tools

        tools = get_all_tools()
        logger.info("\n=== Registered Tools ===")
        for tool in tools:
            logger.info(f"- {tool.name}: {tool.__module__}.{tool.__name__}")
    except Exception:
        logger.exception("Failed to get registered tools")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
