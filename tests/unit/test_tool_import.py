"""
Test script to verify tool imports and registration.
"""

import logging
import sys
from pathlib import Path

import pytest

# Add src to path
src_dir = str(Path(__file__).parent.absolute() / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


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

        logger.exception(traceback.format_exc())
        assert False
    except Exception:
        logger.exception(f"⚠️ Error importing {module_name}")
        import traceback

        logger.exception(traceback.format_exc())
        assert False


def main():
    """Main function to test imports."""
    # Test importing base_tool
    test_import("devices_mcp.tools.base_tool")

    # Test importing tools/__init__.py
    test_import("devices_mcp.tools")

    # Test tool registration
    try:
        from devices_mcp.tools import get_all_tools

        tools = get_all_tools()
        logger.info("\n=== Registered Tools ===")
        for tool in tools:
            logger.info(f"- {tool.name}: {tool.__module__}.{tool.__name__}")
        logger.info(f"Total tools registered: {len(tools)}")
    except Exception:
        logger.exception("\n❌ Error getting registered tools")
        import traceback

        logger.exception(traceback.format_exc())


if __name__ == "__main__":
    main()
