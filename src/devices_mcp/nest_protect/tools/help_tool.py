"""Help tools for Nest Protect MCP."""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


def _get_tool_category(tool_name: str) -> str:
    """Categorize tools by functionality."""
    device_status = ["list_devices", "get_device_status", "get_device_events"]
    device_control = [
        "hush_alarm",
        "run_safety_check",
        "set_led_brightness",
        "sound_alarm",
        "arm_disarm_security",
    ]
    system_status = ["get_system_status", "get_process_status", "get_api_status"]
    help_tools = [
        "list_available_tools",
        "get_tool_help",
        "search_tools",
        "about_server",
        "get_supported_devices",
    ]
    auth_tools = [
        "initiate_oauth_flow",
        "handle_oauth_callback",
        "refresh_access_token",
    ]
    config_tools = [
        "get_config",
        "update_config",
        "reset_config",
        "export_config",
        "import_config",
    ]

    if tool_name in device_status:
        return "Device Status"
    if tool_name in device_control:
        return "Device Control"
    if tool_name in system_status:
        return "System Status"
    if tool_name in help_tools:
        return "Help & Documentation"
    if tool_name in auth_tools:
        return "Authentication"
    if tool_name in config_tools:
        return "Configuration"
    return "Other"


def _generate_usage_examples(tool_name: str, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate usage examples for a tool based on its parameters."""
    examples = []

    # Basic example with minimal required parameters
    required_params = {
        name: info for name, info in parameters.items() if info.get("required", False)
    }

    if required_params:
        basic_example = {
            "description": "Basic usage with required parameters",
            "parameters": {},
        }
        for param_name, param_info in required_params.items():
            if param_info["type"] == "string":
                if "device" in param_name.lower():
                    basic_example["parameters"][param_name] = "device-123"
                elif "file" in param_name.lower() or "path" in param_name.lower():
                    basic_example["parameters"][param_name] = "/path/to/file"
                else:
                    basic_example["parameters"][param_name] = f"example_{param_name}"
            elif param_info["type"] == "integer":
                basic_example["parameters"][param_name] = param_info.get("minimum", 1)
            elif param_info["type"] == "boolean":
                basic_example["parameters"][param_name] = True
            elif param_info["type"] == "array":
                basic_example["parameters"][param_name] = ["example"]
        examples.append(basic_example)
    else:
        examples.append({"description": "No parameters required", "parameters": {}})

    # Advanced example with optional parameters
    if len(parameters) > len(required_params):
        advanced_example = {
            "description": "Advanced usage with optional parameters",
            "parameters": {},
        }
        for param_name, param_info in parameters.items():
            if param_info["type"] == "string":
                if "enum" in param_info:
                    advanced_example["parameters"][param_name] = param_info["enum"][0]
                elif "device" in param_name.lower():
                    advanced_example["parameters"][param_name] = "device-456"
                else:
                    advanced_example["parameters"][param_name] = f"advanced_{param_name}"
            elif param_info["type"] == "integer":
                advanced_example["parameters"][param_name] = param_info.get("maximum", 100)
            elif param_info["type"] == "boolean":
                advanced_example["parameters"][param_name] = False
        examples.append(advanced_example)

    return examples


class ToolHelpParams(BaseModel):
    """Parameters for getting tool help."""

    tool_name: str = Field(..., description="Name of the tool to get help for")


class SearchToolsParams(BaseModel):
    """Parameters for searching tools."""

    query: str = Field(..., description="Search query")
    search_in: List[str] = Field(["name", "description"], description="Fields to search in")


async def list_available_tools() -> Dict[str, Any]:
    """List all available tools with their descriptions."""
    # Import here to avoid circular imports
    from ..fastmcp_server import app

    try:
        # Get tools from FastMCP app (3.x: list_tools returns list)
        tools_list = await app.list_tools()
        tools = []

        for tool_obj in tools_list:
            tool_name = getattr(tool_obj, "name", str(tool_obj))
            # Get input schema (FastMCP 3.x tool may have parameters schema)
            if hasattr(tool_obj, "parameters") and hasattr(tool_obj.parameters, "model_json_schema"):
                input_schema = tool_obj.parameters.model_json_schema()
            elif hasattr(tool_obj, "to_mcp_tool"):
                mcp_tool = tool_obj.to_mcp_tool()
                input_schema = getattr(mcp_tool, "inputSchema", {})
            else:
                input_schema = {}

            # Extract parameter info from the nested schema
            params_ref = input_schema.get("properties", {}).get("params", {})
            if "$ref" in params_ref:
                # Get the referenced schema from $defs
                ref_name = params_ref["$ref"].split("/")[
                    -1
                ]  # Get 'EmptyParams' from '#/$defs/EmptyParams'
                param_schema = input_schema.get("$defs", {}).get(ref_name, {})
            else:
                param_schema = params_ref

            tools.append(
                {
                    "name": tool_name,
                    "description": getattr(tool_obj, "description", "") or "",
                    "parameters": param_schema.get("properties", {}),
                    "required": param_schema.get("required", []),
                    "category": _get_tool_category(tool_name),
                }
            )

        # Group by category
        categories = {}
        for tool in tools:
            cat = tool["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(tool)

        return {
            "status": "success",
            "count": len(tools),
            "categories": {k: sorted(v, key=lambda x: x["name"]) for k, v in categories.items()},
            "tools": sorted(tools, key=lambda x: x["name"]),
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to list tools: {e!s}"}


async def get_tool_help(tool_name: str) -> Dict[str, Any]:
    """Get detailed help for a specific tool with comprehensive information."""
    from ..fastmcp_server import app

    try:
        # Get tools from FastMCP app (3.x: list_tools returns list)
        tools_list = await app.list_tools()
        tool_obj = next((t for t in tools_list if getattr(t, "name", None) == tool_name), None)

        if tool_obj is None:
            return {"status": "error", "message": f"Tool '{tool_name}' not found"}

        if hasattr(tool_obj, "parameters") and hasattr(tool_obj.parameters, "model_json_schema"):
            input_schema = tool_obj.parameters.model_json_schema()
        elif hasattr(tool_obj, "to_mcp_tool"):
            mcp_tool = tool_obj.to_mcp_tool()
            input_schema = getattr(mcp_tool, "inputSchema", {})
        else:
            input_schema = {}

        # Extract parameter info from the nested schema
        params_ref = input_schema.get("properties", {}).get("params", {})
        if "$ref" in params_ref:
            # Get the referenced schema from $defs
            ref_name = params_ref["$ref"].split("/")[-1]
            param_schema = input_schema.get("$defs", {}).get(ref_name, {})
        else:
            param_schema = params_ref

        properties = param_schema.get("properties", {})
        required = param_schema.get("required", [])

        # Build detailed parameter info
        parameters = {}
        for param_name, param_schema in properties.items():
            param_info = {
                "type": param_schema.get("type", "string"),
                "description": param_schema.get("description", "No description"),
                "required": param_name in required,
            }

            # Add additional schema properties
            if "default" in param_schema:
                param_info["default"] = param_schema["default"]
            if "enum" in param_schema:
                param_info["allowed_values"] = param_schema["enum"]
            if "minimum" in param_schema:
                param_info["minimum"] = param_schema["minimum"]
            if "maximum" in param_schema:
                param_info["maximum"] = param_schema["maximum"]
            if "items" in param_schema:
                param_info["array_items"] = param_schema["items"]

            parameters[param_name] = param_info

        # Generate usage examples
        examples = _generate_usage_examples(tool_name, parameters)

        return {
            "status": "success",
            "tool": tool_name,
            "description": getattr(tool_obj, "description", "") or "",
            "category": _get_tool_category(tool_name),
            "parameters": parameters,
            "required_parameters": required,
            "usage_examples": examples,
            "full_schema": param_schema,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get help for tool '{tool_name}': {e!s}",
        }


async def search_tools(
    query: str, search_in: List[str] = ["name", "description"]
) -> Dict[str, Any]:
    """Search for tools by keyword or description with advanced filtering."""
    from ..fastmcp_server import app

    try:
        query = query.lower()
        results = []

        # Get tools from FastMCP app (3.x: list_tools returns list)
        tools_list = await app.list_tools()

        for tool_obj in tools_list:
            tool_name = getattr(tool_obj, "name", str(tool_obj))
            match = False
            match_type = []

            # Search in name
            if "name" in search_in and query in tool_name.lower():
                match = True
                match_type.append("name")

            # Search in description
            description = getattr(tool_obj, "description", "") or ""
            if "description" in search_in and query in description.lower():
                match = True
                match_type.append("description")

            # Search in parameter names and descriptions
            if "parameters" in search_in:
                mcp_tool = tool_obj.to_mcp_tool()
                input_schema = mcp_tool.inputSchema

                # Extract parameter info from the nested schema
                params_ref = input_schema.get("properties", {}).get("params", {})
                if "$ref" in params_ref:
                    ref_name = params_ref["$ref"].split("/")[-1]
                    param_schema = input_schema.get("$defs", {}).get(ref_name, {})
                else:
                    param_schema = params_ref

                properties = param_schema.get("properties", {})

                for param_name, param_schema in properties.items():
                    if query in param_name.lower():
                        match = True
                        match_type.append("parameter_name")
                        break

                    param_desc = param_schema.get("description", "")
                    if query in param_desc.lower():
                        match = True
                        match_type.append("parameter_description")
                        break

            # Search in category
            if "category" in search_in:
                category = _get_tool_category(tool_name)
                if query in category.lower():
                    match = True
                    match_type.append("category")

            if match:
                mcp_tool = tool_obj.to_mcp_tool()
                input_schema = mcp_tool.inputSchema

                # Extract parameter info from the nested schema
                params_ref = input_schema.get("properties", {}).get("params", {})
                if "$ref" in params_ref:
                    ref_name = params_ref["$ref"].split("/")[-1]
                    param_schema = input_schema.get("$defs", {}).get(ref_name, {})
                else:
                    param_schema = params_ref

                results.append(
                    {
                        "name": tool_name,
                        "description": description,
                        "category": _get_tool_category(tool_name),
                        "parameters": list(param_schema.get("properties", {}).keys()),
                        "match_type": match_type,
                        "relevance_score": len(match_type),  # Simple relevance scoring
                    }
                )

        # Sort by relevance score (descending) then by name
        results.sort(key=lambda x: (-x["relevance_score"], x["name"]))

        return {
            "status": "success",
            "query": query,
            "search_in": search_in,
            "count": len(results),
            "results": results,
        }
    except Exception as e:
        return {"status": "error", "message": f"Search failed: {e!s}"}
