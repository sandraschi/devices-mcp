"""Error handling utilities for PlexMCP.

Provides standardized error handling and formatting for MCP tools
to ensure consistent, AI-friendly error messages across all operations.
"""

from typing import Any


def handle_tool_error(
    exception: Exception,
    operation: str | None = None,
    parameters: dict[str, Any] | None = None,
    tool_name: str = "unknown_tool",
    context: str = "",
) -> dict[str, Any]:
    """Standardized error handler for MCP tools.

    This function should be used in the except block of all @mcp.tool()
    decorated functions to ensure consistent error handling and reporting.

    Args:
        exception: The exception that was caught
        operation: Optional operation name (for portmanteau tools)
        parameters: Optional dict of parameters that were passed to the tool
        tool_name: Name of the tool where error occurred
        context: Additional context about what was happening when error occurred

    Returns:
        Standardized error response dictionary

    Examples:
        @mcp.tool()
        async def my_tool(param: str) -> Dict[str, Any]:
            try:
                result = await do_something(param)
                return {"success": True, "data": result}
            except Exception as e:
                return handle_tool_error(
                    exception=e,
                    parameters={"param": param},
                    tool_name="my_tool",
                    context="Processing user request"
                )
    """
    # Determine error type
    error_type = type(exception).__name__
    error_message = str(exception)

    # Build base error response
    error_response: dict[str, Any] = {
        "success": False,
        "error": error_message,
        "error_type": error_type,
        "tool_name": tool_name,
    }

    # Add operation if specified (for portmanteau tools)
    if operation:
        error_response["operation"] = operation

    # Add context if provided
    if context:
        error_response["context"] = context

    # Add parameters if provided (helpful for debugging)
    if parameters:
        error_response["parameters"] = parameters

    # Get suggestions based on error type
    suggestions = get_error_suggestions(exception, tool_name, operation)
    if suggestions:
        error_response["suggestions"] = suggestions

    # Add related tools that might help
    related_tools = get_related_tools(exception, tool_name)
    if related_tools:
        error_response["related_tools"] = related_tools

    # Add traceback in development/debug mode (optional)
    # Uncomment for debugging:
    # error_response["traceback"] = traceback.format_exc()

    return error_response


def format_error_response(
    error_msg: str,
    error_code: str,
    suggestions: list[str] | None = None,
    related_tools: list[str] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Format a custom error response with suggestions.

    Use this when you want to return a custom error message rather than
    catching an exception.

    Args:
        error_msg: Clear, actionable error message
        error_code: Specific error code (e.g., "INVALID_MEDIA_ID")
        suggestions: List of suggestions for fixing the error
        related_tools: List of related tools that might help
        **kwargs: Additional fields to include in response

    Returns:
        Formatted error response dictionary

    Examples:
        return format_error_response(
            error_msg="Media ID must be an integer",
            error_code="INVALID_MEDIA_ID",
            suggestions=[
                "Use list_media() to find valid media IDs",
                "Use search_media() to search by title"
            ],
            related_tools=["plex_media", "plex_search"]
        )
    """
    response = {
        "success": False,
        "error": error_msg,
        "error_code": error_code,
    }

    if suggestions:
        response["suggestions"] = suggestions

    if related_tools:
        response["related_tools"] = related_tools

    # Add any additional fields
    response.update(kwargs)

    return response


def get_error_suggestions(exception: Exception, tool_name: str, operation: str | None = None) -> list[str]:
    """Get contextual suggestions based on error type.

    Args:
        exception: The exception that occurred
        tool_name: Name of the tool
        operation: Optional operation name

    Returns:
        List of suggestions for resolving the error
    """
    suggestions = []
    error_type = type(exception).__name__
    error_msg = str(exception).lower()

    # Connection errors
    if error_type in ("ConnectionError", "TimeoutError", "ConnectTimeout"):
        suggestions.extend(
            [
                "Check that Plex Media Server is running",
                "Verify PLEX_SERVER_URL is correct in configuration",
                "Ensure network connectivity to Plex server",
                "Check firewall settings",
            ]
        )

    # Authentication errors
    elif "401" in error_msg or "unauthorized" in error_msg or "authentication" in error_msg:
        suggestions.extend(
            [
                "Verify PLEX_TOKEN is correct and not expired",
                "Check that token has necessary permissions",
                "Generate a new Plex authentication token",
            ]
        )

    # Not found errors
    elif error_type == "FileNotFoundError" or "404" in error_msg or "not found" in error_msg:
        suggestions.extend(
            [
                "Verify the resource exists using list/search operations",
                "Check that IDs or paths are correct",
                "Ensure the resource hasn't been deleted",
            ]
        )

    # Invalid input errors
    elif error_type in ("ValueError", "TypeError"):
        suggestions.extend(
            [
                "Check parameter types match expected values",
                "Verify all required parameters are provided",
                "Review tool documentation for correct usage",
            ]
        )

    # Permission errors
    elif error_type == "PermissionError" or "403" in error_msg or "forbidden" in error_msg:
        suggestions.extend(
            [
                "Check that user has necessary permissions",
                "Verify token has admin rights if required",
                "Ensure resource is accessible to current user",
            ]
        )

    # General fallback
    if not suggestions:
        suggestions.append(f"Check tool documentation for {tool_name}")
        if operation:
            suggestions.append(f"Verify parameters for '{operation}' operation")

    return suggestions


def get_related_tools(exception: Exception, tool_name: str) -> list[str]:
    """Get related tools that might help resolve the error.

    Args:
        exception: The exception that occurred
        tool_name: Name of the tool where error occurred

    Returns:
        List of related tool names
    """
    related = []
    error_msg = str(exception).lower()

    # Suggest search/list tools for not found errors
    if "not found" in error_msg or "404" in error_msg:
        if "media" in tool_name:
            related.extend(["plex_media", "plex_search"])
        elif "library" in tool_name:
            related.extend(["plex_library"])
        elif "user" in tool_name:
            related.extend(["plex_user"])

    # Suggest server status tool for connection errors
    if "connection" in error_msg or "timeout" in error_msg:
        related.append("plex_server")

    return related


def create_success_response(data: Any, message: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Create a standardized success response.

    Args:
        data: The data to return
        message: Optional success message
        **kwargs: Additional fields to include in response

    Returns:
        Standardized success response dictionary

    Examples:
        return create_success_response(
            data=media_list,
            message="Found 25 media items",
            count=25
        )
    """
    response = {
        "success": True,
        "data": data,
    }

    if message:
        response["message"] = message

    # Add any additional fields
    response.update(kwargs)

    return response
