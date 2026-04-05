import os
import sys

# Add src to path
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

try:
    from devices_mcp.tools import base_tool

    # Check if register_tool exists
    if hasattr(base_tool, "register_tool"):
        pass
    else:
        pass

    # Check if tools_registry exists
    if hasattr(base_tool, "tools_registry"):
        pass
    else:
        pass

except ImportError:
    import traceback

    traceback.print_exc()
