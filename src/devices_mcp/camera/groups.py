"""Camera groups implementation."""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class CameraGroup:
    """Represents a group of cameras."""

    name: str
    camera_names: Set[str] = field(default_factory=set)

    def add_camera(self, camera_name: str) -> bool:
        """Add a camera to the group."""
        if camera_name not in self.camera_names:
            self.camera_names.add(camera_name)
            return True
        return False

    def remove_camera(self, camera_name: str) -> bool:
        """Remove a camera from the group."""
        if camera_name in self.camera_names:
            self.camera_names.remove(camera_name)
            return True
        return False

    def list_cameras(self) -> List[str]:
        """List all cameras in the group."""
        return list(self.camera_names)

    def has_camera(self, camera_name: str) -> bool:
        """Check if a camera is in the group."""
        return camera_name in self.camera_names


class CameraGroupManager:
    """Manages camera groups."""

    def __init__(self):
        self._groups: Dict[str, CameraGroup] = {}
        self._camera_groups: Dict[str, Set[str]] = {}

    def create_group(self, group_name: str) -> bool:
        """Create a new camera group."""
        if group_name in self._groups:
            logger.warning(f"Group {group_name} already exists")
            return False

        self._groups[group_name] = CameraGroup(group_name)
        return True

    def delete_group(self, group_name: str) -> bool:
        """Delete a camera group."""
        if group_name not in self._groups:
            logger.warning(f"Group {group_name} does not exist")
            return False

        # Remove group from camera indexes
        for camera_name in self._groups[group_name].camera_names:
            if camera_name in self._camera_groups:
                self._camera_groups[camera_name].discard(group_name)
                if not self._camera_groups[camera_name]:
                    del self._camera_groups[camera_name]

        # Remove the group
        del self._groups[group_name]
        return True

    def add_camera_to_group(self, camera_name: str, group_name: str) -> bool:
        """Add a camera to a group."""
        if group_name not in self._groups:
            self.create_group(group_name)

        # Add to group
        if self._groups[group_name].add_camera(camera_name):
            # Update camera index
            if camera_name not in self._camera_groups:
                self._camera_groups[camera_name] = set()
            self._camera_groups[camera_name].add(group_name)
            return True

        return False

    def remove_camera_from_group(self, camera_name: str, group_name: str) -> bool:
        """Remove a camera from a group."""
        if group_name not in self._groups:
            logger.warning(f"Group {group_name} does not exist")
            return False

        # Remove from group
        if self._groups[group_name].remove_camera(camera_name):
            # Update camera index
            if camera_name in self._camera_groups:
                self._camera_groups[camera_name].discard(group_name)
                if not self._camera_groups[camera_name]:
                    del self._camera_groups[camera_name]
            return True

        return False

    def get_camera_groups(self, camera_name: str) -> List[str]:
        """Get all groups a camera belongs to."""
        return list(self._camera_groups.get(camera_name, set()))

    def get_group_cameras(self, group_name: str) -> List[str]:
        """Get all cameras in a group."""
        if group_name not in self._groups:
            return []
        return self._groups[group_name].list_cameras()

    def list_groups(self) -> List[str]:
        """List all group names."""
        return list(self._groups.keys())

    def remove_camera(self, camera_name: str) -> None:
        """Remove a camera from all groups."""
        if camera_name in self._camera_groups:
            groups = list(self._camera_groups[camera_name])
            for group_name in groups:
                self.remove_camera_from_group(camera_name, group_name)

    def get_group(self, group_name: str) -> Optional[CameraGroup]:
        """Get a group by name."""
        return self._groups.get(group_name)

    def group_exists(self, group_name: str) -> bool:
        """Check if a group exists."""
        return group_name in self._groups
