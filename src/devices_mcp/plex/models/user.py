"""Pydantic models for Plex users and authentication."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """User roles in Plex."""

    OWNER = "owner"
    ADMIN = "admin"
    USER = "user"
    MANAGED = "managed"
    SHARED = "shared"


class UserPermissions(BaseModel):
    """Model representing user permissions in Plex."""

    download: bool = Field(False, description="Can download content")
    sync: bool = Field(False, description="Can sync content")
    camera_upload: bool = Field(False, description="Can upload photos from camera")
    channels: bool = Field(False, description="Can access channels")
    playlists: bool = Field(True, description="Can manage playlists")
    library: bool = Field(True, description="Can access library")
    admin: bool = Field(False, description="Has admin privileges")


class User(BaseModel):
    """Model representing a Plex user."""

    id: int = Field(..., description="Unique identifier for the user")
    email: Optional[EmailStr] = Field(None, description="User's email address")
    username: str = Field(..., description="User's username")
    thumb: Optional[str] = Field(None, description="URL to user's avatar")
    title: Optional[str] = Field(None, description="User's display name")
    role: UserRole = Field(UserRole.USER, description="User's role")
    permissions: UserPermissions = Field(
        default_factory=UserPermissions, description="User's permissions"
    )
    auth_token: Optional[str] = Field(
        None, description="Authentication token (only available for the current user)", exclude=True
    )
    server: bool = Field(False, description="Is a server owner/admin")
    restricted: bool = Field(False, description="Is a restricted user")
    home: bool = Field(False, description="Has access to home features")
    guest: bool = Field(False, description="Is a guest user")
    protected: bool = Field(False, description="Is a protected user")
    last_seen: Optional[datetime] = Field(None, description="When the user was last active")
    created_at: Optional[datetime] = Field(None, description="When the user was created")
    updated_at: Optional[datetime] = Field(None, description="When the user was last updated")
    extra_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata about the user"
    )


class UserList(BaseModel):
    """Model representing a list of users."""

    users: List[User] = Field(default_factory=list, description="List of users")
    total: int = Field(0, description="Total number of users")
