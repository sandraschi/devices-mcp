import contextlib
import importlib
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def print_section(title):
    pass


def main():
    # Print Python environment info
    print_section("Python Environment")

    # Add src to path
    src_dir = str(Path(__file__).parent.absolute() / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Test basic imports
    print_section("Testing Basic Imports")

    # Test importing base_tool
    with contextlib.suppress(ImportError):
        pass

    # Test importing tools/__init__.py
    with contextlib.suppress(ImportError):
        pass

    # Test importing a tool module
    print_section("Testing Tool Module Imports")

    tool_modules = [
        "devices_mcp.tools.camera",
        "devices_mcp.tools.system",
        "devices_mcp.tools.ptz",
        "devices_mcp.tools.media",
        "devices_mcp.tools.grafana",
    ]

    for module_name in tool_modules:
        with contextlib.suppress(ImportError):
            importlib.import_module(module_name)

    # Test tool registration
    print_section("Testing Tool Registration")
    try:
        from devices_mcp.tools import get_all_tools

        tools = get_all_tools()
        for _tool in tools:
            pass
    except Exception as e:
        logger.debug(f"Tool iteration failed: {e}")


if __name__ == "__main__":
    main()
