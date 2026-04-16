"""
PlexMCP User Management Portmanteau Tool

Consolidates all user-related operations into a single comprehensive interface.
FastMCP 2.13+ compliant with comprehensive docstrings and AI-friendly error messages.
"""

import os
from typing import Any, Literal

from ...app import mcp
from ...models.user import UserRole
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
async def plex_user(
    operation: Literal["list", "get", "create", "update", "delete", "update_permissions"],
    user_id: str | None = None,
    username: str | None = None,
    email: str | None = None,
    password: str | None = None,
    role: Literal["owner", "admin", "user", "managed", "shared"] | None = None,
    restricted: bool | None = None,
    permissions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Comprehensive user management operations for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 6 separate tools (one per operation), this tool consolidates related
    user management operations into a single interface. This design:
    - Prevents tool explosion (6 tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with user management tasks
    - Enables consistent user interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - list: List all Plex users
    - get: Get detailed information about a specific user
    - create: Create a new Plex user
    - update: Update an existing user's information
    - delete: Delete a user
    - update_permissions: Update user permissions and restrictions

    OPERATIONS DETAIL:

    list: List all Plex users
    - Parameters: None required
    - Returns: List of all users with their information
    - Example: plex_user(operation="list")
    - Use when: You want to see all users on the server

    get: Get detailed information about a specific user
    - Parameters: user_id (required)
    - Returns: Detailed user information
    - Example: plex_user(operation="get", user_id="12345")
    - Use when: You need details about a specific user

    create: Create a new Plex user
    - Parameters: username (required), email (required), password (required), role (optional), restricted (optional)
    - Returns: Created user information
    - Example: plex_user(operation="create", username="newuser", email="user@example.com", password="securepass123")
    - Use when: Adding a new user to the server

    update: Update an existing user's information
    - Parameters: user_id (required), username (optional), email (optional), password (optional), role (optional), restricted (optional)
    - Returns: Updated user information
    - Example: plex_user(operation="update", user_id="12345", username="newname")
    - Use when: Changing user details

    delete: Delete a user
    - Parameters: user_id (required)
    - Returns: Deletion confirmation
    - Example: plex_user(operation="delete", user_id="12345")
    - Use when: Removing a user from the server (WARNING: Cannot be undone)

    update_permissions: Update user permissions and restrictions
    - Parameters: user_id (required), permissions (required)
    - Returns: Updated user information with new permissions
    - Example: plex_user(operation="update_permissions", user_id="12345", permissions={"allowSync": True, "restricted": False})
    - Use when: Changing what a user can access

    Prerequisites:
        - Plex Media Server running and accessible
        - Valid PLEX_TOKEN environment variable set
        - Admin/owner permissions for create/update/delete operations

    Args:
        operation (str): The user operation to perform. Required. Must be one of: "list", "get", "create", "update", "delete", "update_permissions"
        user_id (str | None): User identifier (required for get/update/delete/update_permissions).
        username (str | None): Username (required for create, optional for update).
        email (str | None): Email address (required for create, optional for update).
        password (str | None): Password (required for create, optional for update).
        role (str | None): User role ("owner", "admin", "user", "managed", "shared").
        restricted (bool | None): Whether user should be restricted.
        permissions (dict | None): Permissions dictionary (required for update_permissions).

    Returns:
        Dictionary containing:
            - success: Boolean indicating operation success
            - operation: The operation that was performed
            - data: Operation-specific result data
            - count: Number of users returned (for list operation)
            - error: Error message if success is False
            - error_code: Specific error code for programmatic handling
            - suggestions: List of suggested fixes (on error)

    Examples:
        # List all users
        result = await plex_user(operation="list")
        # Returns: {'success': True, 'operation': 'list', 'data': [...], 'count': 5}

        # Get user details
        result = await plex_user(operation="get", user_id="12345")
        # Returns: {'success': True, 'operation': 'get', 'data': {...}}

        # Create new user
        result = await plex_user(
            operation="create",
            username="newuser",
            email="user@example.com",
            password="securepass123",
            role="user",
            restricted=False
        )
        # Returns: {'success': True, 'operation': 'create', 'data': {...}}

        # Update user
        result = await plex_user(operation="update", user_id="12345", username="newname")
        # Returns: {'success': True, 'operation': 'update', 'data': {...}}

        # Update permissions
        result = await plex_user(
            operation="update_permissions",
            user_id="12345",
            permissions={"allowSync": True, "restricted": False}
        )
        # Returns: {'success': True, 'operation': 'update_permissions', 'data': {...}}

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Set PLEX_TOKEN environment variable with your auth token
        - "user_id required": Provide valid user ID for operations that require it
        - "User not found": Use plex_user(operation="list") to find valid user IDs
        - "Permission denied": Admin access required for create/update/delete operations
        - "Invalid email": Provide a valid email address format
        - "Password too short": Password must be at least 8 characters
        - "Username too short": Username must be at least 3 characters

    See Also:
        - plex_library: For library management operations
        - plex_server: For server management operations
    """
    try:
        plex = _get_plex_service()

        # Operation: list
        if operation == "list":
            users_data = await plex.list_users()
            return {
                "success": True,
                "operation": "list",
                "data": users_data,
                "count": len(users_data),
            }

        # Operation: get
        if operation == "get":
            if not user_id:
                return {
                    "success": False,
                    "error": "user_id is required for get operation",
                    "error_code": "MISSING_USER_ID",
                    "suggestions": ["Use plex_user(operation='list') to find available user IDs"],
                }

            user_data = await plex.get_user(user_id)
            if user_data is None:
                return {
                    "success": False,
                    "error": f"User {user_id} not found",
                    "error_code": "USER_NOT_FOUND",
                    "suggestions": [
                        "Use plex_user(operation='list') to find valid user IDs",
                        "Verify the user_id is correct",
                    ],
                }
            return {"success": True, "operation": "get", "data": user_data}

        # Operation: create
        if operation == "create":
            if not username:
                return {
                    "success": False,
                    "error": "username is required for create operation",
                    "error_code": "MISSING_USERNAME",
                    "suggestions": ["Provide username parameter (min 3 characters)"],
                }
            if not email:
                return {
                    "success": False,
                    "error": "email is required for create operation",
                    "error_code": "MISSING_EMAIL",
                    "suggestions": ["Provide email parameter (valid email format)"],
                }
            if not password:
                return {
                    "success": False,
                    "error": "password is required for create operation",
                    "error_code": "MISSING_PASSWORD",
                    "suggestions": ["Provide password parameter (min 8 characters)"],
                }

            if len(username) < 3:
                return {
                    "success": False,
                    "error": "username must be at least 3 characters",
                    "error_code": "INVALID_USERNAME",
                    "suggestions": ["Provide a username with at least 3 characters"],
                }
            if len(password) < 8:
                return {
                    "success": False,
                    "error": "password must be at least 8 characters",
                    "error_code": "INVALID_PASSWORD",
                    "suggestions": ["Provide a password with at least 8 characters"],
                }

            role_str = role.value if isinstance(role, UserRole) else (role or "user")
            user_data = await plex.create_user(
                username=username,
                email=email,
                password=password,
                role=role_str,
                restricted=restricted or False,
            )
            return {
                "success": True,
                "operation": "create",
                "data": user_data,
            }

        # Operation: update
        if operation == "update":
            if not user_id:
                return {
                    "success": False,
                    "error": "user_id is required for update operation",
                    "error_code": "MISSING_USER_ID",
                    "suggestions": ["Provide user_id to update"],
                }

            update_kwargs = {}
            if username is not None:
                if len(username) < 3:
                    return {
                        "success": False,
                        "error": "username must be at least 3 characters",
                        "error_code": "INVALID_USERNAME",
                        "suggestions": ["Provide a username with at least 3 characters"],
                    }
                update_kwargs["username"] = username
            if email is not None:
                update_kwargs["email"] = email
            if password is not None:
                if len(password) < 8:
                    return {
                        "success": False,
                        "error": "password must be at least 8 characters",
                        "error_code": "INVALID_PASSWORD",
                        "suggestions": ["Provide a password with at least 8 characters"],
                    }
                update_kwargs["password"] = password
            if role is not None:
                role_str = role.value if isinstance(role, UserRole) else role
                update_kwargs["role"] = role_str
            if restricted is not None:
                update_kwargs["restricted"] = restricted

            if not update_kwargs:
                return {
                    "success": False,
                    "error": "At least one update field (username, email, password, role, restricted) is required",
                    "error_code": "MISSING_UPDATE_FIELDS",
                    "suggestions": ["Provide at least one field to update"],
                }

            user_data = await plex.update_user(user_id, **update_kwargs)
            return {
                "success": True,
                "operation": "update",
                "user_id": user_id,
                "data": user_data,
            }

        # Operation: delete
        if operation == "delete":
            if not user_id:
                return {
                    "success": False,
                    "error": "user_id is required for delete operation",
                    "error_code": "MISSING_USER_ID",
                    "suggestions": ["Provide user_id to delete"],
                }

            result = await plex.delete_user(user_id)
            return {
                "success": result,
                "operation": "delete",
                "user_id": user_id,
                "data": {"deleted": result},
            }

        # Operation: update_permissions
        if operation == "update_permissions":
            if not user_id:
                return {
                    "success": False,
                    "error": "user_id is required for update_permissions operation",
                    "error_code": "MISSING_USER_ID",
                    "suggestions": ["Provide user_id to update permissions"],
                }
            if not permissions:
                return {
                    "success": False,
                    "error": "permissions dictionary is required for update_permissions operation",
                    "error_code": "MISSING_PERMISSIONS",
                    "suggestions": [
                        "Provide permissions dict: {'allowSync': True, 'restricted': False}",
                        "Available permission keys: allowSync, allowCameraUpload, allowChannels, restricted",
                    ],
                }

            result = await plex.update_user_permissions(user_id, permissions)
            # Get updated user data
            user_data = await plex.get_user(user_id)
            return {
                "success": True,
                "operation": "update_permissions",
                "user_id": user_id,
                "data": user_data or result,
            }

        return {
            "success": False,
            "error": f"Invalid operation: '{operation}'",
            "error_code": "INVALID_OPERATION",
            "suggestions": [
                "Valid operations: list, get, create, update, delete, update_permissions",
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
        elif "not found" in error_msg.lower():
            suggestions = [
                "Verify the user_id is correct",
                "Use plex_user(operation='list') to find valid user IDs",
            ]
        elif "permission" in error_msg.lower() or "denied" in error_msg.lower():
            suggestions = [
                "Admin access required for this operation",
                "Verify you have owner/admin permissions",
            ]

        return {
            "success": False,
            "error": error_msg,
            "error_code": "RUNTIME_ERROR",
            "operation": operation,
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.exception("Unexpected error in plex_user operation '{operation}':")
        return {
            "success": False,
            "error": f"Unexpected error during {operation}: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
            "operation": operation,
            "suggestions": [
                "Check server logs for detailed error information",
                "Verify all required parameters are provided",
                "Try the operation again with valid parameters",
            ],
        }
