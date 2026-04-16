"""
Admin and user management Pydantic models for PlexMCP.

This module contains models related to user permissions and server maintenance.
"""

from typing import Any

from pydantic import BaseModel, Field


class UserPermissions(BaseModel):
    """User permission settings for Plex server access"""

    user_id: str = Field(description="User identifier")
    username: str = Field(description="Display username")
    email: str | None = Field(description="User email address")
    is_admin: bool = Field(description="Administrator privileges")
    is_managed: bool = Field(description="Managed user account")
    library_access: list[str] = Field(description="Accessible library IDs")
    restricted_content: bool = Field(description="Content rating restrictions enabled")
    max_rating: str | None = Field(description="Maximum content rating allowed")
    sharing_enabled: bool = Field(description="Can share content with other users")
    sync_enabled: bool = Field(description="Can sync content offline")
    home_user: bool = Field(description="Home user with enhanced privileges")
    last_seen: int | None = Field(description="Last activity timestamp")
    restrictions: list[str] = Field(description="Active restrictions and limitations")


class ServerMaintenanceResult(BaseModel):
    """Result of server maintenance operations"""

    operation: str = Field(description="Maintenance operation performed")
    status: str = Field(description="Operation status (success, error, partial)")
    details: dict[str, Any] = Field(description="Detailed operation results")
    space_freed_gb: float | None = Field(description="Disk space freed in GB")
    items_processed: int = Field(description="Number of items processed")
    duration_seconds: float = Field(description="Operation duration")
    recommendations: list[str] = Field(description="Post-maintenance recommendations")
    next_recommended: str | None = Field(description="Next recommended maintenance")
    warnings: list[str] = Field(description="Warnings or issues encountered")
