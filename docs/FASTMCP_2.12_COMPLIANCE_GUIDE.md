# FastMCP 2.12 Compliance Guide

**Note:** This project now targets **FastMCP 3.1+**. The patterns below still apply; tool structure and registration are compatible.

This document outlines the compliance standards for FastMCP 2.12 in the Devices MCP project (retained for reference).

## Tool Registration Standards

### 1. Tool Decorator Usage

All tools must use the `@tool()` decorator with proper naming:

```python
from ...tools.base_tool import BaseTool, ToolCategory, tool

@tool("tool_name")
class MyTool(BaseTool):
    """Tool description without triple quotes inside."""

    class Meta:
        name = "tool_name"
        description = "Tool description"
        category = ToolCategory.UTILITY

        class Parameters:
            param1: str = Field(..., description="Parameter description")
            param2: Optional[int] = Field(None, description="Optional parameter")
```

### 2. Required Meta Class Structure

Every tool must have a `Meta` class with:

- `name`: Tool identifier (must match decorator)
- `description`: Brief description of tool functionality
- `category`: One of the ToolCategory enum values
- `Parameters`: Pydantic model for tool parameters

### 3. Docstring Standards

- Use single-line or multi-line docstrings
- **NO triple quotes (`"""`) inside docstrings**
- Include parameter descriptions and return value information
- Provide usage examples where helpful

### 4. Parameter Definition

Parameters must be defined in the `Meta.Parameters` class using Pydantic Field:

```python
class Parameters:
    required_param: str = Field(..., description="Required parameter")
    optional_param: Optional[int] = Field(None, description="Optional parameter")
    default_param: bool = Field(default=True, description="Parameter with default")
```

### 5. Execute Method Requirements

All tools must implement an async `execute` method:

```python
async def execute(self, **kwargs) -> Dict[str, Any]:
    """Execute the tool with given parameters."""
    try:
        # Tool implementation
        return {"status": "success", "data": result}
    except Exception as e:
        logger.exception("Tool execution failed: %s", e)
        return {"error": str(e)}
```

## Category Standards

Use appropriate ToolCategory enum values:

- `ToolCategory.CAMERA`: Camera control and monitoring
- `ToolCategory.SECURITY`: Security and alarm systems
- `ToolCategory.UTILITY`: General utility tools
- `ToolCategory.ANALYSIS`: Analytics and reporting
- `ToolCategory.SYSTEM`: System management
- `ToolCategory.MEDIA`: Media handling
- `ToolCategory.PTZ`: PTZ control
- `ToolCategory.CONFIGURATION`: Configuration management

## Error Handling

All tools must implement proper error handling:

```python
async def execute(self, **kwargs) -> Dict[str, Any]:
    try:
        # Tool logic
        return {"status": "success", "result": data}
    except Exception as e:
        logger.exception("Tool execution failed: %s", e)
        return {"error": str(e)}
```

## Tool Categories in Devices MCP

### Energy Management Tools
- `get_smart_plug_status`: Tapo P115 smart plug status
- `control_smart_plug`: Control smart plug power state
- `get_energy_consumption`: Energy consumption data
- `get_energy_cost_analysis`: Cost analysis and savings
- `set_energy_automation`: Automation rules
- `get_tapo_p115_detailed_stats`: Detailed P115 statistics
- `set_tapo_p115_energy_saving_mode`: Energy saving mode
- `get_tapo_p115_power_schedule`: Power schedules
- `get_tapo_p115_data_storage_info`: Data storage capabilities

### Alarm System Tools
- `get_nest_protect_status`: Nest Protect device status
- `get_nest_protect_alerts`: Recent alerts and notifications
- `test_nest_protect_device`: Device testing
- `get_nest_protect_battery_status`: Battery monitoring
- `correlate_nest_camera_events`: Event correlation

### Analytics Tools
- `performance_analyzer`: System performance analysis
- `scene_analyzer`: AI-powered scene analysis

### Automation Tools
- `smart_automation`: Intelligent automation system

## Validation Checklist

Before submitting tools, ensure:

- [ ] `@tool()` decorator is present
- [ ] Meta class has all required fields
- [ ] Parameters class defines all parameters with Field()
- [ ] Docstring has no triple quotes inside
- [ ] Execute method is async and returns Dict[str, Any]
- [ ] Proper error handling with try/except
- [ ] Appropriate ToolCategory is used
- [ ] Tool is registered in appropriate `__init__.py`

## Migration from Legacy Tools

To migrate existing tools to FastMCP 2.12:

1. Add `@tool()` decorator
2. Create `Meta` class with required fields
3. Move parameters to `Meta.Parameters` class
4. Update docstrings to remove triple quotes
5. Ensure async execute method
6. Update imports to include `ToolCategory` and `tool`

## Example: Complete Tool Implementation

```python
"""
Example FastMCP 2.12 compliant tool.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from ...tools.base_tool import BaseTool, ToolCategory, tool

@tool("example_tool")
class ExampleTool(BaseTool):
    """Example tool demonstrating FastMCP 2.12 compliance.

    This tool provides an example of proper FastMCP 2.12 tool
    implementation with all required components.

    Parameters:
        input_param: Input parameter description
        optional_param: Optional parameter description

    Returns:
        Dict with tool execution results
    """

    class Meta:
        name = "example_tool"
        description = "Example tool demonstrating FastMCP 2.12 compliance"
        category = ToolCategory.UTILITY

        class Parameters:
            input_param: str = Field(..., description="Input parameter description")
            optional_param: Optional[int] = Field(None, description="Optional parameter description")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the example tool."""
        try:
            input_param = kwargs.get("input_param")
            optional_param = kwargs.get("optional_param")

            # Tool logic here
            result = {"processed": input_param, "optional": optional_param}

            return {
                "status": "success",
                "result": result,
                "timestamp": "2025-01-16T10:30:00Z"
            }

        except Exception as e:
            logger.exception("Example tool execution failed: %s", e)
            return {"error": str(e)}
```

This guide ensures all tools in the Devices MCP project maintain FastMCP 2.12 compliance and provide consistent, reliable functionality.
