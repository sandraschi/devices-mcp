"""Custom PTZ Preset Manager for storing favorite positions."""

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CustomPTZPreset:
    """Custom PTZ preset position data."""

    name: str
    camera_name: str
    pan: float
    tilt: float
    zoom: float = 0.0
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CustomPTZPreset":
        return cls(**data)


class CustomPTZPresetManager:
    """Manages custom PTZ presets for cameras."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.presets_file = self.data_dir / "custom_ptz_presets.json"
        self._presets: Dict[
            str, Dict[str, CustomPTZPreset]
        ] = {}  # camera_name -> {preset_name -> preset}
        self._load_presets()

    def _load_presets(self):
        """Load presets from file."""
        if self.presets_file.exists():
            try:
                with open(self.presets_file, encoding="utf-8") as f:
                    data = json.load(f)
                    for camera_name, presets_data in data.items():
                        self._presets[camera_name] = {}
                        for preset_name, preset_data in presets_data.items():
                            self._presets[camera_name][preset_name] = CustomPTZPreset.from_dict(
                                preset_data
                            )
                logger.info(f"Loaded custom PTZ presets for {len(self._presets)} cameras")
            except Exception:
                logger.exception("Failed to load custom PTZ presets:")
                self._presets = {}

    def _save_presets(self):
        """Save presets to file."""
        try:
            data = {}
            for camera_name, presets in self._presets.items():
                data[camera_name] = {}
                for preset_name, preset in presets.items():
                    data[camera_name][preset_name] = preset.to_dict()

            with open(self.presets_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Saved custom PTZ presets")
        except Exception:
            logger.exception("Failed to save custom PTZ presets:")

    def save_preset(
        self,
        camera_name: str,
        preset_name: str,
        pan: float,
        tilt: float,
        zoom: float = 0.0,
        description: str = "",
    ) -> bool:
        """Save a PTZ preset position."""
        try:
            if camera_name not in self._presets:
                self._presets[camera_name] = {}

            preset = CustomPTZPreset(
                name=preset_name,
                camera_name=camera_name,
                pan=pan,
                tilt=tilt,
                zoom=zoom,
                description=description,
            )

            self._presets[camera_name][preset_name] = preset
            self._save_presets()
            logger.info(f"Saved custom PTZ preset '{preset_name}' for camera '{camera_name}'")
            return True
        except Exception:
            logger.exception("Failed to save custom PTZ preset:")
            return False

    def get_preset(self, camera_name: str, preset_name: str) -> Optional[CustomPTZPreset]:
        """Get a specific preset."""
        return self._presets.get(camera_name, {}).get(preset_name)

    def get_camera_presets(self, camera_name: str) -> List[CustomPTZPreset]:
        """Get all presets for a camera."""
        return list(self._presets.get(camera_name, {}).values())

    def get_all_presets(self) -> Dict[str, List[CustomPTZPreset]]:
        """Get all presets organized by camera."""
        return {camera: list(presets.values()) for camera, presets in self._presets.items()}

    def delete_preset(self, camera_name: str, preset_name: str) -> bool:
        """Delete a preset."""
        try:
            if camera_name in self._presets and preset_name in self._presets[camera_name]:
                del self._presets[camera_name][preset_name]
                # Remove camera entry if no presets left
                if not self._presets[camera_name]:
                    del self._presets[camera_name]
                self._save_presets()
                logger.info(f"Deleted custom PTZ preset '{preset_name}' for camera '{camera_name}'")
                return True
            return False
        except Exception:
            logger.exception("Failed to delete custom PTZ preset:")
            return False

    def rename_preset(self, camera_name: str, old_name: str, new_name: str) -> bool:
        """Rename a preset."""
        try:
            if camera_name in self._presets and old_name in self._presets[camera_name]:
                preset = self._presets[camera_name][old_name]
                preset.name = new_name
                del self._presets[camera_name][old_name]
                self._presets[camera_name][new_name] = preset
                self._save_presets()
                logger.info(
                    f"Renamed custom PTZ preset '{old_name}' to '{new_name}' for camera '{camera_name}'"
                )
                return True
            return False
        except Exception:
            logger.exception("Failed to rename custom PTZ preset:")
            return False


# Global preset manager instance
_preset_manager = None


def get_custom_preset_manager() -> CustomPTZPresetManager:
    """Get the global custom preset manager instance."""
    global _preset_manager
    if _preset_manager is None:
        _preset_manager = CustomPTZPresetManager()
    return _preset_manager
