# FastMCP 2.14.4+ Development Best Practices

**Austrian Efficiency Guide for Professional MCP Server Development**

This document establishes best practices for building production-quality MCP servers using FastMCP 2.14.4+, optimized for rapid development with MCP Inspector integration and MCPB packaging.

## ⚠️ **Critical FastMCP 2.14.4+ Framework Rules**

### 🚨 **NEVER USE THESE - FastMCP Doesn't Support**:
- **NO "description" argument** - FastMCP framework doesn't have this parameter. Use docstrings for tool descriptions.
- **NO "parameters" in tool calls** - FastMCP handles this differently internally.
- **Errors are defined in "exceptions"** - Always use `MCPError(message=...)`, never `description=`.

### ✅ **Correct FastMCP Patterns**:
```python
# ✅ CORRECT: No description parameter
@mcp.tool()
async def example_tool(param: str) -> str:
    """Tool documentation goes in docstring, not description parameter."""
    return f"Processed: {param}"

# ❌ WRONG: Don't do this
@mcp.tool(description="This will cause errors")  # NO! FastMCP doesn't support this
async def wrong_tool(param: str) -> str:
    return f"This won't work: {param}"

# ✅ CORRECT: Error handling
try:
    result = process_data(input_data)
except Exception as e:
    raise MCPError(message=str(e), code="PROCESSING_ERROR")

# ❌ WRONG: Don't use description in errors
raise MCPError(description="Wrong pattern")  # NO! Use message parameter
```

## 🚨 **CRITICAL: Stdio Transport Integrity**

When using `stdio` transport (default for Claude Desktop/Antigravity), **NOTHING** except JSON-RPC messages can be written to `stdout`.

- **NEVER use `print()`** in production tool code or initialization.
- **NEVER use `sys.stdout.write()`** for diagnostics.
- **ALWAYS use `logging`** configured to write to `stderr`.
- **BANNER REDIRECTION**: If you have a startup banner, use `print(banner, file=sys.stderr)`.

Any plain-text string on `stdout` will pollute the JSON-RPC stream and cause clients like Antigravity to disconnect or display raw strings as "pollution".

## 🔄 **Asyncio Loop Management**

FastMCP 2.14.4+ handles the event loop internally. Starting conflicting loops in the same thread causes `RuntimeError: Already running asyncio in this thread`.

- **AVOID `asyncio.run()`** in the same thread where `mcp.run()` or `mcp.run_stdio_async()` is called.
- **PREFER Context Managers**: Use the provided FastMCP runners to ensure safe startup/shutdown.
- **LOOP DETECTION**: Robust entry points should check for existing loops or use `run_stdio_async()` if manually managing the loop.

## 🛠️ **PowerShell & Development Environment Rules**

### Core System Paths
- **Repos folder**: `D:\Dev\repos`
- **Python executable**: `C:\Users\sandr\AppData\Local\Programs\Python\Python313\python.exe`
- **Claude Config**: `C:\Users\sandr\AppData\Roaming\Claude\claude_desktop_config.json`

### PowerShell Best Practices - CRITICAL FOR RELIABILITY

#### 1. **ALWAYS Use PowerShell Cmdlets (NEVER external commands)**:
```powershell
# ✅ CORRECT:
New-Item -ItemType Directory -Path "C:\path\folder" -Force
Copy-Item -Path "source.txt" -Destination "dest.txt"
Remove-Item -Path "file.txt" -Force
Get-ChildItem -Path "C:\folder"

# ❌ NEVER USE:
mkdir folder        # Use New-Item instead
copy file.txt       # Use Copy-Item instead
del file.txt        # Use Remove-Item instead
dir                 # Use Get-ChildItem instead
```

#### 2. **ALWAYS Use File Redirect + Read Back Pattern**:
```powershell
# ✅ BASIC commands:
Command > C:\temp\output.txt; Get-Content C:\temp\output.txt

# ✅ EXTERNAL executables:
Start-Process -FilePath "npm.cmd" -ArgumentList "--version" -Wait -RedirectStandardOutput "C:\temp\npm.txt" -WindowStyle Hidden; Get-Content C:\temp\npm.txt
```

#### 3. **CRITICAL: Folder Tree Creation Rules**:
```powershell
# ✅ CORRECT - Build one folder at a time:
New-Item -ItemType Directory -Path "D:\Dev\repos\project" -Force
New-Item -ItemType Directory -Path "D:\Dev\repos\project\src" -Force
New-Item -ItemType Directory -Path "D:\Dev\repos\project\src\tools" -Force

# ❌ NEVER USE Linux syntax:
mkdir folder && mkdir folder/subfolder  # This will fail on Windows!

# ❌ NEVER USE mkdir command:
mkdir "D:\path\folder"  # Use New-Item instead
```

#### 4. **Reliability Rules**:
- **ALWAYS quote paths with spaces**: `"C:\Program Files\"`
- **TEST paths first**: `Test-Path` before operations
- **SPECIFY encoding**: `Get-Content -Encoding UTF8`
- **ADD error handling**: `-ErrorAction SilentlyContinue`
- **USE unique temp names**: `C:\temp\op_$(Get-Date -Format 'HHmmss').txt`

#### 5. **Development Commands**:
```powershell
# ✅ Use where.exe for finding executables:
where.exe python    # CORRECT
where python        # WRONG - can cause issues

# ✅ Refresh environment variables:
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User")
```

## 📦 **MCPB Packaging - SOTA 2026 Guide**

### What is MCPB?

**MCPB (MCP Builder)** is the standardized packaging system for building and distributing MCP servers. It replaces the outdated DXT format and provides a more robust, **source-first**, cross-platform distribution model.

> [!IMPORTANT]
> **COMPLETENESS REQUIREMENT**: An `.mcpb` package **MUST** contain the **complete source code** of the MCP server. It is NOT a compiled binary format; it is a source-transparent bundle designed for auditability and seamless execution.

### Essential Build Exclusions

To ensure lean, source-complete bundles, users **MUST** exclude heavy build artifacts. Create an `.mcpbignore` file in your root:

```text
# MANDATORY EXCLUSIONS
tests/
.git/
__pycache__/
.venv/
dist/
build/
target/
target_wasm/
coverage_html/
*.mcpb
.pytest_cache/
.coverage
Cargo.lock
```

> [!CAUTION]
> **TARGET DIRECTORY**: Failing to exclude `target/` or `build/` will result in massive, unrollable bundles. Always verify your `.mcpb` size (should be <10MB for typical servers).

### Core Configuration Files

#### 1. **mcpb/manifest.json** - Package Metadata:
```json
{
  "manifest_version": "0.2",
  "name": "server-name",
  "version": "1.18.1",
  "description": "Brief server description",
  "author": "Sandra Schipal",
  "license": "MIT"
}
```

#### 2. **mcpb/mcpb.json** - Build Configuration:
```json
{
  "name": "server-name",
  "version": "1.18.1",
  "type": "server",
  "runtime": "python",
  "entry_point": "src/server.py",
  "dependencies": [
    "fastmcp>=2.14.4,<3.0.0"
  ],
  "build": {
    "include": [
      "src/**/*",   // MUST include everything in src/
      "README.md",
      "LICENSE",
      "manifest.json",
      "assets/**/*"
    ],
    "exclude": [
      "tests/",
      ".git/",
      "__pycache__/",
      "*.pyc"
    ]
  }
}
```

### Build and Validation Workflow

#### 1. **Development Build**:
```powershell
# Build for local development
mcpb build --dev

# Output: dist/server-name-dev.mcpb
```

#### 2. **Production Build**:
```powershell
# Build for distribution
mcpb build --prod

# Output: dist/server-name-v1.18.1.mcpb
```

#### 3. **Package Validation**:
```powershell
# Validate package structure
mcpb validate dist/server-name-v1.18.1.mcpb
```

### Installation and Integration

Once an `.mcpb` package is generated, it can be installed into the local environment or distributed via GitHub releases.

#### Claude Desktop Integration:
```json
// claude_desktop_config.json
{
  "mcpServers": {
    "server-name": {
      "command": "python",
      "args": ["-m", "mcp_server_name.server"],
      "env": {
        "PYTHONPATH": "path/to/extracted/mcpb/src"
      }
    }
  }
}
```

## 🎯 **Core Architecture Principles**

### 1. **Modular Tool Organization**
```python
# Recommended structure for scalable MCP servers
src/your_mcp_server/
├── __init__.py
├── server.py              # Main server entry point
├── config.py              # Configuration management
├── tools/                 # Tool modules
│   ├── __init__.py
│   ├── core.py           # Essential tools (help, status, health)
│   ├── business.py       # Main business logic tools
│   ├── integrations.py   # External API integrations
│   └── debug.py          # Development and debugging tools
├── resources/             # MCP resources
│   ├── __init__.py
│   └── endpoints.py      # Resource endpoints
├── utils/                # Utilities
│   ├── __init__.py
│   ├── logging.py        # Logging configuration
│   ├── validators.py     # Input validation
│   └── helpers.py        # Helper functions
└── exceptions.py         # Custom exceptions
```

### 2. **FastMCP 2.14.4+ Server Foundation**
```python
"""Production-ready FastMCP server template."""
import asyncio
import logging
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP
from fastmcp.exceptions import MCPError
from pydantic import BaseModel, Field

# Server configuration
SERVER_CONFIG = {
    "name": "Your MCP Server",
    "version": "1.0.0",
    # NO description parameter - FastMCP doesn't support it
    "features": [
        "inspector_optimized",
        "error_tracking",
        "performance_monitoring",
        "type_safety"
    ]
}

# Initialize server with Austrian efficiency
mcp = FastMCP(**SERVER_CONFIG)

# Global state management
_server_state = {
    "startup_time": datetime.now(),
    "request_count": 0,
    "error_count": 0,
    "last_health_check": None
}
```

## 🔧 **Tool Development Patterns**

### 1. **Standard Tool Template**
```python
from typing import Any, Dict, Optional
from fastmcp.exceptions import MCPError
from pydantic import BaseModel, Field

class ToolResponse(BaseModel):
    """Standard response format for consistency."""
    success: bool
    data: Any = None
    message: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)

@mcp.tool()
async def example_business_tool(
    required_param: str,
    optional_param: Optional[int] = None,
    config_param: bool = True
) -> ToolResponse:
    """
    Business tool with Austrian efficiency patterns.

    Args:
        required_param: Description of required parameter
        optional_param: Description of optional parameter
        config_param: Boolean configuration option

    Returns:
        ToolResponse: Standardized response format

    Raises:
        MCPError: When business logic validation fails
    """
    try:
        # Input validation
        if not required_param.strip():
            raise MCPError("Required parameter cannot be empty", code="INVALID_INPUT")

        # Business logic
        result = await process_business_logic(
            required_param,
            optional_param,
            config_param
        )

        # Track metrics
        _server_state["request_count"] += 1

        return ToolResponse(
            success=True,
            data=result,
            message=f"Successfully processed: {required_param}",
            metadata={
                "processing_time": "tracked_internally",
                "request_id": f"req_{_server_state['request_count']}"
            }
        )

    except Exception as e:
        _server_state["error_count"] += 1
        logger.error(f"Tool {example_business_tool.__name__} failed: {e}")

        # Convert to MCPError for proper Inspector display
        if isinstance(e, MCPError):
            raise
        else:
            raise MCPError(
                message=f"Processing failed: {str(e)}",
                code="PROCESSING_ERROR",
                data={"original_error": type(e).__name__}
            )
```

### 2. **Error Handling Best Practices**
```python
from enum import Enum

class MCPErrorCodes(str, Enum):
    """Standardized error codes for consistency."""
    INVALID_INPUT = "INVALID_INPUT"
    AUTHENTICATION_ERROR = "AUTH_ERROR"
    RESOURCE_NOT_FOUND = "NOT_FOUND"
    EXTERNAL_API_ERROR = "EXTERNAL_API_ERROR"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    CONFIGURATION_ERROR = "CONFIG_ERROR"

def create_mcp_error(
    message: str,
    code: MCPErrorCodes,
    recoverable: bool = True,
    context: Optional[Dict[str, Any]] = None
) -> MCPError:
    """Create standardized MCP errors."""
    return MCPError(
        message=message,
        code=code.value,
        data={
            "recoverable": recoverable,
            "timestamp": datetime.now().isoformat(),
            "context": context or {}
        }
    )
```

## 🗣️ **Dialogic Tool Return Patterns**

SOTA 2026 tools should return **Dialogic Results** that combine natural language context with structured data. This pattern enables the LLM to understand the outcome while maintaining programmatic access to the result substrate.

### **The Dialogic Return Schema**
```python
class DialogicResponse(BaseModel):
    """SOTA 2026 standardized response format."""
    message: str = Field(..., description="Natural language summary for the LLM/User")
    data: Any = Field(..., description="Structured payload for programmatic consumption")
    success: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

@mcp.tool()
async def smart_home_action(action: str) -> DialogicResponse:
    """Perform action with dialogic feedback."""
    # ... logic ...
    return DialogicResponse(
        message=f"I've successfully verified that the {action} was completed.",
        data={"action": action, "timestamp": "2026-02-04T19:04:00Z"},
        success=True
    )
```

**Benefits**:
- **Zero-Friction**: The LLM doesn't need to "guess" the result from a raw list.
- **Traceability**: Structured data remains available for further tool chaining.
- **Persona Alignment**: Matches Sandra's industrial, zero-friction communication style.

## 🤖 **Advanced Sampling (Agentic Workflows)**

FastMCP 2.14.1+ introduces **Sampling** (SEP-1577), allowing the server to request "thoughts" or tool executions from the client-side LLM.

### **The Sampling Pattern**
```python
@mcp.tool()
async def autonomous_file_cleanup(directory: str) -> str:
    """Orchestrate a cleanup using the client's LLM to decide what to delete."""

    # Request a 'thought' from the client-side LLM
    response = await mcp.create_message(
        messages=[
            {
                "role": "user",
                "content": f"Analyze these files in {directory} and return a list of obsolete items."
            }
        ],
        model_preferences={"quality": "high"}
    )

    # Use the LLM's 'decision' to drive local tool execution
    obsolete_files = parse_llm_response(response.content)
    for file in obsolete_files:
        await delete_file(file)

    return f"Autonomous cleanup completed based on LLM analysis: {len(obsolete_files)} files removed."
```

### **When to Use Sampling**:
- **Complex Orchestration**: When a tool needs to make "decisions" during execution.
- **Multi-Step Workflows**: Reducing client-server round-trips for agent-led tasks.
- **Agentic File Workflows**: Autonomous organization/cleanup based on semantic analysis.

## 📝 **Basic Memory Tagging Discipline - CRITICAL QOL**

### ALWAYS tag notes with: [project-name, technology, status, priority]

Examples:
- **windows-operations-mcp work**: ["windows-operations-mcp", "powershell", "mcp", "fix", "critical"]
- **llm-txt-mcp work**: ["llm-txt-mcp", "python", "fastmcp", "completed", "high"]
- **Research notes**: ["research", "technology-name", "solution", "medium"]
- **Bug fixes**: ["project-name", "bug", "fix", "technology", "priority"]

### Memory Rules
- **Always timestamp notes** to quickly find the LAST one of the day
- **Mark outdated notes with OBSOLETE** when produced during project work
- **At chat start ALWAYS read last basic memory note** to continue work quickly

**Tag properly = find instantly. Search poorly tagged notes = waste time.**

## 📈 **Austrian Efficiency Metrics**

### Key Performance Indicators:
- **Development Speed**: 10-30x faster with Inspector + proper practices
- **Error Detection**: Real-time vs delayed log analysis
- **Tool Testing**: Interactive vs manual
- **Package Management**: MCPB distribution vs manual setup
- **Team Productivity**: Shared configurations and best practices

### Success Criteria:
- ✅ Inspector integration working
- ✅ All tools testable in browser
- ✅ Error handling visible and clear
- ✅ Performance monitoring active
- ✅ Health checks operational
- ✅ MCPB packaging functional
- ✅ Prompt templates registered
- ✅ Production deployment ready

---

*These best practices ensure your FastMCP 2.14.4+ servers are production-ready, developer-friendly, maintainable, and properly packaged at Austrian efficiency standards with comprehensive MCPB support.*
