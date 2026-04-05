"""
Admin API endpoints for PlexMCP.

This module contains administrative API endpoints for user management
and server maintenance.
"""

from typing import Any, Dict, List, Optional

# Import the shared FastMCP instance from the package level
# Import models
from ..models import ServerMaintenanceResult, UserPermissions

# Import utilities
from ..utils import get_logger

# Initialize logger
logger = get_logger(__name__)


async def get_users() -> List[UserPermissions]:
    """
    Get server users (admin function).

    Returns list of users with access to the Plex server.
    Only works with admin authentication.

    Returns:
        List of user accounts and their permissions

    Raises:
        RuntimeError: If there's an error fetching user information
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        users = await plex.get_users()

        user_permissions = []
        for user in users:
            # Get user sections/access
            sections = []
            if hasattr(user, "sections"):
                sections = (
                    [section.key for section in user.sections()]
                    if callable(getattr(user, "sections", None))
                    else []
                )

            # Get restrictions
            restrictions = []
            if hasattr(user, "restrictions"):
                restrictions = (
                    [str(r) for r in user.restrictions]
                    if hasattr(user.restrictions, "__iter__")
                    else []
                )

            user_permissions.append(
                UserPermissions(
                    user_id=getattr(user, "id", ""),
                    username=getattr(user, "title", ""),
                    email=getattr(user, "email", ""),
                    is_admin=getattr(user, "admin", False),
                    is_managed=getattr(user, "restricted", False),
                    library_access=sections,
                    restricted_content=getattr(user, "restricted", False),
                    max_rating=getattr(user, "rating", None),
                    sharing_enabled=getattr(user, "allowSync", False),
                    sync_enabled=getattr(user, "allowSync", False),
                    home_user=getattr(user, "home", False),
                    last_seen=getattr(user, "lastSeenAt", 0) if hasattr(user, "lastSeenAt") else 0,
                    restrictions=restrictions,
                )
            )

        return user_permissions

    except Exception as e:
        raise RuntimeError(f"Error fetching users: {e!s}") from e


async def update_user_permissions(user_id: str, permissions: Dict[str, Any]) -> UserPermissions:
    """
    Update user permissions and restrictions.

    Args:
        user_id: ID of the user to update
        permissions: Dictionary of permissions to update

    Returns:
        Updated user permissions

    Raises:
        RuntimeError: If there's an error updating user permissions
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        updated_user = await plex.update_user_permissions(user_id, permissions)

        if not updated_user:
            raise RuntimeError(f"Failed to update permissions for user {user_id}")

        # Get sections/access
        sections = []
        if hasattr(updated_user, "sections"):
            sections = (
                [section.key for section in updated_user.sections()]
                if callable(getattr(updated_user, "sections", None))
                else []
            )

        # Get restrictions
        restrictions = []
        if hasattr(updated_user, "restrictions"):
            restrictions = (
                [str(r) for r in updated_user.restrictions]
                if hasattr(updated_user.restrictions, "__iter__")
                else []
            )

        return UserPermissions(
            user_id=getattr(updated_user, "id", user_id),
            username=getattr(updated_user, "title", ""),
            email=getattr(updated_user, "email", ""),
            is_admin=getattr(updated_user, "admin", False),
            is_managed=getattr(updated_user, "restricted", True),
            library_access=sections,
            restricted_content=getattr(updated_user, "restricted", False),
            max_rating=getattr(updated_user, "rating", None),
            sharing_enabled=getattr(updated_user, "allowSync", False),
            sync_enabled=getattr(updated_user, "allowSync", False),
            home_user=getattr(updated_user, "home", False),
            last_seen=getattr(updated_user, "lastSeenAt", 0)
            if hasattr(updated_user, "lastSeenAt")
            else 0,
            restrictions=restrictions,
        )

    except Exception as e:
        raise RuntimeError(f"Error updating user permissions: {e!s}") from e


async def run_server_maintenance(
    operation: str, options: Optional[Dict[str, Any]] = None
) -> ServerMaintenanceResult:
    """
    Run server maintenance operations.

    Args:
        operation: Type of maintenance to perform
                  (optimize, clean_bundles, empty_trash, etc.)
        options: Additional options for the operation

    Returns:
        Result of the maintenance operation

    Raises:
        RuntimeError: If there's an error running the maintenance operation
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        result = await plex.run_maintenance(operation, options or {})

        if not result:
            raise RuntimeError(f"Failed to run maintenance operation: {operation}")

        # Handle different result types
        if isinstance(result, dict):
            # If result is already a dictionary, use it directly
            result_data = result
        else:
            # If result is a Plex object, convert to dict
            result_data = {
                "status": getattr(result, "status", "completed"),
                "details": {},
                "space_freed_gb": getattr(result, "space_freed_gb", 0),
                "items_processed": getattr(result, "items_processed", 0),
                "duration_seconds": getattr(result, "duration_seconds", 0),
                "recommendations": getattr(result, "recommendations", []),
                "warnings": getattr(result, "warnings", []),
            }

        return ServerMaintenanceResult(
            operation=operation,
            status=result_data.get("status", "completed"),
            details=result_data.get("details", {}),
            space_freed_gb=result_data.get("space_freed_gb", 0),
            items_processed=result_data.get("items_processed", 0),
            duration_seconds=result_data.get("duration_seconds", 0),
            recommendations=result_data.get("recommendations", []),
            next_recommended=result_data.get("next_recommended"),
            warnings=result_data.get("warnings", []),
        )
    except Exception as e:
        raise RuntimeError(f"Error running maintenance operation: {e!s}") from e


async def get_server_health() -> Dict[str, Any]:
    """
    Get detailed server health and performance metrics.

    Returns:
        Dictionary containing server health information
    """
    # TODO: Implement actual health check
    return {
        "status": "healthy",
        "timestamp": 1625184000,
        "resources": {
            "cpu_percent": 45.2,
            "memory_percent": 60.1,
            "disk_usage_percent": 35.7,
            "network_usage": {
                "bytes_sent": 1024 * 1024 * 500,  # 500 MB
                "bytes_received": 1024 * 1024 * 250,  # 250 MB
            },
        },
        "active_sessions": 3,
        "background_tasks": {"running": 2, "pending": 1},
        "alerts": ["Consider adding more storage space in the next 30 days"],
    }


# No need to export app - tools are registered with the shared mcp instance
