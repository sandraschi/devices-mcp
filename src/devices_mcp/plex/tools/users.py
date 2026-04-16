"""Plex user management tools for FastMCP 2.10.1."""

import os

from pydantic import BaseModel, EmailStr, Field

from ..app import mcp
from ..models.user import User, UserList, UserRole
from ..utils import get_logger

logger = get_logger(__name__)


def _get_plex_service():
    from ..services.plex_service import PlexService

    base_url = os.getenv("PLEX_URL") or os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    token = os.getenv("PLEX_TOKEN")
    if not token:
        raise RuntimeError("PLEX_TOKEN environment variable is required")
    return PlexService(base_url=base_url, token=token)


class CreateUserRequest(BaseModel):
    """Request model for creating a new user."""

    username: str = Field(..., min_length=3, max_length=50, description="Username for the new user")
    email: EmailStr = Field(..., description="Email address for the new user")
    password: str = Field(..., min_length=8, description="Password for the new user")
    role: UserRole = Field(UserRole.USER, description="User role (admin, user, managed, shared)")
    restricted: bool = Field(False, description="Whether the user should be restricted")


@mcp.tool()
async def create_user(request: CreateUserRequest) -> User:
    """Create a new Plex user.

    Args:
        request: User creation parameters

    Returns:
        The created user information
    """
    plex = _get_plex_service()
    try:
        user_data = await plex.create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            role=request.role.value,  # Convert enum to string
            restricted=request.restricted,
        )
        return User(**user_data)
    except Exception:
        logger.exception("Failed to create user {request.username}:")
        raise


class UpdateUserRequest(BaseModel):
    """Request model for updating a user."""

    user_id: str = Field(..., description="ID of the user to update")
    username: str | None = Field(None, min_length=3, max_length=50, description="New username")
    email: EmailStr | None = Field(None, description="New email address")
    password: str | None = Field(None, min_length=8, description="New password")
    role: UserRole | None = Field(None, description="New user role")
    restricted: bool | None = Field(None, description="Whether the user should be restricted")


@mcp.tool()
async def update_user(request: UpdateUserRequest) -> User:
    """Update an existing Plex user.

    Args:
        request: User update parameters

    Returns:
        Updated user information
    """
    plex = _get_plex_service()
    try:
        update_data = {}
        if request.username is not None:
            update_data["username"] = request.username
        if request.email is not None:
            update_data["email"] = request.email
        if request.password is not None:
            update_data["password"] = request.password
        if request.role is not None:
            update_data["role"] = request.role.value  # Convert enum to string
        if request.restricted is not None:
            update_data["restricted"] = request.restricted

        user_data = await plex.update_user(user_id=request.user_id, **update_data)
        return User(**user_data)
    except Exception:
        logger.exception("Failed to update user {request.user_id}:")
        raise


class DeleteUserRequest(BaseModel):
    """Request model for deleting a user."""

    user_id: str = Field(..., description="ID of the user to delete")


@mcp.tool()
async def delete_user(request: DeleteUserRequest) -> bool:
    """Delete a Plex user.

    Args:
        request: User deletion parameters

    Returns:
        True if deletion was successful, False otherwise
    """
    plex = _get_plex_service()
    try:
        success = await plex.delete_user(user_id=request.user_id)
        if success:
            logger.info(f"Successfully deleted user {request.user_id}")
        else:
            logger.warning(f"Failed to delete user {request.user_id}")
        return success
    except Exception:
        logger.exception("Error deleting user {request.user_id}:")
        return False


@mcp.tool()
async def list_users() -> UserList:
    """List all Plex users.

    Returns:
        List of all users with their information
    """
    plex = _get_plex_service()
    try:
        users_data = await plex.list_users()
        users = [User(**user_data) for user_data in users_data]
        return UserList(users=users)
    except Exception:
        logger.exception("Error listing users:")
        return UserList(users=[])


class GetUserRequest(BaseModel):
    """Request model for getting a specific user."""

    user_id: str = Field(..., description="ID of the user to retrieve")


@mcp.tool()
async def get_user(request: GetUserRequest) -> User | None:
    """Get a specific Plex user by ID.

    Args:
        request: User retrieval parameters

    Returns:
        User information if found, None otherwise
    """
    plex = _get_plex_service()
    try:
        user_data = await plex.get_user(user_id=request.user_id)
        if user_data:
            return User(**user_data)
        return None
    except Exception:
        logger.exception("Error getting user {request.user_id}:")
        return None


class UpdateUserPermissionsRequest(BaseModel):
    """Request model for updating user permissions."""

    user_id: str = Field(..., description="ID of the user to update")
    permissions: dict = Field(..., description="Dictionary of permissions to update")


@mcp.tool()
async def update_user_permissions(request: UpdateUserPermissionsRequest) -> User:
    """Update permissions for a Plex user.

    Args:
        request: Permission update parameters

    Returns:
        Updated user information with new permissions
    """
    plex = _get_plex_service()
    try:
        await plex.update_user_permissions(user_id=request.user_id, permissions=request.permissions)
        # Get the updated user data
        user_data = await plex.get_user(user_id=request.user_id)
        if not user_data:
            raise ValueError(f"User {request.user_id} not found after updating permissions")
        return User(**user_data)
    except Exception:
        logger.exception("Error updating permissions for user {request.user_id}:")
        raise
