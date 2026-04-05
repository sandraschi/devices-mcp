"""
Admin service implementation for PlexMCP.

This module contains the AdminService class which handles administrative
operations like user management and server maintenance.
"""

import logging
import random
import time
from typing import Any, Dict, List, Optional

from plexapi.exceptions import Unauthorized

from ..models import ServerMaintenanceResult, UserPermissions
from .base import BaseService, ServiceError

logger = logging.getLogger(__name__)


class AdminService(BaseService):
    """Service for administrative operations."""

    def __init__(self, plex_service):
        """Initialize the admin service.

        Args:
            plex_service: Instance of PlexService for Plex server interaction
        """
        super().__init__()
        self.plex_service = plex_service
        self.plex = None
        self.myplex_account = None

    async def _initialize(self) -> None:
        """Initialize the service."""
        await self.plex_service.initialize()
        self.plex = self.plex_service.plex

        # Try to get MyPlex account if available
        try:
            if hasattr(self.plex, "myPlexAccount"):
                self.myplex_account = self.plex.myPlexAccount()
        except Exception as e:
            logger.warning(f"Failed to get MyPlex account: {e!s}")

    async def get_users(self) -> List[UserPermissions]:
        """Get all users with access to the Plex server.

        Returns:
            List of user accounts and their permissions
        """
        await self.initialize()

        try:
            users = []

            # Get server owner (admin) first
            if self.myplex_account and self.myplex_account.email:
                users.append(self._create_admin_user_permissions(self.myplex_account))

            # Get managed users (home users)
            if hasattr(self.plex, "myPlexAccount") and hasattr(self.plex.myPlexAccount(), "users"):
                for user in self.plex.myPlexAccount().users():
                    users.append(self._convert_to_user_permissions(user))

            # Get local users (if any)
            # Note: This requires Plex Pass and the server to be claimed
            if hasattr(self.plex, "myPlexUsers"):
                for user in self.plex.myPlexUsers():
                    if not any(u.user_id == str(user.id) for u in users):
                        users.append(self._convert_to_user_permissions(user))

            return users

        except Unauthorized as e:
            error_msg = "Unauthorized: Admin privileges required to access user information"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="unauthorized") from e
        except Exception as e:
            error_msg = f"Failed to get users: {e!s}"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="get_users_failed") from e

    async def update_user_permissions(
        self, user_id: str, permissions: Dict[str, Any]
    ) -> UserPermissions:
        """Update user permissions and restrictions.

        Args:
            user_id: ID of the user to update
            permissions: Dictionary of permissions to update

        Returns:
            Updated user permissions
        """
        await self.initialize()

        try:
            # This is a simplified example - actual implementation would use Plex API
            # to update user permissions on the server

            # In a real implementation, we would:
            # 1. Find the user by ID
            # 2. Update their permissions using the Plex API
            # 3. Return the updated user object

            # For now, we'll just log the update and return a mock response
            logger.info(f"Updating permissions for user {user_id}: {permissions}")

            # Simulate a successful update
            return UserPermissions(
                user_id=user_id,
                username=permissions.get("username", f"user_{user_id}"),
                email=permissions.get("email", f"user_{user_id}@example.com"),
                is_admin=permissions.get("is_admin", False),
                is_managed=permissions.get("is_managed", True),
                library_access=permissions.get("library_access", []),
                restricted_content=permissions.get("restricted_content", False),
                max_rating=permissions.get("max_rating"),
                sharing_enabled=permissions.get("sharing_enabled", False),
                sync_enabled=permissions.get("sync_enabled", False),
                home_user=permissions.get("home_user", False),
                last_seen=int(time.time()),
                restrictions=permissions.get("restrictions", []),
            )

        except Exception as e:
            error_msg = f"Failed to update user permissions: {e!s}"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="update_user_failed") from e

    async def run_server_maintenance(
        self, operation: str, options: Optional[Dict[str, Any]] = None
    ) -> ServerMaintenanceResult:
        """Run server maintenance operations.

        Args:
            operation: Type of maintenance to perform
                      (optimize, clean_bundles, empty_trash, etc.)
            options: Additional options for the operation

        Returns:
            Result of the maintenance operation
        """
        await self.initialize()

        try:
            # This is a simplified example - actual implementation would use Plex API
            # to perform maintenance operations

            # Log the maintenance operation
            logger.info(f"Running maintenance operation: {operation}")
            if options:
                logger.info(f"Options: {options}")

            # Simulate the maintenance operation
            # In a real implementation, we would call the appropriate Plex API methods
            time.sleep(2)  # Simulate work being done

            # Generate some mock results
            result_details = {
                "operation": operation,
                "options": options or {},
                "completed_at": int(time.time()),
                "status": "completed",
            }

            # Add operation-specific details
            if operation == "optimize":
                result_details.update(
                    {
                        "database_optimized": True,
                        "fragmentation_reduced": random.randint(10, 50),
                        "performance_improved": True,
                    }
                )
            elif operation == "clean_bundles":
                result_details.update(
                    {
                        "bundles_cleaned": random.randint(5, 20),
                        "space_freed_mb": random.randint(50, 500),
                    }
                )
            elif operation == "empty_trash":
                result_details.update(
                    {
                        "items_removed": random.randint(0, 10),
                        "space_freed_mb": random.randint(0, 100),
                    }
                )

            return ServerMaintenanceResult(
                operation=operation,
                status="success",
                details=result_details,
                space_freed_gb=random.uniform(0.1, 2.0),
                items_processed=random.randint(1, 100),
                duration_seconds=random.uniform(1.0, 10.0),
                recommendations=[
                    "Run this operation weekly for optimal performance",
                    "Consider running a full optimization next time",
                ],
                next_recommended=int(time.time()) + (7 * 24 * 3600),  # 1 week from now
                warnings=[],
            )

        except Exception as e:
            error_msg = f"Failed to run maintenance operation {operation}: {e!s}"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="maintenance_failed") from e

    async def get_server_health(self) -> Dict[str, Any]:
        """Get detailed server health and performance metrics.

        Returns:
            Dictionary containing server health information
        """
        await self.initialize()

        try:
            # Get basic server status
            server_status = await self.plex_service.get_server_status()

            # Get active sessions
            sessions = await self.plex_service.get_sessions()

            # Get system resources (simulated)
            resources = {
                "cpu_percent": random.uniform(10.0, 80.0),
                "memory_percent": random.uniform(20.0, 90.0),
                "disk_usage_percent": random.uniform(10.0, 95.0),
                "network_usage": {
                    "bytes_sent": random.randint(1000000, 1000000000),
                    "bytes_received": random.randint(1000000, 1000000000),
                },
            }

            # Check for any active alerts
            alerts = []
            if resources["disk_usage_percent"] > 85:
                alerts.append("Disk usage is high - consider freeing up space")
            if resources["memory_percent"] > 90:
                alerts.append("Memory usage is high - consider upgrading your server")

            return {
                "status": "healthy" if not alerts else "warning",
                "timestamp": int(time.time()),
                "server": {
                    "name": server_status.name,
                    "version": server_status.version,
                    "platform": server_status.platform,
                    "my_plex_connected": server_status.connected,
                },
                "resources": resources,
                "active_sessions": len(sessions),
                "background_tasks": {
                    "running": random.randint(0, 5),
                    "pending": random.randint(0, 3),
                },
                "alerts": alerts,
            }

        except Exception as e:
            error_msg = f"Failed to get server health: {e!s}"
            logger.exception(error_msg)
            raise ServiceError(error_msg, code="health_check_failed") from e

    # Helper methods
    def _create_admin_user_permissions(self, account) -> UserPermissions:
        """Create a UserPermissions object for the admin user."""
        return UserPermissions(
            user_id=account.id,
            username=account.username,
            email=account.email,
            is_admin=True,
            is_managed=False,
            library_access=[],  # Admin has access to all libraries
            restricted_content=False,
            max_rating=None,
            sharing_enabled=True,
            sync_enabled=True,
            home_user=True,
            last_seen=int(time.time()),
            restrictions=[],
        )

    def _convert_to_user_permissions(self, user) -> UserPermissions:
        """Convert a Plex user object to our UserPermissions model."""
        return UserPermissions(
            user_id=user.id,
            username=user.username or user.title or f"user_{user.id}",
            email=getattr(user, "email", ""),
            is_admin=getattr(user, "admin", False),
            is_managed=getattr(user, "restricted", False),
            library_access=getattr(user, "sections", []),
            restricted_content=getattr(user, "restricted", False),
            max_rating=getattr(user, "rating", None),
            sharing_enabled=getattr(user, "sharing", False),
            sync_enabled=getattr(user, "sync", False),
            home_user=getattr(user, "home", False),
            last_seen=getattr(user, "lastSeenAt", 0),
            restrictions=getattr(user, "restrictions", []),
        )
