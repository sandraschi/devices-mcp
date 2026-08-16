"""Plex service implementation for FastMCP 2.10."""

import asyncio
import logging
from typing import Any

from plexapi.exceptions import PlexApiException
from plexapi.server import PlexServer

from ..models.media import MediaItem
from ..models.server import PlexServerStatus

logger = logging.getLogger(__name__)


class PlexService:
    """Service for interacting with Plex Media Server."""

    def __init__(self, base_url: str, token: str, timeout: int = 30):
        """Initialize Plex service.

        Args:
            base_url: Base URL of the Plex server (e.g., http://localhost:32400)
            token: Plex authentication token
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.server: PlexServer | None = None
        self._initialized = False

    async def connect(self) -> None:
        """Establish connection to Plex server."""
        if self._initialized:
            return

        try:
            # PlexAPI handles its own session management, don't pass aiohttp session
            self.server = await self._run_in_executor(PlexServer, self.base_url, self.token, timeout=self.timeout)
            self._initialized = True
            logger.info(f"Connected to Plex server: {self.server.friendlyName}")

        except PlexApiException:
            logger.exception("Failed to connect to Plex server:")
            raise

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run synchronous PlexAPI calls in executor."""
        from functools import partial

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    async def get_server_status(self) -> PlexServerStatus:
        """Get Plex server status and information."""
        if not self._initialized:
            await self.connect()

        try:
            status = await self._run_in_executor(self._get_server_status_sync)
            return PlexServerStatus(**status)

        except PlexApiException:
            logger.exception("Failed to get server status:")
            raise

    def _get_server_status_sync(self) -> dict[str, Any]:
        """Synchronous helper to get server status."""
        if not self.server:
            raise RuntimeError("Not connected to Plex server")

        return {
            "name": self.server.friendlyName,
            "version": self.server.version,
            "platform": self.server.platform,
            "active_sessions": len(self.server.sessions()),
            "libraries": [s.title for s in self.server.library.sections()],
            "updated_at": self.server.updated_at.timestamp() if hasattr(self.server, "updated_at") else 0,
        }

    async def list_libraries(self) -> list[dict[str, Any]]:
        """Get list of all libraries from Plex server.

        Returns:
            List of dictionaries containing library information
        """
        if not self._initialized:
            await self.connect()

        try:
            libraries = await self._run_in_executor(self._get_libraries_sync)
            return libraries

        except PlexApiException:
            logger.exception("Failed to list libraries:")
            raise

    async def get_libraries(self) -> list[dict[str, Any]]:
        """Alias for list_libraries for backward compatibility."""
        return await self.list_libraries()

    def _get_libraries_sync(self) -> list[dict[str, Any]]:
        """Synchronous helper to get libraries with complete section information."""
        if not self.server:
            raise RuntimeError("Not connected to Plex server")

        libraries = []
        for section in self.server.library.sections():
            try:
                # Get the section details
                section_info = {
                    "id": section.key,
                    "title": section.title,
                    "type": section.type,
                    "agent": getattr(section, "agent", ""),
                    "scanner": getattr(section, "scanner", ""),
                    "language": getattr(section, "language", "en"),
                    "updated_at": section.updatedAt.timestamp() if hasattr(section, "updatedAt") else 0,
                    "created_at": section.addedAt.timestamp() if hasattr(section, "addedAt") else 0,
                    "scanned_at": section.scannedAt.timestamp() if hasattr(section, "scannedAt") else 0,
                    "content": getattr(section, "content", None),
                    "count": section.totalSize if hasattr(section, "totalSize") else 0,
                }

                # Get additional metadata if available
                if hasattr(section, "contentChangedAt"):
                    section_info["content_changed_at"] = section.contentChangedAt.timestamp()

                libraries.append(section_info)

            except Exception as e:
                logger.exception(f"Error processing library section {getattr(section, 'title', 'unknown')}: {e!s}")
                continue

        return libraries

    async def search_media(self, query: str, limit: int = 10, library_id: str | None = None) -> list[MediaItem]:
        """Search for media across all libraries or within a specific library."""
        if not self._initialized:
            await self.connect()

        try:
            results = await self._run_in_executor(self._search_media_sync, query, limit, library_id)
            return [MediaItem(**item) for item in results]

        except PlexApiException:
            logger.exception("Search failed:")
            raise

    def _search_media_sync(self, query: str, limit: int, library_id: str | None = None) -> list[dict[str, Any]]:
        """Synchronous helper to search for media."""
        if not self.server:
            raise RuntimeError("Not connected to Plex server")

        if library_id:
            section = self.server.library.sectionByID(int(library_id))
            results = section.search(query, maxresults=limit)
        else:
            results = self.server.search(query, limit=limit)

        return [
            {
                "id": str(getattr(item, "ratingKey", getattr(item, "id", ""))),
                "title": getattr(item, "title", getattr(item, "tag", "Unknown")),
                "type": getattr(item, "type", "unknown"),
                "year": getattr(item, "year", None),
                "thumb": getattr(item, "thumb", ""),
                "summary": getattr(item, "summary", ""),
            }
            for item in results
        ]

    async def organize_library(
        self,
        library_id: str,
        dry_run: bool = False,
        patterns: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Organize a Plex library according to best practices.

        Args:
            library_id: ID of the library to organize
            dry_run: If True, only show what would be changed
            patterns: Custom patterns for organization

        Returns:
            Dictionary with organization results
        """
        if not self._initialized:
            await self.connect()

        try:
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))

            # In a real implementation, this would perform actual organization
            # For now, we'll return a summary of the library
            items = await self._run_in_executor(lambda: section.all())

            # Honesty: library organization against the real Plex API is
            # NOT implemented. Previously it claimed "Organization completed"
            # without doing anything (fake green). Now it returns the library
            # summary only and says so explicitly.
            return {
                "library_id": library_id,
                "library_name": section.title,
                "item_count": len(items),
                "changes": [],
                "dry_run": dry_run,
                "note": "Library organization is not implemented - summary only, nothing was reorganized.",
            }
        except Exception:
            logger.exception("Error organizing library {library_id}:")
            raise

    async def analyze_library(self, library_id: str) -> dict[str, Any]:
        """Analyze a library for organization issues.

        Args:
            library_id: ID of the library to analyze

        Returns:
            Dictionary with analysis results
        """
        if not self._initialized:
            await self.connect()

        try:
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
            items = await self._run_in_executor(lambda: section.all())

            # Analyze items for potential issues
            issues = []
            for item in items[:100]:  # Limit to first 100 items for performance
                if not hasattr(item, "media") or not item.media:
                    issues.append(
                        {
                            "item_id": item.ratingKey,
                            "title": item.title,
                            "issue": "Missing media files",
                            "severity": "high",
                        }
                    )

            return {
                "library_id": library_id,
                "library_name": section.title,
                "total_items": len(items),
                "issues_found": len(issues),
                "issues": issues[:10],  # Return first 10 issues
            }
        except Exception:
            logger.exception("Error analyzing library {library_id}:")
            raise

    async def refresh_metadata(
        self,
        item_id: str | None = None,
        library_id: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        """Refresh metadata for an item or library.

        Args:
            item_id: ID of the item to refresh
            library_id: ID of the library to refresh
            force: Force refresh even if not needed

        Returns:
            Dictionary with refresh results
        """
        if not self._initialized:
            await self.connect()

        try:
            if item_id:
                item = await self._run_in_executor(lambda: self.server.fetchItem(int(item_id)))
                await self._run_in_executor(item.refresh)
                return {"item_id": item_id, "title": item.title, "refreshed": True}
            if library_id:
                section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
                await self._run_in_executor(section.update)
                return {
                    "library_id": library_id,
                    "library_name": section.title,
                    "refreshed": True,
                }
            raise ValueError("Either item_id or library_id must be provided")
        except Exception:
            logger.exception("Error refreshing metadata:")
            raise

    # User Management Methods

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        role: str,
        restricted: bool = False,
    ) -> dict[str, Any]:
        """Create a new Plex user.

        Args:
            username: Username for the new user
            email: Email address for the new user
            password: Password for the new user
            role: User role (admin, user, managed, shared)
            restricted: Whether the user should be restricted

        Returns:
            Dictionary with user information
        """
        if not self._initialized:
            await self.connect()

        try:
            # Plex Home requires different handling than managed users
            if role == "managed":
                user = await self._run_in_executor(
                    self.server.myPlexAccount().addFriend,
                    email=email,
                    user=username,
                    password=password,
                    server=True,
                    allowSync=True,
                    allowCameraUpload=False,
                    allowChannels=True,
                    filterMovies=None,
                    filterTelevision=None,
                    filterMusic=None,
                )
            else:
                user = await self._run_in_executor(
                    self.server.myPlexAccount().addFriend,
                    user=username,
                    server=True,
                    allowSync=True,
                    allowCameraUpload=False,
                    allowChannels=True,
                )

            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "thumb": user.thumb,
                "restricted": restricted,
                "role": role,
                "created_at": user.createdAt.timestamp() if hasattr(user, "createdAt") else None,
            }
        except Exception:
            logger.exception("Error creating user {username}:")
            raise

    async def update_user(self, user_id: str, **kwargs) -> dict[str, Any]:
        """Update an existing Plex user.

        Args:
            user_id: ID of the user to update
            **kwargs: Fields to update (username, email, password, role, restricted)

        Returns:
            Updated user information
        """
        if not self._initialized:
            await self.connect()

        try:
            account = await self._run_in_executor(self.server.myPlexAccount)
            user = await self._run_in_executor(account.user, user_id)

            # Update fields if provided
            if "username" in kwargs:
                await self._run_in_executor(setattr, user, "username", kwargs["username"])
            if "email" in kwargs:
                await self._run_in_executor(setattr, user, "email", kwargs["email"])
            if "password" in kwargs:
                await self._run_in_executor(user.updatePassword, kwargs["password"])

            # For Plex Home users, update restrictions
            if "restricted" in kwargs and hasattr(user, "updateHomeUser"):
                await self._run_in_executor(
                    user.updateHomeUser,
                    allowSync=True,
                    allowCameraUpload=False,
                    allowChannels=True,
                    filterMovies=None,
                    filterTelevision=None,
                    filterMusic=None,
                    restricted=kwargs["restricted"],
                )

            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "restricted": getattr(user, "restricted", False),
                "role": "managed" if hasattr(user, "home") and user.home else "friend",
            }
        except Exception:
            logger.exception("Error updating user {user_id}:")
            raise

    async def delete_user(self, user_id: str) -> bool:
        """Delete a Plex user.

        Args:
            user_id: ID of the user to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            account = await self._run_in_executor(self.server.myPlexAccount)
            user = await self._run_in_executor(account.user, user_id)
            await self._run_in_executor(account.removeFriend, user)
            return True
        except Exception:
            logger.exception("Error deleting user {user_id}:")
            return False

    async def list_users(self) -> list[dict[str, Any]]:
        """List all Plex users.

        Returns:
            List of users with their information
        """
        if not self._initialized:
            await self.connect()

        try:
            account = await self._run_in_executor(self.server.myPlexAccount)
            users = await self._run_in_executor(account.users)

            return [
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "thumb": getattr(user, "thumb", ""),
                    "restricted": getattr(user, "restricted", False),
                    "role": "managed" if hasattr(user, "home") and user.home else "friend",
                    "created_at": user.createdAt.timestamp() if hasattr(user, "createdAt") else None,
                }
                for user in users
            ]
        except Exception:
            logger.exception("Error listing users:")
            return []

    async def get_user(self, user_id: str) -> dict[str, Any] | None:
        """Get a specific Plex user by ID.

        Args:
            user_id: ID of the user to retrieve

        Returns:
            User information if found, None otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            account = await self._run_in_executor(self.server.myPlexAccount)
            user = await self._run_in_executor(account.user, user_id)

            if not user:
                return None

            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "thumb": getattr(user, "thumb", ""),
                "restricted": getattr(user, "restricted", False),
                "role": "managed" if hasattr(user, "home") and user.home else "friend",
                "created_at": user.createdAt.timestamp() if hasattr(user, "createdAt") else None,
                "permissions": await self._get_user_permissions(user),
            }
        except Exception:
            logger.exception("Error getting user {user_id}:")
            return None

    async def update_user_permissions(self, user_id: str, permissions: dict[str, Any]) -> dict[str, Any]:
        """Update permissions for a Plex user.

        Args:
            user_id: ID of the user to update
            permissions: Dictionary of permissions to update

        Returns:
            Updated user information with new permissions
        """
        if not self._initialized:
            await self.connect()

        try:
            account = await self._run_in_executor(self.server.myPlexAccount)
            user = await self._run_in_executor(account.user, user_id)

            # Update permissions based on the provided dictionary
            # Note: Plex API has limited permission controls
            if "allowSync" in permissions:
                user.allowSync = permissions["allowSync"]
            if "allowCameraUpload" in permissions:
                user.allowCameraUpload = permissions["allowCameraUpload"]
            if "allowChannels" in permissions:
                user.allowChannels = permissions["allowChannels"]

            # Save changes
            await self._run_in_executor(user.save)

            # Return updated user info
            return {
                "id": user.id,
                "username": user.username,
                "permissions": {
                    "allowSync": user.allowSync,
                    "allowCameraUpload": user.allowCameraUpload,
                    "allowChannels": user.allowChannels,
                },
            }
        except Exception:
            logger.exception("Error updating permissions for user {user_id}:")
            raise

    # Library Management Methods

    async def scan_library(self, library_id: str, force: bool = False) -> dict[str, Any]:
        """Scan a library for new or updated files.

        Args:
            library_id: ID of the library to scan
            force: If True, force a full scan

        Returns:
            Dictionary with scan results
        """
        if not self._initialized:
            await self.connect()

        try:
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
            if force:
                await self._run_in_executor(section.update)
            else:
                await self._run_in_executor(section.refresh)

            return {
                "library_id": library_id,
                "library_name": section.title,
                "scan_successful": True,
                "full_scan": force,
            }
        except Exception:
            logger.exception("Error scanning library {library_id}:")
            raise

    async def refresh_library_metadata(self, library_id: str) -> bool:
        """Refresh metadata for a library.

        Args:
            library_id: ID of the library to refresh

        Returns:
            True if refresh was successful, False otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
            await self._run_in_executor(section.refresh)
            return True
        except Exception:
            logger.exception("Error refreshing library {library_id}:")
            return False

    async def optimize_library(self, library_id: str) -> bool:
        """Optimize a library database.

        Args:
            library_id: ID of the library to optimize

        Returns:
            True if optimization was successful, False otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            # Plex doesn't have a direct optimize method, so we'll clean bundles
            # and refresh metadata as an alternative
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
            await self._run_in_executor(section.cleanBundles)
            await self._run_in_executor(section.update)
            return True
        except Exception:
            logger.exception("Error optimizing library {library_id}:")
            return False

    async def get_library(self, library_id: str) -> dict[str, Any] | None:
        """Get information about a specific library.

        Args:
            library_id: ID of the library to retrieve

        Returns:
            Library information if found, None otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
            return self._format_library_section(section)
        except Exception:
            logger.exception("Error getting library {library_id}:")
            return None

    # Removed duplicate list_libraries - using the one at line 86

    async def add_library(
        self,
        name: str,
        libtype: str,
        agent: str,
        scanner: str,
        language: str,
        location: str,
        **kwargs,
    ) -> dict[str, Any] | None:
        """Add a new library.

        Args:
            name: Name of the new library
            libtype: Type of library (movie, show, artist, photo)
            agent: Metadata agent to use
            scanner: Scanner to use
            language: Language for metadata
            location: Path to the library content
            **kwargs: Additional library settings

        Returns:
            The created library information if successful, None otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            # Plex API doesn't support adding libraries directly, so we'll return
            # instructions for manual addition
            logger.warning(
                "Adding libraries programmatically is not directly supported by Plex API. "
                "Please add the library through the Plex web interface with these settings:\n"
                f"Name: {name}\n"
                f"Type: {libtype}\n"
                f"Agent: {agent}\n"
                f"Scanner: {scanner}\n"
                f"Language: {language}\n"
                f"Location: {location}"
            )
            return None
        except Exception:
            logger.exception("Error adding library {name}:")
            return None

    async def update_library(self, library_id: str, **kwargs) -> dict[str, Any] | None:
        """Update a library's settings.

        Args:
            library_id: ID of the library to update
            **kwargs: Fields to update (name, agent, scanner, language, thumb)

        Returns:
            The updated library information if successful, None otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))

            # Update fields if provided
            if "name" in kwargs:
                await self._run_in_executor(setattr, section, "title", kwargs["name"])
            if "agent" in kwargs:
                await self._run_in_executor(section.editAdvanced, agent=kwargs["agent"])
            if "scanner" in kwargs:
                await self._run_in_executor(section.editAdvanced, scanner=kwargs["scanner"])
            if "language" in kwargs:
                await self._run_in_executor(section.editAdvanced, language=kwargs["language"])
            if "thumb" in kwargs:
                await self._run_in_executor(section.uploadPoster, url=kwargs["thumb"])

            # Reload the section to get updated info
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
            return self._format_library_section(section)
        except Exception:
            logger.exception("Error updating library {library_id}:")
            return None

    async def delete_library(self, library_id: str) -> bool:
        """Delete a library.

        Args:
            library_id: ID of the library to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
            await self._run_in_executor(section.delete)
            return True
        except Exception:
            logger.exception("Error deleting library {library_id}:")
            return False

    async def add_library_location(self, library_id: str, path: str) -> bool:
        """Add a location to a library.

        Args:
            library_id: ID of the library
            path: Path to add to the library

        Returns:
            True if addition was successful, False otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
            await self._run_in_executor(section.addLocation, path)
            return True
        except Exception:
            logger.exception("Error adding location {path} to library {library_id}:")
            return False

    async def remove_library_location(self, library_id: str, path: str) -> bool:
        """Remove a location from a library.

        Args:
            library_id: ID of the library
            path: Path to remove from the library

        Returns:
            True if removal was successful, False otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
            await self._run_in_executor(section.removeLocation, path)
            return True
        except Exception:
            logger.exception("Error removing location {path} from library {library_id}:")
            return False

    async def get_library_items(
        self,
        library_id: str,
        limit: int = 100,
        offset: int = 0,
        sort: str | None = None,
        **filters,
    ) -> dict[str, Any]:
        """Get items from a library.

        Args:
            library_id: ID of the library
            limit: Maximum number of items to return
            offset: Offset for pagination
            sort: Sort field (e.g., 'titleSort', 'addedAt', 'lastViewedAt')
            **filters: Filter criteria (e.g., genre='Action', year=2020)

        Returns:
            Dictionary with items and pagination info
        """
        if not self._initialized:
            await self.connect()

        try:
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))

            # Get all items from section
            all_items = await self._run_in_executor(lambda: section.all())

            # Apply filters if any
            items = all_items
            for key, value in filters.items():
                items = [item for item in items if getattr(item, key, None) == value]

            # Apply sorting
            if sort:
                reverse = sort.startswith("-")
                sort_key = sort.lstrip("-")
                items = sorted(items, key=lambda x: getattr(x, sort_key, ""), reverse=reverse)

            # Apply pagination
            total = len(items)
            items = items[offset : offset + limit]

            # Format items - _format_media_item is async so we need to await each
            formatted_items = []
            for item in items:
                try:
                    formatted = await self._format_media_item(item)
                    if formatted:
                        formatted_items.append(formatted)
                except Exception as e:
                    logger.warning(f"Failed to format item {getattr(item, 'title', 'unknown')}: {e}")
                    continue

            return {
                "items": formatted_items,
                "total": total,
                "offset": offset,
                "limit": limit,
            }
        except Exception:
            logger.exception("Error getting items from library {library_id}:")
            return {"items": [], "total": 0, "offset": 0, "limit": limit}

    async def empty_trash(self, library_id: str) -> bool:
        """Empty the trash for a library.

        Args:
            library_id: ID of the library

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
            await self._run_in_executor(section.emptyTrash)
            return True
        except Exception:
            logger.exception("Error emptying trash for library {library_id}:")
            return False

    async def clean_bundles(self, library_id: str | None = None) -> dict[str, Any]:
        """Clean old bundles for a library or all libraries.

        Args:
            library_id: Optional ID of the library to clean

        Returns:
            Dictionary with cleanup results
        """
        if not self._initialized:
            await self.connect()

        try:
            if library_id:
                section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
                await self._run_in_executor(section.cleanBundles)
                return {
                    "library_id": library_id,
                    "library_name": section.title,
                    "cleaned": True,
                }
            await self._run_in_executor(self.server.library.cleanBundles)
            return {"all_libraries": True, "cleaned": True}
        except Exception as e:
            logger.exception("Error cleaning bundles:")
            return {"cleaned": False, "error": str(e)}

    def _format_library_section(self, section) -> dict[str, Any]:
        """Format a library section into a dictionary."""
        return {
            "id": section.key,
            "title": section.title,
            "type": section.type,
            "agent": section.agent,
            "scanner": section.scanner,
            "language": section.language,
            "uuid": section.uuid,
            "updated_at": section.updatedAt.timestamp() if hasattr(section, "updatedAt") else 0,
            "scanned_at": section.scannedAt.timestamp() if hasattr(section, "scannedAt") else 0,
            "count": len(section.all()),
            "locations": [loc for loc in section.locations] if hasattr(section, "locations") else [],
        }

    async def _format_media_item(self, item) -> dict[str, Any]:
        """Format a media item into a dictionary."""
        if not item:
            return None

        def safe_ts(dt):
            try:
                return dt.timestamp() if dt else 0
            except Exception:
                return 0

        # Handle Role/Director objects which have 'tag' instead of 'title'
        title = getattr(item, "title", getattr(item, "tag", "Unknown"))
        rating_key = getattr(item, "ratingKey", getattr(item, "id", ""))

        # Basic result structure
        result = {
            "id": str(rating_key),
            "title": title,
            "type": getattr(item, "type", "unknown"),
            "year": getattr(item, "year", None),
            "thumb": getattr(item, "thumb", ""),
            "art": getattr(item, "art", ""),
            "summary": getattr(item, "summary", ""),
            "rating_key": str(rating_key),
            "key": getattr(item, "key", ""),
        }

        # Add timestamp fields safely
        if hasattr(item, "addedAt"):
            result["added_at"] = safe_ts(item.addedAt)
        if hasattr(item, "updatedAt"):
            result["updated_at"] = safe_ts(item.updatedAt)
        if hasattr(item, "lastViewedAt"):
            result["last_viewed_at"] = safe_ts(item.lastViewedAt)

        # Add other common fields if present
        if hasattr(item, "viewCount"):
            result["view_count"] = item.viewCount
        if hasattr(item, "contentRating"):
            result["content_rating"] = item.contentRating
        if hasattr(item, "rating"):
            result["rating"] = item.rating
        if hasattr(item, "audienceRating"):
            result["audience_rating"] = item.audienceRating
        if hasattr(item, "duration"):
            result["duration"] = item.duration / 60000 if item.duration else 0
        if hasattr(item, "guid"):
            result["guid"] = item.guid

        # Type-specific fields
        if hasattr(item, "originalTitle"):
            result["original_title"] = item.originalTitle

        if hasattr(item, "studio"):
            result["studio"] = item.studio

        if hasattr(item, "tagline"):
            result["tagline"] = item.tagline

        if hasattr(item, "originallyAvailableAt"):
            result["originally_available_at"] = safe_ts(item.originallyAvailableAt)

        # Collections and genres
        if hasattr(item, "collections"):
            result["collections"] = [c.tag for c in item.collections]

        if hasattr(item, "genres"):
            result["genres"] = [g.tag for g in item.genres]

        # People
        if hasattr(item, "directors"):
            result["directors"] = [d.tag for d in item.directors]

        if hasattr(item, "writers"):
            result["writers"] = [w.tag for w in item.writers]

        if hasattr(item, "roles"):
            result["actors"] = [{"name": r.tag, "role": r.role} for r in item.roles]

        # Library info
        if hasattr(item, "librarySectionID"):
            result["library_section_id"] = item.librarySectionID

        if hasattr(item, "librarySectionTitle"):
            result["library_section_title"] = item.librarySectionTitle

        # Media info
        if hasattr(item, "media"):
            result["media_info"] = [
                {
                    "video_codec": m.videoCodec if hasattr(m, "videoCodec") else None,
                    "video_resolution": m.videoResolution if hasattr(m, "videoResolution") else None,
                    "video_frame_rate": m.videoFrameRate if hasattr(m, "videoFrameRate") else None,
                    "audio_codec": m.audioCodec if hasattr(m, "audioCodec") else None,
                    "audio_channels": m.audioChannels if hasattr(m, "audioChannels") else None,
                    "container": m.container if hasattr(m, "container") else None,
                    "bitrate": m.bitrate if hasattr(m, "bitrate") else None,
                    "width": m.width if hasattr(m, "width") else None,
                    "height": m.height if hasattr(m, "height") else None,
                    "aspect_ratio": m.aspectRatio if hasattr(m, "aspectRatio") else None,
                    "duration": m.duration if hasattr(m, "duration") else None,
                }
                for m in item.media
            ]

        return result

    async def advanced_search_media(
        self,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
        library_id: str | None = None,
        media_type: str | None = None,
        title: str | None = None,
        year: int | list[int] | str | None = None,
        decade: int | None = None,
        genre: str | list[str] | None = None,
        actor: str | list[str] | None = None,
        director: str | list[str] | None = None,
        content_rating: str | list[str] | None = None,
        studio: str | list[str] | None = None,
        country: str | list[str] | None = None,
        language: str | list[str] | None = None,
        collection: str | list[str] | None = None,
        min_rating: float | None = None,
        max_rating: float | None = None,
        min_year: int | None = None,
        max_year: int | None = None,
        unwatched: bool | None = None,
        sort_by: str = "titleSort",
        sort_dir: str = "asc",
        **kwargs,
    ) -> dict[str, Any]:
        """Advanced search for media with extensive filtering options.

        Args:
            query: General search term (searches across multiple fields)
            limit: Maximum number of results to return (1-1000)
            offset: Offset for pagination
            library_id: Optional library ID to search within
            media_type: Filter by media type (movie, show, season, episode, artist, album, track, photo)
            title: Filter by title (supports wildcards with *)
            year: Filter by specific year or list of years
            decade: Filter by decade (e.g., 2020 for 2020s)
            genre: Filter by genre (single or list)
            actor: Filter by actor (single or list)
            director: Filter by director (single or list)
            content_rating: Filter by content rating (e.g., 'PG', 'R', 'TV-MA')
            studio: Filter by studio
            country: Filter by country
            language: Filter by language code (e.g., 'en', 'ja', 'es')
            collection: Filter by collection
            min_rating: Minimum user rating (0-10)
            max_rating: Maximum user rating (0-10)
            min_year: Minimum release year
            max_year: Maximum release year
            unwatched: Only show unwatched items
            sort_by: Field to sort by (e.g., 'titleSort', 'year', 'rating', 'addedAt', 'lastViewedAt')
            sort_dir: Sort direction ('asc' or 'desc')
            **kwargs: Additional filters

        Returns:
            Dictionary with search results and pagination info
        """
        if not self._initialized:
            await self.connect()

        try:
            # Prepare filters
            filters = {}

            # Basic filters
            if media_type:
                filters["libtype"] = media_type
            if title:
                filters["title"] = title
            if year:
                filters["year"] = year
            if decade:
                filters["decade"] = decade

            # List filters
            for field in [
                "genre",
                "actor",
                "director",
                "content_rating",
                "studio",
                "country",
                "language",
                "collection",
            ]:
                value = locals()[field]
                if value:
                    if isinstance(value, str):
                        value = [value]
                    filters[f"{field}"] = value

            # Range filters
            if min_rating is not None:
                filters["userRating>"] = min_rating
            if max_rating is not None:
                filters["userRating<"] = max_rating
            if min_year is not None:
                filters["year>"] = min_year
            if max_year is not None:
                filters["year<"] = max_year

            # Special filters
            if unwatched is not None:
                filters["unwatched"] = unwatched

            # Sorting
            if sort_dir.lower() not in ("asc", "desc"):
                sort_dir = "asc"
            sort = f"{sort_dir.lower()}:{sort_by}"

            # Search in specific library or across all
            if library_id:
                section = await self._run_in_executor(lambda: self.server.library.sectionByID(int(library_id)))
                search_func = section.search
            else:
                search_func = self.server.library.search

            # Execute search
            results = await self._run_in_executor(
                lambda: search_func(
                    title=query,
                    sort=sort,
                    maxresults=min(limit, 1000),  # Plex API limit
                    **filters,
                    **kwargs,
                )
            )

            # Apply pagination
            total = len(results)
            paginated_results = results[offset : offset + limit]

            return {
                "items": [await self._format_media_item(item) for item in paginated_results if item is not None],
                "total": total,
                "offset": offset,
                "limit": limit,
                "filters": filters,
            }

        except Exception as e:
            logger.exception("Error searching media:")
            return {
                "items": [],
                "total": 0,
                "offset": offset,
                "limit": limit,
                "error": str(e),
            }

    async def get_media_info(self, media_id: str) -> dict[str, Any] | None:
        """Get detailed information about a media item.

        Args:
            media_id: ID of the media item

        Returns:
            Media item details or None if not found
        """
        if not self._initialized:
            await self.connect()

        try:
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))
            return await self._format_media_item(item)
        except Exception:
            logger.exception("Error getting media info for {media_id}:")
            return None

    async def update_media(self, media_id: str, **updates) -> dict[str, Any] | None:
        """Update media item metadata.

        Args:
            media_id: ID of the media item to update
            **updates: Fields to update (e.g., title, summary, year)

        Returns:
            Updated media item or None if update failed
        """
        if not self._initialized:
            await self.connect()

        try:
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))

            # Apply updates
            for key, value in updates.items():
                if hasattr(item, f"set{key.capitalize()}"):
                    await self._run_in_executor(getattr(item, f"set{key.capitalize()}"))(value)
                elif hasattr(item, key):
                    await self._run_in_executor(setattr, item, key, value)

            # Reload the item to get updated data
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))

            return await self._format_media_item(item)

        except Exception:
            logger.exception("Error updating media {media_id}:")
            return None

    async def delete_media(self, media_id: str) -> bool:
        """Delete a media item.

        Args:
            media_id: ID of the media item to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))
            await self._run_in_executor(item.delete)
            return True
        except Exception:
            logger.exception("Error deleting media {media_id}:")
            return False

    async def rate_media(self, media_id: str, rating: float) -> bool:
        """Rate a media item.

        Args:
            media_id: ID of the media item to rate
            rating: Rating value (0-10)

        Returns:
            True if rating was successful, False otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))
            await self._run_in_executor(item.rate, rating)
            return True
        except Exception:
            logger.exception("Error rating media {media_id}:")
            return False

    async def mark_watched(self, media_id: str) -> bool:
        """Mark a media item as watched.

        Args:
            media_id: ID of the media item

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))
            await self._run_in_executor(item.markWatched)
            return True
        except Exception:
            logger.exception("Error marking media {media_id} as watched:")
            return False

    async def mark_unwatched(self, media_id: str) -> bool:
        """Mark a media item as unwatched.

        Args:
            media_id: ID of the media item

        Returns:
            True if successful, False otherwise
        """
        if not self._initialized:
            await self.connect()

        try:
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))
            await self._run_in_executor(item.markUnwatched)
            return True
        except Exception:
            logger.exception("Error marking media {media_id} as unwatched:")
            return False

    async def get_media_streams(self, media_id: str) -> list[dict[str, Any]]:
        """Get stream information for a media item.

        Args:
            media_id: ID of the media item

        Returns:
            List of stream information dictionaries
        """
        if not self._initialized:
            await self.connect()

        try:
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))

            streams = []
            for media in item.media:
                for part in media.parts:
                    for stream in part.streams:
                        stream_info = {
                            "type": stream.streamType,
                            "codec": stream.codec,
                            "bitrate": getattr(stream, "bitrate", None),
                            "language": getattr(stream, "language", None),
                            "language_code": getattr(stream, "languageCode", None),
                            "channels": getattr(stream, "channels", None),
                            "width": getattr(stream, "width", None),
                            "height": getattr(stream, "height", None),
                            "duration": getattr(stream, "duration", None),
                            "bit_depth": getattr(stream, "bitDepth", None),
                            "chroma_subsampling": getattr(stream, "chromaSubsampling", None),
                            "frame_rate": getattr(stream, "frameRate", None),
                            "profile": getattr(stream, "profile", None),
                            "ref_frames": getattr(stream, "refFrames", None),
                            "sampling_rate": getattr(stream, "samplingRate", None),
                            "selected": getattr(stream, "selected", False),
                            "stream_identifier": getattr(stream, "streamIdentifier", None),
                            "title": getattr(stream, "title", None),
                        }
                        streams.append(stream_info)

            return streams

        except Exception:
            logger.exception("Error getting streams for media {media_id}:")
            return []

    async def get_related_media(self, media_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Get related media items.

        Args:
            media_id: ID of the media item
            limit: Maximum number of related items to return

        Returns:
            List of related media items
        """
        if not self._initialized:
            await self.connect()

        try:
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))

            related = []
            if hasattr(item, "related"):
                related_items = await self._run_in_executor(lambda: item.related(maxresults=limit))
                related = [await self._format_media_item(i) for i in related_items]

            return related

        except Exception:
            logger.exception("Error getting related media for {media_id}:")
            return []

    async def get_media_children(self, media_id: str, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """Get child items for a media item (e.g., episodes for a show).

        Args:
            media_id: ID of the parent media item
            limit: Maximum number of items to return
            offset: Offset for pagination

        Returns:
            Dictionary with items and pagination info
        """
        if not self._initialized:
            await self.connect()

        try:
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))

            if not hasattr(item, "children") or not callable(item.children):
                return {"items": [], "total": 0, "offset": 0, "limit": limit}

            children = await self._run_in_executor(item.children)
            total = len(children)
            items = children[offset : offset + limit]

            return {
                "items": [await self._format_media_item(i) for i in items],
                "total": total,
                "offset": offset,
                "limit": limit,
            }

        except Exception:
            logger.exception("Error getting children for media {media_id}:")
            return {"items": [], "total": 0, "offset": 0, "limit": limit}

    async def get_media_metadata(self, media_id: str) -> dict[str, Any]:
        """Get metadata for a media item.

        Args:
            media_id: ID of the media item

        Returns:
            Dictionary with metadata
        """
        if not self._initialized:
            await self.connect()

        try:
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))

            metadata = {
                "id": item.ratingKey,
                "title": item.title,
                "type": item.type,
                "metadata": {},
            }

            # Get all available attributes
            for attr in dir(item):
                if not attr.startswith("_") and not callable(getattr(item, attr)):
                    try:
                        value = getattr(item, attr)
                        # Skip large binary data or complex objects
                        if not isinstance(value, (bytes, bytearray, type(item))):
                            metadata["metadata"][attr] = value
                    except Exception:
                        continue

            return metadata

        except Exception:
            logger.exception("Error getting metadata for media {media_id}:")
            return {}

    async def get_media_analysis(self, media_id: str) -> dict[str, Any]:
        """Get analysis data for a media item.

        Args:
            media_id: ID of the media item

        Returns:
            Dictionary with analysis data
        """
        if not self._initialized:
            await self.connect()

        try:
            item = await self._run_in_executor(lambda: self.server.fetchItem(int(media_id)))

            analysis = {
                "id": item.ratingKey,
                "title": item.title,
                "type": item.type,
                "analysis": {},
            }

            # Get media parts and streams
            if hasattr(item, "media") and item.media:
                analysis["media"] = []
                for media in item.media:
                    media_info = {
                        "id": media.id,
                        "duration": media.duration,
                        "bitrate": media.bitrate,
                        "width": media.width,
                        "height": media.height,
                        "aspect_ratio": media.aspectRatio,
                        "video_codec": media.videoCodec,
                        "video_resolution": media.videoResolution,
                        "video_frame_rate": media.videoFrameRate,
                        "audio_codec": media.audioCodec,
                        "audio_channels": media.audioChannels,
                        "container": media.container,
                        "parts": [],
                    }

                    for part in media.parts:
                        part_info = {
                            "id": part.id,
                            "file": part.file,
                            "size": part.size,
                            "duration": part.duration,
                            "streams": [],
                        }

                        for stream in part.streams:
                            stream_info = {
                                "id": stream.id,
                                "type": stream.streamType,
                                "codec": stream.codec,
                                "index": stream.index,
                                "channels": getattr(stream, "channels", None),
                                "bitrate": getattr(stream, "bitrate", None),
                                "language": getattr(stream, "language", None),
                                "language_code": getattr(stream, "languageCode", None),
                                "profile": getattr(stream, "profile", None),
                                "selected": getattr(stream, "selected", False),
                            }

                            if stream.streamType == "video":
                                stream_info.update(
                                    {
                                        "width": stream.width,
                                        "height": stream.height,
                                        "aspect_ratio": stream.aspectRatio,
                                        "frame_rate": stream.frameRate,
                                        "bit_depth": getattr(stream, "bitDepth", None),
                                        "chroma_subsampling": getattr(stream, "chromaSubsampling", None),
                                        "ref_frames": getattr(stream, "refFrames", None),
                                        "scan_type": getattr(stream, "scanType", None),
                                    }
                                )
                            elif stream.streamType == "audio":
                                stream_info.update(
                                    {
                                        "channels": stream.channels,
                                        "sampling_rate": getattr(stream, "samplingRate", None),
                                        "bitrate_mode": getattr(stream, "bitrateMode", None),
                                        "audio_channel_layout": getattr(stream, "audioChannelLayout", None),
                                    }
                                )
                            elif stream.streamType == "subtitle":
                                stream_info.update(
                                    {
                                        "format": getattr(stream, "format", None),
                                        "title": getattr(stream, "title", None),
                                        "forced": getattr(stream, "forced", False),
                                        "hearing_impaired": getattr(stream, "hearingImpaired", False),
                                    }
                                )

                            part_info["streams"].append(stream_info)

                        media_info["parts"].append(part_info)

                    analysis["media"].append(media_info)

            return analysis

        except Exception:
            logger.exception("Error getting analysis for media {media_id}:")
            return {}

    async def _get_user_permissions(self, user) -> dict[str, Any]:
        """Helper method to get user permissions."""
        return {
            "allowSync": getattr(user, "allowSync", False),
            "allowCameraUpload": getattr(user, "allowCameraUpload", False),
            "allowChannels": getattr(user, "allowChannels", False),
            "restricted": getattr(user, "restricted", False),
        }

    async def close(self) -> None:
        """Close the Plex service connection."""
        if self._initialized:
            self._initialized = False
        logger.info("Plex service closed")

    # Context manager support
    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def get_sessions(self) -> list[dict[str, Any]]:
        """Get all active Plex sessions."""
        if not self._initialized:
            await self.connect()
        try:
            return await self._run_in_executor(self._get_sessions_sync)
        except Exception:
            logger.exception("Failed to get sessions:")
            return []

    def _get_sessions_sync(self) -> list[dict[str, Any]]:
        """Synchronous helper to get sessions."""
        if not self.server:
            raise RuntimeError("Not connected to Plex server")
        sessions = []
        for session in self.server.sessions():
            sessions.append(
                {
                    "id": getattr(session, "sessionKey", ""),
                    "title": session.title,
                    "type": session.type,
                    "grandparent_title": getattr(session, "grandparentTitle", ""),
                    "parent_title": getattr(session, "parentTitle", ""),
                    "thumb": getattr(session, "thumb", ""),
                    "duration": getattr(session, "duration", 0),
                    "view_offset": getattr(session, "viewOffset", 0),
                    "player": {
                        "title": session.player.title if hasattr(session, "player") else "",
                        "product": session.player.product if hasattr(session, "player") else "",
                        "state": session.player.state if hasattr(session, "player") else "",
                        "machineIdentifier": session.player.machineIdentifier if hasattr(session, "player") else "",
                    },
                    "user": session.usernames[0] if hasattr(session, "usernames") and session.usernames else "",
                }
            )
        return sessions

    async def get_clients(self) -> list[dict[str, Any]]:
        """Get all available Plex clients."""
        if not self._initialized:
            await self.connect()
        try:
            clients = await self._run_in_executor(self._get_clients_sync)
            logger.info(f"get_clients returning {len(clients)} clients")
            return clients
        except Exception:
            logger.exception("Failed to get clients:")
            return []

    def _get_media_type(self, media_key: str) -> str | None:
        """Get media type from media_key by fetching the item."""
        if not self.server:
            return None
        try:
            item = self.server.fetchItem(int(media_key))
            media_type = getattr(item, "type", None)
            logger.debug(f"Media key {media_key} has type: {media_type}")
            return media_type
        except Exception as e:
            logger.warning(f"Failed to get media type for {media_key}: {e}")
            return None

    def _select_client_for_media(self, media_type: str, clients: list[dict[str, Any]]) -> dict[str, Any] | None:
        """Select the best client for a given media type.

        Rules:
        - Music and audiobooks → PlexAmp (if available)
        - Movies, TV shows, etc. → Plex Web or Plex app (video-capable clients)
        """
        if not clients:
            return None

        # Audio-only media types
        audio_types = {"track", "album", "artist"}
        is_audio = media_type in audio_types or "music" in media_type.lower() or "audiobook" in media_type.lower()

        if is_audio:
            # Prefer PlexAmp for audio
            for client in clients:
                product = client.get("product", "").lower()
                if "plexamp" in product:
                    logger.info(f"Selected PlexAmp client '{client.get('name')}' for audio media type '{media_type}'")
                    return client
            # Fall back to any client if PlexAmp not available
            logger.info("No PlexAmp found, using first available client for audio")
            return clients[0]
        # For video content, prefer video-capable clients (not PlexAmp)
        video_clients = []
        for client in clients:
            product = client.get("product", "").lower()
            # Exclude PlexAmp for video
            if "plexamp" not in product:
                video_clients.append(client)

        if video_clients:
            # Prefer Plex Web or Plex app
            for client in video_clients:
                product = client.get("product", "").lower()
                if "plex web" in product or "plex" in product:
                    logger.info(
                        f"Selected video client '{client.get('name')}' ({product}) for media type '{media_type}'"
                    )
                    return client
            # Fall back to first video-capable client
            logger.info(
                f"Using first video-capable client '{video_clients[0].get('name')}' for media type '{media_type}'"
            )
            return video_clients[0]
        # No video clients available, return first client anyway
        logger.warning(f"No video-capable clients found, using first available client for media type '{media_type}'")
        return clients[0]

    def _find_client_by_id(self, client_identifier: str):
        """Helper method to find a client by machineIdentifier using all available methods.

        This is more reliable than just using server.clients() which might miss some clients.
        Uses the same multi-source approach as _get_clients_sync.
        """
        if not self.server:
            return None

        # Try Method 1: Direct clients()
        try:
            for client in self.server.clients():
                if client.machineIdentifier == client_identifier:
                    return client
        except Exception:
            pass

        # Try Method 2: From active sessions
        try:
            for session in self.server.sessions():
                if hasattr(session, "players") and session.players:
                    for player in session.players:
                        if player.machineIdentifier == client_identifier:
                            return player
        except Exception:
            pass

        # Try Method 3: From account resources (same as _get_clients_sync)
        try:
            account = self.server.myPlexAccount()
            resources = account.resources()
            for resource in resources:
                provides = getattr(resource, "provides", "")
                is_client = provides and ("player" in provides or "client" in provides.lower())
                is_server = provides and "server" in provides
                if is_client and not is_server:
                    machine_id = getattr(resource, "clientIdentifier", getattr(resource, "machineIdentifier", ""))
                    if machine_id == client_identifier:
                        return resource
        except Exception:
            pass

        return None

    def _get_clients_sync(self) -> list[dict[str, Any]]:
        """Synchronous helper to get clients.

        Gets clients from multiple sources:
        1. server.clients() - actively discoverable clients via GDM
        2. Active sessions - clients that have active sessions (even if paused)
        3. Direct HTTP API call to /clients endpoint as fallback
        """
        if not self.server:
            raise RuntimeError("Not connected to Plex server")

        clients_dict = {}  # Use dict to deduplicate by machineIdentifier

        # Method 1: Get directly discoverable clients via plexapi
        try:
            for client in self.server.clients():
                machine_id = client.machineIdentifier
                clients_dict[machine_id] = {
                    "name": client.title,
                    "product": client.product,
                    "platform": client.platform,
                    "version": getattr(client, "version", ""),
                    "address": getattr(client, "address", ""),
                    "port": getattr(client, "port", 32400),
                    "protocol": getattr(client, "protocol", "http"),
                    "device": getattr(client, "device", ""),
                    "device_name": getattr(client, "deviceName", client.title),
                    "id": machine_id,
                    "machineIdentifier": machine_id,
                    "local": getattr(client, "local", True),
                }
        except Exception as e:
            logger.warning(f"Failed to get clients via server.clients(): {e}")

        # Method 2: Get clients from active sessions (catches clients that might not be discoverable)
        try:
            for session in self.server.sessions():
                if hasattr(session, "players") and session.players:
                    for player in session.players:
                        machine_id = player.machineIdentifier
                        if machine_id not in clients_dict:
                            # Extract client info from player
                            clients_dict[machine_id] = {
                                "name": getattr(player, "title", "Unknown Client"),
                                "product": getattr(player, "product", "Unknown"),
                                "platform": getattr(player, "platform", "Unknown"),
                                "version": getattr(player, "version", ""),
                                "address": getattr(player, "address", ""),
                                "port": getattr(player, "port", 32400),
                                "protocol": getattr(player, "protocol", "http"),
                                "device": getattr(player, "device", ""),
                                "device_name": getattr(player, "deviceName", getattr(player, "title", "Unknown")),
                                "id": machine_id,
                                "machineIdentifier": machine_id,
                                "local": getattr(player, "local", True),
                                "state": getattr(player, "state", ""),  # playing, paused, stopped
                            }
        except Exception as e:
            logger.warning(f"Failed to get clients from sessions: {e}")

        # Method 3: Try using myPlexAccount().resources() which lists all resources including clients
        # This can find clients that aren't currently discoverable via GDM
        try:
            account = self.server.myPlexAccount()
            resources = account.resources()
            logger.debug(f"Found {len(resources)} resources from account")
            for resource in resources:
                # Resources include both servers and clients
                # Check what this resource provides
                provides = getattr(resource, "provides", "")
                logger.debug(
                    f"Resource: {getattr(resource, 'name', 'Unknown')}, provides: {provides}, product: {getattr(resource, 'product', 'Unknown')}"
                )

                # Filter for client-capable resources (those that provide player functionality)
                # Also include resources that are clients (not servers)
                is_client = provides and ("player" in provides or "client" in provides.lower())
                is_server = provides and "server" in provides

                if is_client and not is_server:
                    machine_id = getattr(resource, "clientIdentifier", getattr(resource, "machineIdentifier", ""))
                    if machine_id and machine_id not in clients_dict:
                        # Get connection info from resource
                        connections = getattr(resource, "connections", [])
                        address = ""
                        port = 32400
                        protocol = "http"
                        if connections:
                            # Use the first local connection if available
                            local_conn = next((c for c in connections if getattr(c, "local", False)), None)
                            if local_conn:
                                address = getattr(local_conn, "address", "")
                                port = getattr(local_conn, "port", 32400)
                                protocol = getattr(local_conn, "protocol", "http")
                            elif connections:
                                # Fall back to first connection
                                conn = connections[0]
                                address = getattr(conn, "address", "")
                                port = getattr(conn, "port", 32400)
                                protocol = getattr(conn, "protocol", "http")

                        clients_dict[machine_id] = {
                            "name": getattr(resource, "name", "Unknown Client"),
                            "product": getattr(resource, "product", "Unknown"),
                            "platform": getattr(resource, "platform", "Unknown"),
                            "version": getattr(resource, "version", ""),
                            "address": address,
                            "port": port,
                            "protocol": protocol,
                            "device": getattr(resource, "device", ""),
                            "device_name": getattr(resource, "name", "Unknown"),
                            "id": machine_id,
                            "machineIdentifier": machine_id,
                            "local": any(getattr(c, "local", False) for c in connections) if connections else True,
                        }
                        logger.debug(
                            f"Added client from resources: {getattr(resource, 'name', 'Unknown')} ({machine_id})"
                        )
        except AttributeError as e:
            # myPlexAccount() or resources() might not be available
            logger.debug(f"myPlexAccount().resources() not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to get clients via account resources(): {e}", exc_info=True)

        # Log what we found
        client_names = [c["name"] for c in clients_dict.values()]
        logger.info(f"Found {len(clients_dict)} clients: {client_names}")

        # Convert dict to list
        return list(clients_dict.values())

    async def play_media(self, client_identifier: str, media_key: str) -> bool:
        """Play media on a specific client."""
        if not self._initialized:
            await self.connect()
        try:
            return await self._run_in_executor(self._play_media_sync, client_identifier, media_key)
        except Exception:
            logger.exception("Failed to play media:")
            return False

    def _play_media_sync(self, client_identifier: str, media_key: str) -> bool:
        """Synchronous helper to play media."""
        if not self.server:
            raise RuntimeError("Not connected to Plex server")
        try:
            # Get media item first to ensure it exists
            try:
                media_item = self.server.fetchItem(int(media_key))
                media_type = getattr(media_item, "type", "video")
                logger.debug(f"Playing {media_type}: {getattr(media_item, 'title', 'Unknown')}")
            except Exception:
                logger.exception("Could not fetch media item {media_key}:")
                return False

            # First, try plexapi client.playMedia() if available (most reliable)
            plexapi_client = None
            try:
                for c in self.server.clients():
                    if c.machineIdentifier == client_identifier:
                        plexapi_client = c
                        break
            except:
                pass

            if plexapi_client and hasattr(plexapi_client, "playMedia"):
                try:
                    logger.info(f"Using plexapi client.playMedia() for {plexapi_client.title}")
                    plexapi_client.playMedia(media_item)
                    logger.info("SUCCESS: Started playback via plexapi")
                    return True
                except Exception as e:
                    logger.warning(f"plexapi playMedia failed: {e}, trying HTTP API")

            # Get client info we already discovered (from _get_clients_sync)
            # This includes clients found via sessions, account resources, etc.
            found_client = self._find_client_by_id(client_identifier)
            if found_client:
                # Get client address/port for direct HTTP
                if isinstance(found_client, dict):
                    found_client.get("address", "")
                    found_client.get("port", 32400)
                    found_client.get("name", "Unknown")
                else:
                    getattr(found_client, "address", "")
                    getattr(found_client, "port", 32400)
                    getattr(found_client, "title", getattr(found_client, "name", "Unknown"))

                # For Plex Web and Plex for Windows, we need to use server API routing
                # Direct HTTP won't work (address is 127.0.0.1 or server address)
                import urllib.parse

                import requests

                # Try server-side client control endpoint
                # Try /system/players/{player}/playback/playMedia endpoint (from Plex API docs)
                server_url = f"{self.base_url}/system/players/{client_identifier}/playback/playMedia"
                params = {
                    "key": f"/library/metadata/{media_key}",
                    "path": f"{self.base_url}/library/metadata/{media_key}",
                    "offset": "0",
                }

                full_url = f"{server_url}?{urllib.parse.urlencode(params)}"
                headers = {"X-Plex-Token": self.token}

                logger.info(f"Trying /system/players endpoint: {full_url}")
                response = requests.post(full_url, headers=headers, timeout=15)

                logger.info(f"Response: {response.status_code} - {response.text[:300]}")

                if response.status_code in (200, 201, 204):
                    logger.info("SUCCESS: Started playback via /system/players")
                    return True

                # Fallback: Try /player/playback/playMedia
                server_url2 = f"{self.base_url}/player/playback/playMedia"
                params2 = {
                    "commandID": "1",
                    "machineIdentifier": client_identifier,
                    "key": f"/library/metadata/{media_key}",
                    "offset": "0",
                }

                full_url2 = f"{server_url2}?{urllib.parse.urlencode(params2)}"
                logger.info(f"Trying /player/playback endpoint: {full_url2}")
                response2 = requests.post(full_url2, headers=headers, timeout=15)

                logger.info(f"Response2: {response2.status_code} - {response2.text[:300]}")

                if response2.status_code in (200, 201, 204):
                    logger.info("SUCCESS: Started playback via /player/playback")
                    return True
                logger.error("Both endpoints failed")

            logger.error(f"Client {client_identifier} not found or not controllable")
            return False
        except Exception:
            logger.exception("Error playing media:")
            return False

    def _send_client_command(self, client: Any, command: str, params: dict[str, Any] | None = None) -> bool:
        """Send a playback command to a Plex client.

        Tries multiple methods in order:
        1. Use plexapi client object methods (most reliable)
        2. Direct HTTP to client (for directly accessible clients)
        3. Fallback to server API routing (may not work for all clients)
        """
        import urllib.parse

        import requests

        try:
            # Get client identifier and info
            if isinstance(client, dict):
                client_identifier = client.get("machineIdentifier", client.get("id", ""))
                client_name = client.get("name", "Unknown Client")
                client_address = client.get("address", "")
                client_port = client.get("port", 32400)
            else:
                client_identifier = getattr(client, "machineIdentifier", getattr(client, "id", ""))
                client_name = getattr(client, "title", getattr(client, "name", "Unknown Client"))
                client_address = getattr(client, "address", "")
                client_port = getattr(client, "port", 32400)

            if not client_identifier:
                logger.error("Cannot send command: client missing machineIdentifier")
                return False

            # Method 1: Try to get plexapi client object and use its methods
            try:
                for c in self.server.clients():
                    if c.machineIdentifier == client_identifier:
                        # Use plexapi's built-in methods
                        if command == "pause" and hasattr(c, "pause"):
                            c.pause()
                            logger.info(f"SUCCESS: Paused {c.title} via plexapi")
                            return True
                        if command == "play" and hasattr(c, "play"):
                            c.play()
                            logger.info(f"SUCCESS: Played {c.title} via plexapi")
                            return True
                        if command == "stop" and hasattr(c, "stop"):
                            c.stop()
                            logger.info(f"SUCCESS: Stopped {c.title} via plexapi")
                            return True
                        break
            except Exception as e:
                logger.debug(f"plexapi client method failed: {e}")

            # Method 2: Direct HTTP to client (if address available)
            if client_address and command != "playMedia":  # playMedia handled separately
                try:
                    client_url = f"http://{client_address}:{client_port}/player/playback/{command}"
                    query_params = {"commandID": "1"}
                    if params:
                        query_params.update(params)

                    full_url = f"{client_url}?{urllib.parse.urlencode(query_params)}"
                    headers = {"X-Plex-Token": self.token}

                    logger.debug(f"Direct HTTP to {client_name}: {full_url}")
                    response = requests.get(full_url, headers=headers, timeout=10)

                    if response.status_code in (200, 201, 204):
                        logger.info(f"SUCCESS: Command '{command}' sent to {client_name} via direct HTTP")
                        return True
                except Exception as e:
                    logger.debug(f"Direct HTTP failed: {e}")

            # Method 3: Fallback - try server API routing (may not work)
            server_url = f"{self.base_url}/player/playback/{command}"
            query_params = {
                "commandID": "1",
                "machineIdentifier": client_identifier,
            }
            if params:
                query_params.update(params)

            full_url = f"{server_url}?{urllib.parse.urlencode(query_params)}"
            headers = {"X-Plex-Token": self.token}

            logger.debug(f"Fallback server API: {full_url}")
            response = requests.get(full_url, headers=headers, timeout=10)

            if response.status_code in (200, 201, 204):
                logger.info(f"SUCCESS: Command '{command}' sent to {client_name} via server API")
                return True
            logger.error(
                f"FAILED: Command '{command}' failed (Status: {response.status_code}, Response: {response.text[:200]})"
            )
            return False

        except Exception:
            logger.exception("Failed to send command '{command}':")
            return False

    async def stop_playback(self, client_identifier: str) -> bool:
        """Stop playback on a specific client."""
        if not self._initialized:
            await self.connect()
        try:
            return await self._run_in_executor(self._stop_playback_sync, client_identifier)
        except Exception:
            logger.exception("Failed to stop playback:")
            return False

    def _stop_playback_sync(self, client_identifier: str) -> bool:
        """Synchronous helper to stop playback."""
        if not self.server:
            raise RuntimeError("Not connected to Plex server")
        try:
            # Find the client using multi-source discovery
            client = self._find_client_by_id(client_identifier)
            if not client:
                logger.error(f"Client {client_identifier} not found using any discovery method")
                return False
            return self._send_client_command(client, "stop")
        except Exception:
            logger.exception("Error stopping playback:")
            return False

    async def control_playback(
        self,
        client_identifier: str,
        action: str,
        media_key: str | None = None,
        **kwargs,
    ) -> bool:
        """Control playback on a client."""
        if not self._initialized:
            await self.connect()
        try:
            return await self._run_in_executor(
                self._control_playback_sync,
                client_identifier,
                action,
                media_key,
                **kwargs,
            )
        except Exception:
            logger.exception("Failed to control playback:")
            return False

    def _control_playback_sync(
        self,
        client_identifier: str,
        action: str,
        media_key: str | None = None,
        **kwargs,
    ) -> bool:
        """Synchronous helper to control playback."""
        if not self.server:
            raise RuntimeError("Not connected to Plex server")
        try:
            # Find the client using multi-source discovery
            client = self._find_client_by_id(client_identifier)
            if not client:
                logger.error(f"Client {client_identifier} not found using any discovery method")
                return False

            # Map actions to Plex remote control commands
            action_map = {
                "play": "play",
                "pause": "pause",
                "stop": "stop",
                "skip_next": "skipNext",
                "skip_previous": "skipPrevious",
                "step_forward": "stepForward",
                "step_back": "stepBack",
                "seek_to": "seekTo",
                "set_volume": "setVolume",
            }

            if action not in action_map:
                logger.error(f"Unknown action: {action}")
                return False

            command = action_map[action]
            params = {}

            if action == "play" and media_key:
                # Handle direct play with media_key
                # Use standard Plex API format (not server:// URI)
                try:
                    media_item = self.server.fetchItem(int(media_key))
                    media_type = getattr(media_item, "type", "video")
                except Exception:
                    logger.exception("Could not fetch media item {media_key}:")
                    return False

                command = "playMedia"
                params = {
                    "key": f"/library/metadata/{media_key}",
                    "offset": "0",
                    "containerKey": f"/library/metadata/{media_key}",
                    "type": media_type,
                }
            elif action in ("step_forward", "step_back"):
                params["offset"] = kwargs.get("offset", 30000)  # Default 30s in ms
            elif action == "seek_to":
                params["offset"] = kwargs.get("seek_to", 0)
            elif action == "set_volume":
                params["volume"] = kwargs.get("volume", 50)

            return self._send_client_command(client, command, params)
        except Exception:
            logger.exception("Error controlling playback:")
            return False

    async def get_audio_streams(self, media_key: str) -> list[dict[str, Any]]:
        """Get available audio streams for a media item."""
        if not self._initialized:
            await self.connect()
        try:
            item = await self._run_in_executor(self.server.fetchItem, int(media_key))
            streams = []
            # plexapi provides audioStreams() on media items
            for stream in item.audioStreams():
                streams.append(
                    {
                        "id": str(stream.id),
                        "language": getattr(stream, "language", "Unknown"),
                        "language_code": getattr(stream, "languageCode", "unk"),
                        "codec": getattr(stream, "codec", "unknown"),
                        "channels": getattr(stream, "channels", 0),
                        "title": getattr(stream, "displayTitle", getattr(stream, "title", "")),
                        "selected": getattr(stream, "selected", False),
                    }
                )
            return streams
        except Exception:
            logger.exception("Failed to get audio streams for {media_key}:")
            return []

    async def set_audio_stream(self, client_identifier: str, stream_id: str) -> bool:
        """Set the active audio stream on a client."""
        if not self._initialized:
            await self.connect()
        try:
            return await self._run_in_executor(self._set_audio_stream_sync, client_identifier, stream_id)
        except Exception:
            logger.exception("Failed to set audio stream:")
            return False

    def _set_audio_stream_sync(self, client_identifier: str, stream_id: str) -> bool:
        """Synchronous helper to set audio stream."""
        if not self.server:
            raise RuntimeError("Not connected to Plex server")
        try:
            # Find the client using multi-source discovery
            client = self._find_client_by_id(client_identifier)
            if not client:
                logger.error(f"Client {client_identifier} not found using any discovery method")
                return False

            # Plex remote control command for setting streams
            return self._send_client_command(client, "setStreams", {"audioStreamID": stream_id})
        except Exception:
            logger.exception("Error setting audio stream:")
            return False

    async def handover_media(self, source_client_id: str, target_client_id: str) -> bool:
        """Transfer playback from one client to another at the current offset."""
        if not self._initialized:
            await self.connect()
        try:
            return await self._run_in_executor(self._handover_media_sync, source_client_id, target_client_id)
        except Exception:
            logger.exception("Failed to handover media:")
            return False

    def _handover_media_sync(self, source_client_id: str, target_client_id: str) -> bool:
        """Synchronous helper for media handover."""
        if not self.server:
            raise RuntimeError("Not connected to Plex server")
        try:
            # 1. Get source session to find what's playing and where
            sessions = self.server.sessions()
            source_session = next(
                (s for s in sessions if any(p.machineIdentifier == source_client_id for p in s.players)),
                None,
            )

            if not source_session:
                logger.error(f"No active session found for source client {source_client_id}")
                return False

            # 2. Get current offset and media key
            media_key = source_session.ratingKey
            # Find the player in the session to get the offset
            player = next(p for p in source_session.players if p.machineIdentifier == source_client_id)
            offset = getattr(player, "offset", 0)

            # 3. Find target client using multi-source discovery
            target_client = self._find_client_by_id(target_client_id)
            if not target_client:
                logger.error(f"Target client {target_client_id} not found using any discovery method")
                return False

            # 4. Start playback on target at offset
            server_machine_id = self.server.machineIdentifier
            uri = f"server://{server_machine_id}/com.plexapp.plugins.library/library/metadata/{media_key}"

            # Start playing on target
            self._send_client_command(target_client, "playMedia", {"uri": uri, "offset": offset})

            # 5. Stop playback on source using multi-source discovery
            source_client = self._find_client_by_id(source_client_id)
            if source_client:
                self._send_client_command(source_client, "stop")

            return True
        except Exception:
            logger.exception("Error during media handover:")
            return False
