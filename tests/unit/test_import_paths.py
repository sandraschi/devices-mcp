import logging
import os
import sys
from pathlib import Path

import pytest

# Set up logging
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def add_src_to_path():
    """Add the src directory to the Python path."""
    src_dir = str(Path(__file__).parent.absolute() / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    logger.info(f"Added to path: {src_dir}")
    return src_dir


@pytest.mark.skip(reason="# TODO: Fix test_import - currently has assert False")
def test_import(module_name):
    """Test importing a module and print the result."""
    logger.info(f"\n=== Testing import of {module_name} ===")
    try:
        module = __import__(module_name, fromlist=["*"])
        logger.info(f"✅ Successfully imported {module_name}")

        # List available attributes
        attrs = [attr for attr in dir(module) if not attr.startswith("_")]
        logger.info(f"Available attributes: {', '.join(attrs)}")

        # Try to get the module's file path
        try:
            file_path = getattr(module, "__file__", "Unknown")
            logger.info(f"Module file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not get module file path: {e}")

        assert True
    except ImportError:
        logger.exception(f"❌ Failed to import {module_name}")
        import traceback

        logger.exception(traceback.format_exc())
        assert False
    except Exception:
        logger.exception(f"⚠️ Unexpected error importing {module_name}")
        import traceback

        logger.exception(traceback.format_exc())
        assert False


def main():
    """Main function to test imports."""
    src_dir = add_src_to_path()

    # List all Python files in the devices_mcp directory
    tapo_dir = os.path.join(src_dir, "devices_mcp")
    logger.info(f"\n=== Contents of {tapo_dir} ===")
    for root, _dirs, files in os.walk(tapo_dir):
        level = root.replace(tapo_dir, "").count(os.sep)
        indent = " " * 4 * level
        logger.info(f"{indent}{os.path.basename(root)}/")
        subindent = " " * 4 * (level + 1)
        for f in files:
            if f.endswith(".py"):
                logger.info(f"{subindent}{f}")

    # Test importing base_tool first
    test_import("devices_mcp.tools.base_tool")

    # Try to import tools/__init__.py
    test_import("devices_mcp.tools")

    # Try to import a tool module directly
    test_import("devices_mcp.tools.camera")

    # Try to import a tool class directly
    try:
        from devices_mcp.tools.camera.camera_tools import ConnectCameraTool

        logger.info("✅ Successfully imported ConnectCameraTool")
        assert ConnectCameraTool is not None
    except ImportError:
        logger.exception("❌ Failed to import ConnectCameraTool")
        import traceback

        logger.exception(traceback.format_exc())


if __name__ == "__main__":
    main()
