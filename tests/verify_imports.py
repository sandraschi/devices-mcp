"""
Verify imports for Devices MCP tools.
"""

import logging
import sys

logger = logging.getLogger(__name__)
from pathlib import Path

# Add the src directory to the Python path
src_dir = str(Path(__file__).parent.absolute() / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# List of modules to test
modules_to_test = [
    "devices_mcp.tools.camera",
    "devices_mcp.tools.system",
    "devices_mcp.tools.ptz",
    "devices_mcp.tools.media",
    "devices_mcp.tools.grafana",
]

# Test each module
for module_name in modules_to_test:
    try:
        logger.info(f"Testing import: {module_name}")
        __import__(module_name, fromlist=["*"])
        logger.info(f"SUCCESS: Successfully imported {module_name}")
    except ImportError as e:
        logger.info(f"ERROR Failed to import {module_name}: {e}")
        import traceback

        traceback.print_exc()
    except Exception as e:
        logger.info(f"WARNING Error importing {module_name}: {e}")
        import traceback

        traceback.print_exc()
    print("-" * 80)
