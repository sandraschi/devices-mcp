"""Otoscope camera implementation for USB otoscope devices."""

import logging
from typing import Dict, Optional

from .base import CameraFactory, CameraType
from .webcam import WebCamera

logger = logging.getLogger(__name__)


@CameraFactory.register(CameraType.OTOSCOPE)
class OtoscopeCamera(WebCamera):
    """Otoscope camera implementation, extending WebCamera with otoscope-specific features."""

    def __init__(self, config, mock_webcam=None):
        super().__init__(config, mock_webcam)
        self._light_intensity = int(
            self.config.params.get("light_intensity", 80)
        )  # Default 80% brightness
        self._focus_mode = self.config.params.get("focus_mode", "auto")
        self._specimen_type = self.config.params.get(
            "specimen_type", "ear"
        )  # ear, throat, nose, etc.
        self._magnification = float(self.config.params.get("magnification", 1.0))
        self._calibration_data = self.config.params.get("calibration_data", {})

    async def get_status(self) -> Dict:
        """Get otoscope camera status with detailed medical capabilities."""
        status = await super().get_status()
        status.update(
            {
                "type": CameraType.OTOSCOPE.value,
                "model": status.get("model", "USB Otoscope"),
                "light_intensity": self._light_intensity,
                "focus_mode": self._focus_mode,
                "specimen_type": self._specimen_type,
                "magnification": self._magnification,
                "calibration_data": self._calibration_data,
                "otoscope_capable": True,
                "medical_device": True,
                "ptz_capable": False,  # Otoscopes typically don't have PTZ
                "digital_zoom_capable": True,  # But digital zoom is always available
            }
        )
        return status

    async def set_light_intensity(self, intensity: int) -> None:
        """Set the LED light intensity (0-100)."""
        self._light_intensity = max(0, min(100, intensity))
        logger.info(f"Otoscope {self.config.name}: Set light intensity to {self._light_intensity}%")
        # In a real implementation, this would control the otoscope's LED lighting

    async def set_focus_mode(self, mode: str) -> None:
        """Set the focus mode (auto, manual, fixed)."""
        if mode not in ["auto", "manual", "fixed"]:
            raise ValueError("Invalid focus mode. Must be 'auto', 'manual', or 'fixed'.")
        self._focus_mode = mode
        logger.info(f"Otoscope {self.config.name}: Set focus mode to {self._focus_mode}")

    async def set_specimen_type(self, specimen_type: str) -> None:
        """Set the type of specimen being examined (ear, throat, nose, etc.)."""
        valid_types = ["ear", "throat", "nose", "mouth", "skin", "other"]
        if specimen_type not in valid_types:
            raise ValueError(f"Invalid specimen type. Must be one of: {', '.join(valid_types)}")
        self._specimen_type = specimen_type
        logger.info(f"Otoscope {self.config.name}: Set specimen type to {self._specimen_type}")

    async def set_magnification(self, magnification: float) -> None:
        """Set the digital magnification level."""
        self._magnification = max(1.0, magnification)  # Ensure at least 1x
        logger.info(f"Otoscope {self.config.name}: Set magnification to {self._magnification}x")

    async def calibrate(self, reference_size_mm: float, pixels: float) -> None:
        """Calibrate the otoscope for accurate measurements."""
        if reference_size_mm > 0 and pixels > 0:
            self._calibration_data = {
                "reference_size_mm": reference_size_mm,
                "reference_pixels": pixels,
                "pixels_per_mm": pixels / reference_size_mm,
                "calibrated_at": "current_timestamp",  # Would use actual timestamp
            }
            logger.info(".3f")
        else:
            raise ValueError("Reference size and pixels must be positive for calibration.")

    async def measure_distance(self, pixels: float) -> float:
        """Convert a distance in pixels to real-world millimeters."""
        if not self._calibration_data:
            raise ValueError("Otoscope must be calibrated before measurements can be taken.")

        pixels_per_mm = self._calibration_data.get("pixels_per_mm", 1.0)
        return pixels / pixels_per_mm

    async def measure_area(self, pixels_area: float) -> float:
        """Convert an area in square pixels to real-world square millimeters."""
        if not self._calibration_data:
            raise ValueError("Otoscope must be calibrated before measurements can be taken.")

        pixels_per_mm = self._calibration_data.get("pixels_per_mm", 1.0)
        return pixels_area / (pixels_per_mm**2)

    async def capture_medical_image(self, filename: str, metadata: Optional[Dict] = None) -> str:
        """Capture a medical image with embedded metadata."""
        # This would capture an image and embed medical metadata
        metadata = metadata or {}
        # In a real implementation, medical metadata would be embedded:
        # - device_type: "otoscope"
        # - specimen_type, light_intensity, magnification, calibration_data
        # - timestamp and other metadata

        # In a real implementation, this would save the image with metadata
        logger.info(
            f"Otoscope {self.config.name}: Captured medical image '{filename}' with metadata"
        )
        return f"medical_capture_{filename}"

    async def start_medical_recording(
        self, filename: str, duration_seconds: Optional[int] = None
    ) -> str:
        """Start recording a medical examination video."""
        logger.info(
            f"Otoscope {self.config.name}: Started medical recording '{filename}'"
            f"{' for ' + str(duration_seconds) + 's' if duration_seconds else ''}"
        )

        # In a real implementation, this would start video recording
        return f"medical_recording_{filename}"

    async def stop_medical_recording(self) -> None:
        """Stop the current medical recording."""
        logger.info(f"Otoscope {self.config.name}: Stopped medical recording")

    async def get_medical_presets(self) -> Dict[str, Dict]:
        """Get predefined medical examination presets."""
        return {
            "ear_exam": {
                "specimen_type": "ear",
                "light_intensity": 70,
                "magnification": 2.0,
                "focus_mode": "auto",
            },
            "throat_exam": {
                "specimen_type": "throat",
                "light_intensity": 60,
                "magnification": 1.5,
                "focus_mode": "auto",
            },
            "nose_exam": {
                "specimen_type": "nose",
                "light_intensity": 65,
                "magnification": 1.8,
                "focus_mode": "auto",
            },
            "skin_exam": {
                "specimen_type": "skin",
                "light_intensity": 80,
                "magnification": 3.0,
                "focus_mode": "manual",
            },
        }

    async def apply_medical_preset(self, preset_name: str) -> None:
        """Apply a medical examination preset."""
        presets = await self.get_medical_presets()
        if preset_name not in presets:
            raise ValueError(f"Unknown preset: {preset_name}. Available: {list(presets.keys())}")

        preset = presets[preset_name]
        await self.set_specimen_type(preset["specimen_type"])
        await self.set_light_intensity(preset["light_intensity"])
        await self.set_magnification(preset["magnification"])
        await self.set_focus_mode(preset["focus_mode"])

        logger.info(f"Otoscope {self.config.name}: Applied medical preset '{preset_name}'")
