import asyncio
import os
import sys
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(os.getcwd()) / "src"))

from devices_mcp.core.server import DevicesMCPServer


async def inspect():
    print("Getting DevicesMCPServer instance...")
    server = await DevicesMCPServer.get_instance(skip_hardware_init=True)

    print(f"Server initialized: {server._initialized}")
    print(f"Has MCP attribute: {hasattr(server, 'mcp')}")

    if hasattr(server, "mcp"):
        mcp = server.mcp
        print(f"MCP type: {type(mcp)}")

        # Check tools (FastMCP 3.x: list_tools returns list)
        if hasattr(mcp, "list_tools") and callable(mcp.list_tools):
            tools = await mcp.list_tools() if asyncio.iscoroutinefunction(mcp.list_tools) else mcp.list_tools()
            print(f"Tools via list_tools(): {len(tools)}")
            for t in tools[:20]:
                print(f"  - {getattr(t, 'name', t)}")
            if len(tools) > 20:
                print(f"  ... and {len(tools) - 20} more")
        elif hasattr(mcp, "_tools"):
            print(f"Tools in mcp._tools: {len(mcp._tools)}")
            for name in list(mcp._tools)[:20]:
                print(f"  - {name}")
        else:
            print("No list_tools() or _tools found on FastMCP instance")


if __name__ == "__main__":
    asyncio.run(inspect())
