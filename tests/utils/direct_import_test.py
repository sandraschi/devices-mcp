"""
Direct import test for Devices MCP tool modules.
"""

import sys
from pathlib import Path


def add_src_to_path():
    """Add the src directory to the Python path."""
    src_dir = str(Path(__file__).parent.absolute() / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)


def test_import(module_name):
    """Test importing a module and print the result."""
    try:
        module = __import__(module_name, fromlist=["*"])

        # Print available attributes if any
        if hasattr(module, "__all__"):
            pass

        return True
    except ImportError:
        import traceback

        traceback.print_exc()
        return False
    except Exception:
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main function to test imports."""
    add_src_to_path()

    # List of modules to test
    modules_to_test = [
        "devices_mcp.tools.camera",
        "devices_mcp.tools.system",
        "devices_mcp.tools.ptz",
        "devices_mcp.tools.media",
        "devices_mcp.tools.grafana",
    ]

    # Test each module
    results = {}
    for module in modules_to_test:
        results[module] = test_import(module)

    # Print summary
    for _module, _success in results.items():
        pass

    # Return non-zero exit code if any import failed
    if not all(results.values()):
        sys.exit(1)
    else:
        pass


if __name__ == "__main__":
    main()
