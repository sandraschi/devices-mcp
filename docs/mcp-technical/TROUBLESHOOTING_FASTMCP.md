# FastMCP Troubleshooting Guide

## Common Issues & Solutions

### 1. Import Errors

**Problem**: `ModuleNotFoundError` when importing FastMCP components

**Solution**:
```bash
# Ensure FastMCP is installed
pip install fastmcp

# Check installation
python -c "import fastmcp; print(fastmcp.__version__)"
```

### 2. Tool Registration Issues

**Problem**: Tools not appearing in Claude Desktop

**Solution**:
```python
# Ensure proper tool registration
from fastmcp import FastMCP

mcp = FastMCP("server-name")

@mcp.tool()
def my_tool(param: str) -> str:
    """Tool description"""
    return f"Result: {param}"

# Verify tool registration
print(mcp.list_tools())
```

### 3. Async/Await Problems

**Problem**: `RuntimeError: cannot be called from a running event loop`

**Solution**:
```python
# Use proper async patterns
import asyncio
from fastmcp import FastMCP

mcp = FastMCP("server-name")

@mcp.tool()
async def async_tool(param: str) -> str:
    """Async tool"""
    await asyncio.sleep(0.1)  # Example async operation
    return f"Async result: {param}"
```

### 4. Pydantic Validation Errors

**Problem**: `ValidationError` for tool parameters

**Solution**:
```python
from pydantic import BaseModel, Field
from fastmcp import FastMCP

mcp = FastMCP("server-name")

class ToolInput(BaseModel):
    param: str = Field(..., description="Required parameter")
    optional_param: int = Field(0, description="Optional parameter")

@mcp.tool()
def validated_tool(input_data: ToolInput) -> str:
    """Tool with validated input"""
    return f"Processed: {input_data.param}"
```

### 5. Resource Management Issues

**Problem**: Memory leaks or unclosed connections

**Solution**:
```python
from contextlib import asynccontextmanager
from fastmcp import FastMCP

mcp = FastMCP("server-name")

@asynccontextmanager
async def resource_manager():
    # Setup
    resource = await create_resource()
    try:
        yield resource
    finally:
        # Cleanup
        await resource.close()

@mcp.tool()
async def resource_tool() -> str:
    """Tool with proper resource management"""
    async with resource_manager() as resource:
        return await resource.process()
```

### 6. Configuration Problems

**Problem**: Environment variables not loading

**Solution**:
```python
import os
from fastmcp import FastMCP

# Load configuration
config = {
    "api_key": os.getenv("API_KEY"),
    "base_url": os.getenv("BASE_URL", "https://api.example.com"),
    "timeout": int(os.getenv("TIMEOUT", "30"))
}

mcp = FastMCP("server-name", config=config)
```

### 7. Error Handling Issues

**Problem**: Unhandled exceptions crashing the server

**Solution**:
```python
from fastmcp import FastMCP
import logging

mcp = FastMCP("server-name")
logger = logging.getLogger(__name__)

@mcp.tool()
def robust_tool(param: str) -> str:
    """Tool with comprehensive error handling"""
    try:
        # Main logic
        result = process_data(param)
        return result
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return f"Error: Invalid input - {e}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return f"Error: {str(e)}"
```

### 8. Performance Issues

**Problem**: Slow tool execution

**Solution**:
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastmcp import FastMCP

mcp = FastMCP("server-name")

# Use thread pool for CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=4)

@mcp.tool()
async def cpu_intensive_tool(data: str) -> str:
    """Tool with async CPU-bound processing"""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(executor, cpu_bound_function, data)
    return result
```

### 9. Logging Configuration

**Problem**: No logs or unclear logging

**Solution**:
```python
import logging
from fastmcp import FastMCP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

mcp = FastMCP("server-name")
logger = logging.getLogger(__name__)

@mcp.tool()
def logged_tool(param: str) -> str:
    """Tool with proper logging"""
    logger.info(f"Processing tool with param: {param}")
    try:
        result = process_param(param)
        logger.info(f"Tool completed successfully")
        return result
    except Exception as e:
        logger.error(f"Tool failed: {e}")
        raise
```

### 10. Testing Issues

**Problem**: Tools not testable or hard to test

**Solution**:
```python
import pytest
from fastmcp import FastMCP

# Create testable MCP instance
def create_test_mcp():
    return FastMCP("test-server")

def test_tool():
    """Test tool functionality"""
    mcp = create_test_mcp()

    @mcp.tool()
    def test_tool(param: str) -> str:
        return f"Test: {param}"

    # Test the tool
    result = test_tool("test_input")
    assert result == "Test: test_input"
```

## Debugging Tips

### 1. Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. Use Claude Desktop Logs
- Check Claude Desktop logs for MCP server output
- Look for error messages and stack traces

### 3. Test Tools Individually
```python
# Test tools outside of MCP context
def test_tool_directly():
    result = my_tool("test_input")
    print(f"Tool result: {result}")
```

### 4. Validate Configuration
```python
# Check configuration loading
print(f"API Key: {os.getenv('API_KEY', 'NOT_SET')}")
print(f"Base URL: {config.get('base_url')}")
```

## Quick Fixes for Common Projects

### FastMCP Version Issues
```bash
# Update to latest version
pip install --upgrade fastmcp

# Check version compatibility
python -c "import fastmcp; print(fastmcp.__version__)"
```

### Environment Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "server-name": {
      "command": "python",
      "args": ["-m", "your_mcp_server"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

## Getting Help

1. **Check FastMCP Documentation**: [FastMCP Docs](https://github.com/pydantic/fastmcp)
2. **Review Error Logs**: Enable debug logging and check Claude Desktop logs
3. **Test Incrementally**: Build and test tools one at a time
4. **Use Type Hints**: Ensure all parameters have proper type annotations
5. **Validate Input**: Use Pydantic models for parameter validation

## Best Practices

- Always use type hints for tool parameters
- Implement comprehensive error handling
- Use async/await for I/O operations
- Manage resources properly with context managers
- Log important operations and errors
- Test tools individually before integration
- Use environment variables for configuration
- Follow FastMCP patterns and conventions

Remember: FastMCP is designed to be simple, but proper error handling and resource management are crucial for production use.
