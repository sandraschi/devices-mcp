"""Digital camera implementation for repurposed digicams as webcams."""

import logging
from typing import Dict, Optional

from .base import CameraFactory, CameraType
from .webcam import Webcam

logger = logging.getLogger(__name__)


@CameraFactory.register(CameraType.DIGICAM)
class DigicamCamera(Webcam):
    """Digital camera implementation for old digicams repurposed as webcams."""

    def __init__(self, config, mock_webcam=None):
        super().__init__(config, mock_webcam)
        self._camera_model = self.config.params.get("camera_model", "Unknown Digicam")
        self._connection_type = self.config.params.get("connection_type", "usb")  # usb, hdmi, wifi
        self._driver_software = self.config.params.get(
            "driver_software", "generic"
        )  # generic, canon, nikon, sony, etc.
        self._original_megapixels = self.config.params.get("original_megapixels", 0)
        self._has_optical_zoom = self.config.params.get("has_optical_zoom", False)
        self._max_optical_zoom = self.config.params.get("max_optical_zoom", 1.0)

        # Digicam-specific settings
        self._focus_mode = self.config.params.get("focus_mode", "auto")
        self._image_stabilization = self.config.params.get("image_stabilization", False)
        self._night_mode = self.config.params.get("night_mode", False)

    async def get_status(self) -> Dict:
        """Get digicam status with camera-specific capabilities."""
        status = await super().get_status()
        status.update(
            {
                "type": CameraType.DIGICAM.value,
                "model": self._camera_model,
                "connection_type": self._connection_type,
                "driver_software": self._driver_software,
                "original_megapixels": self._original_megapixels,
                "has_optical_zoom": self._has_optical_zoom,
                "max_optical_zoom": self._max_optical_zoom,
                "focus_mode": self._focus_mode,
                "image_stabilization": self._image_stabilization,
                "night_mode": self._night_mode,
                "digicam_capable": True,
                "ptz_capable": False,  # Most digicams don't have PTZ
                "digital_zoom_capable": True,  # Digital zoom always available
                "optical_zoom_capable": self._has_optical_zoom,
            }
        )
        return status

    async def set_camera_settings(
        self,
        focus_mode: Optional[str] = None,
        image_stabilization: Optional[bool] = None,
        night_mode: Optional[bool] = None,
    ) -> None:
        """Set digicam-specific camera settings."""
        if focus_mode in ["auto", "manual", "macro", "infinity"]:
            self._focus_mode = focus_mode
        if image_stabilization is not None:
            self._image_stabilization = image_stabilization
        if night_mode is not None:
            self._night_mode = night_mode

        logger.info(
            f"Digicam {self.config.name}: Settings updated - Focus: {self._focus_mode}, "
            f"IS: {self._image_stabilization}, Night: {self._night_mode}"
        )

    async def optical_zoom(self, zoom_level: float) -> None:
        """Control optical zoom if available."""
        if not self._has_optical_zoom:
            raise ValueError("This digicam does not have optical zoom capability")

        zoom_level = max(1.0, min(self._max_optical_zoom, zoom_level))
        logger.info(f"Digicam {self.config.name}: Optical zoom set to {zoom_level}x")

        # In a real implementation, this would control the camera's optical zoom
        # This might require camera-specific drivers or APIs

    async def toggle_night_mode(self) -> None:
        """Toggle night vision/low light mode."""
        self._night_mode = not self._night_mode
        logger.info(
            f"Digicam {self.config.name}: Night mode {'enabled' if self._night_mode else 'disabled'}"
        )

    async def get_camera_info(self) -> Dict:
        """Get detailed information about the digicam."""
        return {
            "model": self._camera_model,
            "original_megapixels": self._original_megapixels,
            "connection_type": self._connection_type,
            "driver_software": self._driver_software,
            "capabilities": {
                "optical_zoom": self._has_optical_zoom,
                "max_optical_zoom": self._max_optical_zoom,
                "focus_modes": ["auto", "manual", "macro", "infinity"],
                "image_stabilization": True,
                "night_mode": True,
            },
            "current_settings": {
                "focus_mode": self._focus_mode,
                "image_stabilization": self._image_stabilization,
                "night_mode": self._night_mode,
            },
        }

    async def test_camera_connection(self) -> Dict:
        """Test the digicam connection and capabilities."""
        try:
            # Test basic webcam functionality
            status = await self.get_status()

            # Additional digicam-specific tests
            connection_test = {
                "webcam_functionality": status.get("connected", False),
                "resolution_supported": status.get("resolution") is not None,
                "driver_working": status.get("status") == "online",
                "camera_model": self._camera_model,
                "connection_type": self._connection_type,
                "estimated_setup_difficulty": self._estimate_setup_difficulty(),
            }

            return {
                "success": True,
                "connection_test": connection_test,
                "recommendations": self._get_setup_recommendations(),
            }

        except Exception as e:
            logger.exception(f"Digicam {self.config.name}: Connection test failed")
            return {
                "success": False,
                "error": str(e),
                "troubleshooting": self._get_troubleshooting_steps(),
            }

    def _estimate_setup_difficulty(self) -> str:
        """Estimate setup difficulty based on camera model and connection type."""
        difficulty_map = {
            ("canon", "usb"): "easy",
            ("nikon", "usb"): "easy",
            ("sony", "usb"): "medium",
            ("pentax", "usb"): "hard",
            ("olympus", "usb"): "hard",
            ("fuji", "usb"): "medium",
            ("generic", "usb"): "medium",
            ("any", "hdmi"): "hard",
            ("any", "wifi"): "easy",
        }

        brand = self._driver_software.lower()
        conn = self._connection_type.lower()

        # Try specific brand match first
        if (brand, conn) in difficulty_map:
            return difficulty_map[(brand, conn)]

        # Try connection type fallback
        if ("any", conn) in difficulty_map:
            return difficulty_map[("any", conn)]

        return "unknown"

    def _get_setup_recommendations(self) -> list:
        """Get setup recommendations based on camera and connection type."""
        recommendations = []

        if self._connection_type == "usb":
            recommendations.extend(
                [
                    "Install manufacturer webcam drivers if available",
                    "Try generic webcam drivers as fallback",
                    "Check camera's USB mode/settings menu",
                    "Ensure camera battery is charged",
                ]
            )

            if self._driver_software == "canon":
                recommendations.append("Use Canon EOS Webcam Utility for DSLR cameras")
            elif self._driver_software == "nikon":
                recommendations.append("Use Nikon Webcam Utility for DSLR cameras")
            elif self._driver_software == "sony":
                recommendations.append("Use Imaging Edge Webcam for Sony cameras")

        elif self._connection_type == "hdmi":
            recommendations.extend(
                [
                    "Use HDMI capture device (Elgato Cam Link, etc.)",
                    "Set camera to HDMI output mode",
                    "Ensure HDMI resolution matches capture device",
                    "Check for HDCP compatibility issues",
                ]
            )

        elif self._connection_type == "wifi":
            recommendations.extend(
                [
                    "Connect camera to same WiFi network",
                    "Use camera's wireless streaming feature",
                    "Check camera's network settings",
                    "Ensure firewall allows camera connections",
                ]
            )

        return recommendations

    def _get_troubleshooting_steps(self) -> list:
        """Get troubleshooting steps for connection issues."""
        return [
            "Check USB cable and connections",
            "Try different USB ports on computer",
            "Ensure camera is in correct mode (PC/Webcam)",
            "Update camera firmware if possible",
            "Try different driver software",
            "Check device manager for driver conflicts",
            "Test camera on another computer",
            "Verify camera battery level",
            "Check camera's manual for webcam mode instructions",
        ]
