"""
PTZ Data Models

Defines the data structures used for PTZ (Pan-Tilt-Zoom) camera control.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class PTZMoveDirection(str, Enum):
    """Enumeration of possible PTZ movement directions"""

    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    UP_LEFT = "up_left"
    UP_RIGHT = "up_right"
    DOWN_LEFT = "down_left"
    DOWN_RIGHT = "down_right"
    STOP = "stop"


class PTZSpeed(str, Enum):
    """Enumeration of PTZ movement speeds"""

    SLOW = "slow"
    MEDIUM = "medium"
    FAST = "fast"


@dataclass
class PTZPosition:
    """Represents a PTZ position with pan, tilt, and zoom values"""

    pan: float  # -1.0 (left) to 1.0 (right)
    tilt: float  # -1.0 (down) to 1.0 (up)
    zoom: float  # 0.0 (wide) to 1.0 (tele)

    def to_dict(self) -> Dict[str, float]:
        """Convert position to dictionary"""
        return {"pan": self.pan, "tilt": self.tilt, "zoom": self.zoom}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PTZPosition":
        """Create PTZPosition from dictionary"""
        return cls(
            pan=float(data.get("pan", 0)),
            tilt=float(data.get("tilt", 0)),
            zoom=float(data.get("zoom", 0)),
        )


@dataclass
class PTZStatus:
    """Current status of PTZ camera"""

    position: PTZPosition
    is_moving: bool
    last_movement: Optional[float] = None  # Timestamp of last movement
    current_preset: Optional[int] = None  # ID of current preset, if any

    def to_dict(self) -> Dict[str, Any]:
        """Convert status to dictionary"""
        return {
            "position": self.position.to_dict(),
            "is_moving": self.is_moving,
            "last_movement": self.last_movement,
            "current_preset": self.current_preset,
        }


@dataclass
class PTZPresetInfo:
    """Information about a saved PTZ preset"""

    preset_id: int
    name: str
    position: PTZPosition
    created_at: float  # Timestamp
    updated_at: float  # Timestamp
    thumbnail_url: Optional[str] = None
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert preset info to dictionary"""
        return {
            "preset_id": self.preset_id,
            "name": self.name,
            "position": self.position.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "thumbnail_url": self.thumbnail_url,
            "description": self.description,
        }


@dataclass
class PTZLimits:
    """Physical limits of PTZ camera movement"""

    min_pan: float = -1.0
    max_pan: float = 1.0
    min_tilt: float = -1.0
    max_tilt: float = 1.0
    min_zoom: float = 0.0
    max_zoom: float = 1.0

    def to_dict(self) -> Dict[str, float]:
        """Convert limits to dictionary"""
        return {
            "min_pan": self.min_pan,
            "max_pan": self.max_pan,
            "min_tilt": self.min_tilt,
            "max_tilt": self.max_tilt,
            "min_zoom": self.min_zoom,
            "max_zoom": self.max_zoom,
        }


class PTZCommandType(str, Enum):
    """Types of PTZ commands"""

    MOVE = "move"
    STOP = "stop"
    ZOOM = "zoom"
    RECALL_PRESET = "recall_preset"
    SAVE_PRESET = "save_preset"
    DELETE_PRESET = "delete_preset"


@dataclass
class PTZCommand:
    """A command to control PTZ camera"""

    command_type: PTZCommandType
    camera_id: str
    timestamp: float

    # Command parameters (optional, depends on command_type)
    direction: Optional[PTZMoveDirection] = None
    speed: Optional[PTZSpeed] = PTZSpeed.MEDIUM
    duration_ms: Optional[int] = 1000
    preset_id: Optional[int] = None
    preset_name: Optional[str] = None
    position: Optional[PTZPosition] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert command to dictionary"""
        result = {
            "command_type": self.command_type.value,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "speed": self.speed.value if self.speed else None,
        }

        if self.direction:
            result["direction"] = self.direction.value
        if self.duration_ms is not None:
            result["duration_ms"] = self.duration_ms
        if self.preset_id is not None:
            result["preset_id"] = self.preset_id
        if self.preset_name is not None:
            result["preset_name"] = self.preset_name
        if self.position is not None:
            result["position"] = self.position.to_dict()

        return result
