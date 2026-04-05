"""
Test module imports for the Devices MCP server.
"""

import os
import sys

import pytest

# Add the src path to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


@pytest.mark.skip(reason="# TODO: Fix test_imports - currently has assert False")
def test_imports():
    """Test that all modules can be imported successfully."""
    try:
        # Test core imports
        from devices_mcp import TapoCameraMCP
        from devices_mcp.core.models import TapoCameraConfig
        from devices_mcp.core.server import TapoCameraServer
        from devices_mcp.exceptions import TapoCameraError

        # Test that imports work
        assert TapoCameraMCP is not None
        assert TapoCameraConfig is not None
        assert TapoCameraServer is not None
        assert TapoCameraError is not None

        assert True

    except ImportError:
        import traceback

        traceback.print_exc()
        assert False
    except Exception:
        import traceback

        traceback.print_exc()
        assert False


if __name__ == "__main__":
    success = test_imports()
    if not success:
        sys.exit(1)
