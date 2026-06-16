"""
PlexMCP Server Management Portmanteau Tool

Consolidates all server management operations into a single comprehensive interface.
FastMCP 2.13+ compliant with comprehensive docstrings and AI-friendly error messages.
"""

import os
from typing import Any, Literal

from ...app import mcp
from ...utils import get_logger

logger = get_logger(__name__)


def _get_plex_service():
    """Get PlexService instance with proper environment variable handling."""
    from ...services.plex_service import PlexService

    base_url = os.getenv("PLEX_URL") or os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    token = os.getenv("PLEX_TOKEN")

    if not token:
        raise RuntimeError(
            "PLEX_TOKEN environment variable is required. "
            "Get your token from Plex Web App (Settings → Account → Authorized Devices) "
            "or visit https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/ "
            "for detailed instructions."
        )

    return PlexService(base_url=base_url, token=token)


@mcp.tool()
async def plex_server(
    operation: Literal[
        "status",
        "info",
        "health",
        "maintenance",
        "restart",
        "update",
    ],
    maintenance_operation: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Comprehensive server management operations for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 6+ separate tools (one per operation), this tool consolidates related
    server management operations into a single interface. This design:
    - Prevents tool explosion (6+ tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with server management tasks
    - Enables consistent server interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - status: Get current server status
    - info: Get comprehensive server information
    - health: Get detailed server health and performance metrics
    - maintenance: Run server maintenance operations
    - restart: Restart the Plex server (placeholder for future implementation)
    - update: Update the Plex server (placeholder for future implementation)

    OPERATIONS DETAIL:

    status: Get current server status
    - Parameters: None required
    - Returns: Server status information
    - Example: plex_server(operation="status")
    - Use when: Checking server health and basic status

    info: Get comprehensive server information
    - Parameters: None required
    - Returns: Combined server status and library information
    - Example: plex_server(operation="info")
    - Use when: Getting complete server overview

    health: Get detailed server health and performance metrics
    - Parameters: None required
    - Returns: Server health information
    - Example: plex_server(operation="health")
    - Use when: Monitoring server performance and health

    maintenance: Run server maintenance operations
    - Parameters: maintenance_operation (required), options (optional)
    - Returns: Maintenance results
    - Example: plex_server(operation="maintenance", maintenance_operation="optimize", options={})
    - Use when: Performing server maintenance tasks

    restart: Restart the Plex server
    - Parameters: None required
    - Returns: Restart confirmation
    - Example: plex_server(operation="restart")
    - Use when: Restarting the server (NOTE: May not be fully supported by Plex API)

    update: Update the Plex server
    - Parameters: None required
    - Returns: Update status
    - Example: plex_server(operation="update")
    - Use when: Updating server software (NOTE: May not be fully supported by Plex API)

    Prerequisites:
        - Plex Media Server running and accessible
        - Valid PLEX_TOKEN environment variable set
        - Admin/owner permissions for maintenance/restart/update operations

    Args:
        operation (str): The server operation to perform. Required. Must be one of: "status", "info", "health", "maintenance", "restart", "update"
        maintenance_operation (str | None): Type of maintenance to perform (required for maintenance).
        options (dict | None): Additional options for maintenance.

    Returns:
        Dictionary containing:
            - success: Boolean indicating operation success
            - operation: The operation that was performed
            - data: Operation-specific result data
            - error: Error message if success is False
            - error_code: Specific error code for programmatic handling
            - suggestions: List of suggested fixes (on error)

    Examples:
        # Get server status
        result = await plex_server(operation="status")
        # Returns: {'success': True, 'operation': 'status', 'data': {...}}

        # Get server info
        result = await plex_server(operation="info")
        # Returns: {'success': True, 'operation': 'info', 'data': {...}}

        # Get server health
        result = await plex_server(operation="health")
        # Returns: {'success': True, 'operation': 'health', 'data': {...}}

        # Run maintenance
        result = await plex_server(operation="maintenance", maintenance_operation="optimize")
        # Returns: {'success': True, 'operation': 'maintenance', 'data': {...}}

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Set PLEX_TOKEN environment variable with your auth token
        - "maintenance_operation required": Provide maintenance operation type
        - "Permission denied": Admin access required for maintenance/restart/update operations

    See Also:
        - plex_library: For library management operations
        - plex_performance: For performance optimization
        - plex_organization: For library organization
    """
    try:
        plex = _get_plex_service()

        # Operation: status
        if operation == "status":
            status = await plex.get_server_status()
            return {
                "success": True,
                "operation": "status",
                "data": status.dict() if hasattr(status, "dict") else status,
            }

        # Operation: info
        if operation == "info":
            status = await plex.get_server_status()
            libraries = await plex.list_libraries()
            return {
                "success": True,
                "operation": "info",
                "data": {
                    "status": status.dict() if hasattr(status, "dict") else status,
                    "libraries": libraries,
                },
            }

        # Operation: health
        if operation == "health":
            # Import admin service for health check
            from ...api.admin import get_server_health

            health_data = await get_server_health()
            return {
                "success": True,
                "operation": "health",
                "data": health_data,
            }

        # Operation: maintenance
        if operation == "maintenance":
            if not maintenance_operation:
                return {
                    "success": False,
                    "message": "maintenance_operation is required for maintenance operation",
                    "error": "maintenance_operation is required for maintenance operation",
                    "error_code": "MISSING_MAINTENANCE_OPERATION",
                    "suggestions": [
                        "Provide maintenance_operation parameter",
                        "Valid values: optimize, clean_bundles, empty_trash, etc.",
                    ],
                }

            # Import admin service for maintenance
            from ...api.admin import run_server_maintenance

            result = await run_server_maintenance(operation=maintenance_operation, options=options or {})
            return {
                "success": True,
                "operation": "maintenance",
                "maintenance_operation": maintenance_operation,
                "data": result.dict() if hasattr(result, "dict") else result,
            }

        # Operation: restart
        if operation == "restart":
            # Note: Plex API may not support programmatic restart
            logger.warning("Server restart operation may not be fully supported by Plex API")
            return {
                "success": False,
                "message": "Server restart is not yet fully implemented",
                "error": "Server restart is not yet fully implemented",
                "error_code": "NOT_IMPLEMENTED",
                "suggestions": [
                    "Use Plex Web App or system service manager to restart the server",
                    "This operation may not be supported by the Plex API",
                ],
            }

        # Operation: update
        if operation == "update":
            # Note: Plex API may not support programmatic updates
            logger.warning("Server update operation may not be fully supported by Plex API")
            return {
                "success": False,
                "message": "Server update is not yet fully implemented",
                "error": "Server update is not yet fully implemented",
                "error_code": "NOT_IMPLEMENTED",
                "suggestions": [
                    "Use Plex Web App or system package manager to update the server",
                    "This operation may not be supported by the Plex API",
                ],
            }

        return {
            "success": False,
            "message": f"Invalid operation: '{operation}'",
            "error_code": "INVALID_OPERATION",
            "suggestions": [
                "Valid operations: status, info, health, maintenance, restart, update",
                f"You provided: '{operation}'",
            ],
        }

    except RuntimeError as e:
        error_msg = str(e)
        suggestions = []

        if "PLEX_TOKEN" in error_msg:
            suggestions = [
                "Set PLEX_TOKEN environment variable",
                "Get token from: Plex Web App → Settings → Account → Authorized Devices",
                "Or visit: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/",
            ]

        return {
            "success": False,
            "message": error_msg,
            "error": error_msg,
            "error_code": "RUNTIME_ERROR",
            "operation": operation,
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.error(
            f"Unexpected error in plex_server operation '{operation}': {e}",
            exc_info=True,
        )
        return {
            "success": False,
            "message": f"Unexpected error during {operation}: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
            "operation": operation,
            "suggestions": [
                "Check server logs for detailed error information",
                "Verify all required parameters are provided",
                "Try the operation again with valid parameters",
            ],
        }
