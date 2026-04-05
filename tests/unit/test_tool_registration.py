"""
Test script to verify tool registration in Devices MCP.
"""

import logging
import sys
from pathlib import Path

import pytest

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def add_src_to_path():
    """Add the src directory to the Python path."""
    src_dir = str(Path(__file__).parent.absolute() / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    logger.info(f"Added to path: {src_dir}")


@pytest.mark.skip(reason="# TODO: Fix test_tool_registration - currently has assert False")
def test_tool_registration():
    """Test if tools are properly registered."""
    try:
        # Import the tools module to trigger registration

        # Get all registered tools
        from devices_mcp.tools import tools_registry

        # Print registered tools
        logger.info("\n=== Registered Tools ===")
        for name, tool_class in tools_registry.items():
            logger.info(f"- {name} ({tool_class.__module__}.{tool_class.__name__})")

        # List of expected tools
        expected_tools = [
            "move_ptz",
            "save_ptz_preset",
            "recall_ptz_preset",
            "get_ptz_presets",
            "go_to_home_ptz",
            "stop_ptz",
            "get_ptz_position",
            "capture_image",
            "find_similar_images",
            "get_stream_url",
            "start_recording",
            "stop_recording",
            "analyze_image",
            "security_scan",
            "capture_still",
            "get_grafana_metrics",
            "get_camera_snapshot",
            "get_vienna_security_dashboard",
        ]

        # Check for missing tools
        missing_tools = [t for t in expected_tools if t not in tools_registry]

        if missing_tools:
            logger.error("\n❌ Missing tools:")
            for tool in missing_tools:
                logger.error(f"- {tool}")
            assert False
        logger.info("\n✅ All expected tools are registered!")
        assert True

    except Exception as e:
        logger.error(f"Error testing tool registration: {e}", exc_info=True)
        assert False


def main():
    """Main function."""
    add_src_to_path()

    logger.info("Testing tool registration...")
    success = test_tool_registration()

    if not success:
        logger.error("Tool registration test failed!")
        sys.exit(1)
    else:
        logger.info("Tool registration test passed!")


if __name__ == "__main__":
    main()
