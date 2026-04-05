# Claude Desktop Debugging Guide

## Overview

This guide covers debugging MCP servers when using Claude Desktop as the client. Claude Desktop provides excellent debugging capabilities through its logging system and STDIO protocol.

## Claude Desktop Logs

### Finding Log Files

**Windows**:
```
%APPDATA%\Claude\logs\
```

**macOS**:
```
~/Library/Logs/Claude/
```

**Linux**:
```
~/.config/claude/logs/
```

### Log File Types

- `claude-desktop.log` - Main application log
- `mcp-server-name.log` - Individual MCP server logs
- `claude-desktop-error.log` - Error-specific logs

## MCP Server Configuration

### Basic Configuration
```json
{
  "mcpServers": {
    "your-server": {
      "command": "python",
      "args": ["-m", "your_mcp_server"],
      "env": {
        "API_KEY": "your-api-key",
        "DEBUG": "true"
      }
    }
  }
}
```

### Debug Configuration
```json
{
  "mcpServers": {
    "your-server": {
      "command": "python",
      "args": ["-m", "your_mcp_server", "--debug"],
      "env": {
        "LOG_LEVEL": "DEBUG",
        "VERBOSE": "true"
      }
    }
  }
}
```

## Debugging Techniques

### 1. Enable Verbose Logging

**Python MCP Server**:
```python
import logging
import sys

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),  # Send to stderr for Claude Desktop
        logging.FileHandler('mcp_server.log')
    ]
)

logger = logging.getLogger(__name__)

@mcp.tool()
def debug_tool(param: str) -> str:
    logger.debug(f"Tool called with param: {param}")
    try:
        result = process_param(param)
        logger.info(f"Tool completed successfully: {result}")
        return result
    except Exception as e:
        logger.error(f"Tool failed: {e}", exc_info=True)
        raise
```

### 2. STDIO Protocol Debugging

**Enable Protocol Logging**:
```python
import json
import sys

def log_protocol_message(message: dict, direction: str):
    """Log MCP protocol messages"""
    print(f"[{direction}] {json.dumps(message)}", file=sys.stderr)

# In your MCP server
def handle_request(request: dict):
    log_protocol_message(request, "RECV")
    response = process_request(request)
    log_protocol_message(response, "SEND")
    return response
```

### 3. Error Handling and Reporting

**Comprehensive Error Handling**:
```python
from fastmcp import FastMCP
import traceback

mcp = FastMCP("your-server")

@mcp.tool()
def robust_tool(param: str) -> str:
    """Tool with detailed error reporting"""
    try:
        # Validate input
        if not param:
            raise ValueError("Parameter cannot be empty")

        # Process with detailed logging
        logger.info(f"Processing parameter: {param}")
        result = complex_processing(param)
        logger.info(f"Processing completed: {result}")

        return result

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        return f"Error: {e}"
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f"Error: {str(e)}"
```

## Common Debugging Scenarios

### 1. Server Not Starting

**Symptoms**:
- Claude Desktop shows "Server not responding"
- No logs appearing

**Debug Steps**:
```bash
# Test server manually
python -m your_mcp_server

# Check for import errors
python -c "import your_mcp_server"

# Verify dependencies
pip list | grep fastmcp
```

**Log Analysis**:
```
[ERROR] Failed to start MCP server: ModuleNotFoundError
[ERROR] Import error in your_mcp_server
```

### 2. Tools Not Appearing

**Symptoms**:
- Server starts but no tools visible
- Empty tool list in Claude Desktop

**Debug Steps**:
```python
# Add tool registration logging
@mcp.tool()
def test_tool() -> str:
    """Test tool for debugging"""
    return "Tool is working"

# Log registered tools
logger.info(f"Registered tools: {list(mcp.list_tools().keys())}")
```

**Log Analysis**:
```
[INFO] Registering tool: test_tool
[INFO] Tool registration complete: ['test_tool']
```

### 3. Tool Execution Failures

**Symptoms**:
- Tools appear but fail when called
- Error messages in Claude Desktop

**Debug Steps**:
```python
@mcp.tool()
def debug_tool(param: str) -> str:
    """Tool with execution debugging"""
    logger.info(f"Tool execution started with: {param}")

    try:
        # Step-by-step logging
        logger.debug("Step 1: Input validation")
        validated_param = validate_input(param)

        logger.debug("Step 2: Processing")
        result = process_data(validated_param)

        logger.debug("Step 3: Formatting output")
        formatted_result = format_output(result)

        logger.info(f"Tool execution completed: {formatted_result}")
        return formatted_result

    except Exception as e:
        logger.error(f"Tool execution failed at step: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise
```

### 4. Performance Issues

**Symptoms**:
- Slow tool responses
- Timeouts

**Debug Steps**:
```python
import time
import asyncio

@mcp.tool()
async def performance_tool(data: str) -> str:
    """Tool with performance monitoring"""
    start_time = time.time()
    logger.info(f"Tool started at {start_time}")

    try:
        # Log each step timing
        step_start = time.time()
        processed_data = await process_data(data)
        step_time = time.time() - step_start
        logger.info(f"Data processing took {step_time:.2f}s")

        step_start = time.time()
        result = await format_result(processed_data)
        step_time = time.time() - step_start
        logger.info(f"Result formatting took {step_time:.2f}s")

        total_time = time.time() - start_time
        logger.info(f"Total tool execution time: {total_time:.2f}s")

        return result

    except asyncio.TimeoutError:
        logger.error("Tool execution timed out")
        raise
    except Exception as e:
        logger.error(f"Performance issue: {e}")
        raise
```

## Advanced Debugging

### 1. Protocol-Level Debugging

**Enable Full Protocol Logging**:
```python
import json
import sys
from typing import Dict, Any

class ProtocolLogger:
    def __init__(self):
        self.request_count = 0

    def log_request(self, request: Dict[str, Any]):
        self.request_count += 1
        print(f"[REQ {self.request_count}] {json.dumps(request, indent=2)}",
              file=sys.stderr)

    def log_response(self, response: Dict[str, Any]):
        print(f"[RESP {self.request_count}] {json.dumps(response, indent=2)}",
              file=sys.stderr)

protocol_logger = ProtocolLogger()

# Use in your MCP server
def handle_mcp_request(request: Dict[str, Any]) -> Dict[str, Any]:
    protocol_logger.log_request(request)

    try:
        response = process_mcp_request(request)
        protocol_logger.log_response(response)
        return response
    except Exception as e:
        error_response = {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }
        protocol_logger.log_response(error_response)
        return error_response
```

### 2. Memory and Resource Debugging

**Resource Monitoring**:
```python
import psutil
import os
import gc

@mcp.tool()
def resource_monitor() -> str:
    """Monitor server resources"""
    process = psutil.Process(os.getpid())

    memory_info = {
        "rss": process.memory_info().rss / 1024 / 1024,  # MB
        "vms": process.memory_info().vms / 1024 / 1024,  # MB
        "percent": process.memory_percent()
    }

    cpu_percent = process.cpu_percent()

    # Force garbage collection
    gc.collect()

    logger.info(f"Memory usage: {memory_info}")
    logger.info(f"CPU usage: {cpu_percent}%")

    return f"Memory: {memory_info['rss']:.1f}MB, CPU: {cpu_percent:.1f}%"
```

### 3. Network Debugging

**API Call Debugging**:
```python
import aiohttp
import asyncio

@mcp.tool()
async def api_debug_tool(url: str) -> str:
    """Debug API calls"""
    logger.info(f"Making API call to: {url}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response headers: {dict(response.headers)}")

                content = await response.text()
                logger.info(f"Response content length: {len(content)}")

                return f"Status: {response.status}, Length: {len(content)}"

    except aiohttp.ClientError as e:
        logger.error(f"API call failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in API call: {e}")
        raise
```

## Log Analysis Tips

### 1. Filtering Logs

**Search for specific patterns**:
```bash
# Find all errors
grep "ERROR" claude-desktop.log

# Find MCP server logs
grep "your-server" claude-desktop.log

# Find tool execution logs
grep "Tool execution" mcp-server-name.log
```

### 2. Log Rotation

**Configure log rotation**:
```python
import logging
from logging.handlers import RotatingFileHandler

# Set up rotating file handler
handler = RotatingFileHandler(
    'mcp_server.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[handler]
)
```

### 3. Structured Logging

**Use structured logging for better analysis**:
```python
import json
import logging

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)

# Configure structured logging
handler = logging.StreamHandler()
handler.setFormatter(StructuredFormatter())
logger = logging.getLogger()
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)
```

## Troubleshooting Checklist

- [ ] Check Claude Desktop logs for MCP server errors
- [ ] Verify MCP server configuration in Claude Desktop
- [ ] Test MCP server manually outside Claude Desktop
- [ ] Check for import errors and missing dependencies
- [ ] Verify tool registration and parameter validation
- [ ] Monitor resource usage (memory, CPU)
- [ ] Check network connectivity for API calls
- [ ] Validate input parameters and error handling
- [ ] Review protocol-level communication logs
- [ ] Test with minimal tool implementations

## Best Practices

1. **Always log tool entry and exit**
2. **Use structured logging for better analysis**
3. **Include request/response IDs in logs**
4. **Log performance metrics**
5. **Handle errors gracefully with detailed logging**
6. **Use debug levels appropriately**
7. **Monitor resource usage**
8. **Test tools individually before integration**
9. **Keep logs readable and searchable**
10. **Use log rotation to manage disk space**

Remember: Good logging is essential for debugging MCP servers in production environments.
