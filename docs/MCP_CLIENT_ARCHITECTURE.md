# MCP Client Architecture

Comprehensive guide to the MCP (Model Context Protocol) client implementation in the Devices MCP platform.

## 🏗️ **Architecture Overview**

The Devices MCP platform uses a sophisticated client-server architecture where web API endpoints communicate with MCP tools through a standardized protocol. This design provides clean separation of concerns, improved testability, and enhanced maintainability.

### **Key Components**

```
┌─────────────────┐    MCP Protocol    ┌─────────────────┐
│   Web API       │◄──────────────────►│   MCP Server    │
│   Endpoints     │   (stdio/HTTP)     │   (Tools)       │
└─────────────────┘                    └─────────────────┘
         │                                      │
         │                                      │
    ┌────▼────┐                            ┌────▼────┐
    │ MCP     │                            │ Tool    │
    │ Client  │                            │ Registry│
    └─────────┘                            └─────────┘
```

## 🔄 **MCP Client Implementation**

### **Client Architecture**

```python
class MCPClient:
    """MCP client for stdio-based communication with MCP servers."""

    def __init__(self, server_command: List[str]):
        self.server_command = server_command
        self.process = None
        self._initialized = False
        self._request_id = 0

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool with arguments."""
        request = {
            "jsonrpc": "2.0",
            "id": self._get_next_request_id(),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        return await self._send_request(request)

    async def list_tools(self) -> List[Dict[str, Any]]:
        """List available MCP tools."""
        response = await self._send_request("tools/list", {})
        return response.get("result", {}).get("tools", [])
```

### **Client Manager**

```python
class MCPClientManager:
    """Manager for multiple MCP client connections."""

    def __init__(self):
        self.clients: Dict[str, MCPClient] = {}
        self._default_client: Optional[str] = None

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any],
                       client_name: Optional[str] = None) -> Dict[str, Any]:
        """Call a tool on the specified MCP client."""
        client = self.get_client(client_name)
        return await client.call_tool(tool_name, arguments)
```

### **Convenience Functions**

```python
# Global client manager instance
mcp_clients = MCPClientManager()

async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any],
                       client_name: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for calling MCP tools."""
    return await mcp_clients.call_tool(tool_name, arguments, client_name)
```

## 🛠️ **Tool Architecture**

### **Portmanteau Tools**

The platform uses "portmanteau tools" - consolidated tools that provide multiple related operations through a single interface:

```python
def register_energy_management_tool(mcp: FastMCP) -> None:
    """Register energy management portmanteau tool."""

    @mcp.tool()
    async def energy_management(
        action: Literal["status", "control", "consumption", "cost"],
        device_id: str | None = None,
        **kwargs
    ) -> dict[str, Any]:
        """Consolidated energy management operations."""
        try:
            if action == "status":
                return await get_energy_device_status()
            elif action == "control":
                return await control_energy_device(device_id, **kwargs)
            elif action == "consumption":
                return await get_energy_consumption(device_id, **kwargs)
            elif action == "cost":
                return await calculate_energy_cost(device_id, **kwargs)
        except Exception as e:
            return {"success": False, "error": str(e)}
```

### **Tool Categories**

| Category | Purpose | Actions |
|----------|---------|---------|
| `energy_management` | Smart plug & energy monitoring | status, control, consumption, cost |
| `motion_management` | Motion detection & events | status, events, subscribe, unsubscribe, test, capabilities |
| `camera_management` | Camera control & streaming | list, info, get_stream_url, capture |
| `ptz_management` | PTZ control & presets | move, stop, home, list_presets, recall_preset |
| `media_management` | Media capture & streaming | capture, start_recording, stop_recording, get_stream_url |
| `system_management` | System operations | info, status, health, logs |
| `medical_management` | Medical devices | get_device_status, scan_document |
| `security_management` | Security systems | status, nest_status, nest_alerts |
| `lighting_management` | Lighting control | list_lights, control_light, list_groups, activate_scene |

## 🌐 **Web API Integration**

### **Endpoint Pattern**

All web API endpoints follow a consistent pattern:

```python
from ...mcp_client import call_mcp_tool

@router.get("/energy/devices")
async def list_energy_devices() -> Dict[str, Any]:
    """List all energy devices via MCP."""
    try:
        result = await call_mcp_tool("energy_management", {"action": "status"})
        if result.get("success"):
            return result.get("data", result)
        else:
            raise HTTPException(status_code=500, detail=result.get("error", "MCP call failed"))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to list energy devices via MCP")
        raise HTTPException(status_code=500, detail=f"Failed to list devices: {e!s}")
```

### **Error Handling**

Consistent error handling across all endpoints:

```python
try:
    result = await call_mcp_tool(tool_name, arguments)
    if result.get("success"):
        return result.get("data", result)
    else:
        error_msg = result.get("error", "Unknown error")
        if "not found" in error_msg:
            raise HTTPException(status_code=404, detail=error_msg)
        else:
            raise HTTPException(status_code=500, detail=error_msg)
except HTTPException:
    raise
except Exception as e:
    logger.exception(f"Failed to execute {operation} via MCP")
    raise HTTPException(status_code=500, detail=f"Operation failed: {e!s}")
```

## 🧪 **Testing Infrastructure**

### **Mock MCP Server**

For comprehensive testing, we provide a mock MCP server:

```python
from tests.utils.mock_mcp_server import MockMCPServer, MockMCPClient

# Create configurable mock server
server = MockMCPServer()
server.configure_response("energy_management", "status", {
    "success": True,
    "action": "status",
    "data": {"devices": [test_device_data]}
})

# Test client
client = MockMCPClient(server)
result = await client.call_tool("energy_management", "status")
assert result["success"] is True
```

### **Test Fixtures**

Comprehensive test fixtures for MCP integration:

```python
@pytest.fixture
def mock_mcp_client():
    """Mock MCP client for testing."""
    client = AsyncMock(spec=MCPClient)
    client.call_tool.return_value = {"success": True, "data": {}}
    return client

@pytest.fixture
def mock_energy_tool_success():
    """Mock successful energy management tool response."""
    return {
        "success": True,
        "action": "status",
        "data": {"devices": [...]}
    }
```

### **Integration Testing**

End-to-end MCP integration testing:

```python
async def test_energy_workflow_integration():
    """Test complete energy management workflow."""
    server = MockMCPServer()
    client = MockMCPClient(server)

    scenario = [
        {"tool": "energy_management", "action": "status"},
        {"tool": "energy_management", "action": "consumption"},
        {"tool": "energy_management", "action": "control", "args": {"device_id": "plug1"}},
    ]

    results = await run_mcp_test_scenario(server, client, scenario)
    assert results["success"] is True
```

## 📊 **Performance Considerations**

### **Connection Management**

- **Connection Pooling**: Efficient MCP client connection management
- **Async Operations**: Non-blocking MCP tool calls
- **Resource Cleanup**: Proper cleanup of client connections

### **Optimization Strategies**

```python
# Connection reuse
client = await get_mcp_client()
result = await client.call_tool("tool_name", arguments)

# Batch operations
batch_results = await asyncio.gather(
    call_mcp_tool("tool1", args1),
    call_mcp_tool("tool2", args2),
    call_mcp_tool("tool3", args3)
)

# Caching results
@cache_async(ttl=300)  # 5 minute cache
async def get_cached_device_status(device_id: str):
    return await call_mcp_tool("energy_management", {
        "action": "status",
        "device_id": device_id
    })
```

## 🔧 **Configuration**

### **Client Configuration**

```python
# Configure MCP clients
setup_default_clients()

# Add custom client
custom_client = MCPClient(["python", "-m", "custom_mcp_server"])
mcp_clients.add_client("custom", custom_client)
```

### **Tool Registration**

```python
def setup_mcp_tools(mcp: FastMCP):
    """Register all MCP tools."""
    # Portmanteau tools
    register_energy_management_tool(mcp)
    register_motion_management_tool(mcp)
    register_camera_management_tool(mcp)
    # ... other tools
```

## 🐛 **Troubleshooting**

### **Common Issues**

#### **Connection Failures**
```python
# Check MCP server status
try:
    result = await call_mcp_tool("system_management", {"action": "status"})
    if not result.get("success"):
        logger.error(f"MCP server error: {result.get('error')}")
except Exception as e:
    logger.error(f"MCP connection failed: {e}")
```

#### **Tool Not Found**
```python
# Verify tool registration
tools = await mcp_client.list_tools()
tool_names = [tool["name"] for tool in tools]
if "energy_management" not in tool_names:
    logger.error("Energy management tool not registered")
```

#### **Timeout Issues**
```python
# Configure timeouts
import asyncio
result = await asyncio.wait_for(
    call_mcp_tool("slow_tool", args),
    timeout=30.0
)
```

### **Debugging MCP Calls**

```python
# Enable debug logging
import logging
logging.getLogger("devices_mcp.mcp_client").setLevel(logging.DEBUG)

# Inspect MCP responses
result = await call_mcp_tool("energy_management", {"action": "status"})
print(f"MCP Response: {result}")

# Test tool availability
tools = await mcp_client.list_tools()
print(f"Available tools: {[t['name'] for t in tools]}")
```

## 🔄 **Migration Guide**

### **From Direct Manager Calls**

**Before (v1.16.x):**
```python
from ...tools.energy.tapo_plug_tools import tapo_plug_manager

async def list_energy_devices():
    devices = await tapo_plug_manager.get_all_devices()
    return {"devices": devices}
```

**After (v1.17.x):**
```python
from ...mcp_client import call_mcp_tool

async def list_energy_devices():
    result = await call_mcp_tool("energy_management", {"action": "status"})
    if result.get("success"):
        return result.get("data", result)
    else:
        raise HTTPException(status_code=500, detail=result.get("error"))
```

### **Benefits of Migration**

- **Consistency**: All APIs use the same communication pattern
- **Testability**: Easier to mock and test MCP interactions
- **Maintainability**: Centralized tool management
- **Scalability**: Better support for multiple MCP servers
- **Reliability**: Improved error handling and connection management

## 📚 **Related Documentation**

- [API Documentation](../API_DOCUMENTATION.md) - Complete API reference
- [Testing Guide](../tests/README.md) - Comprehensive testing infrastructure
- [CI/CD Pipeline](../.github/workflows/ci-comprehensive.yml) - Automated testing pipeline
- [Portmanteau Tools](../docs/portmanteau-tools/) - Tool implementation details
