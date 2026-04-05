"""iPhone camera implementation for repurposed iPhones as webcams."""

import logging
from typing import Dict, Optional

from .base import CameraFactory, CameraType
from .webcam import Webcam

logger = logging.getLogger(__name__)


@CameraFactory.register(CameraType.IPHONE)
class IPhoneCamera(Webcam):
    """iPhone camera implementation for old iPhones repurposed as webcams."""

    def __init__(self, config, mock_webcam=None):
        super().__init__(config, mock_webcam)
        self._iphone_model = self.config.params.get("iphone_model", "Unknown iPhone")
        self._ios_version = self.config.params.get("ios_version", "Unknown")
        self._connection_method = self.config.params.get(
            "connection_method", "wifi"
        )  # wifi, usb, continuity
        self._webcam_app = self.config.params.get(
            "webcam_app", "continuity"
        )  # continuity, epoccam, manycam, etc.
        self._camera_lens = self.config.params.get(
            "camera_lens", "wide"
        )  # wide, ultra_wide, telephoto

        # iPhone-specific settings
        self._hdr_mode = self.config.params.get("hdr_mode", False)
        self._portrait_mode = self.config.params.get("portrait_mode", False)
        self._live_photos = self.config.params.get("live_photos", False)
        self._stabilization = self.config.params.get("stabilization", True)

    async def get_status(self) -> Dict:
        """Get iPhone camera status with device-specific capabilities."""
        status = await super().get_status()
        status.update(
            {
                "type": CameraType.IPHONE.value,
                "model": self._iphone_model,
                "ios_version": self._ios_version,
                "connection_method": self._connection_method,
                "webcam_app": self._webcam_app,
                "camera_lens": self._camera_lens,
                "hdr_mode": self._hdr_mode,
                "portrait_mode": self._portrait_mode,
                "live_photos": self._live_photos,
                "stabilization": self._stabilization,
                "iphone_capable": True,
                "ptz_capable": False,  # iPhones don't have PTZ
                "digital_zoom_capable": True,  # Digital zoom always available
                "optical_zoom_capable": self._camera_lens
                == "telephoto",  # Only telephoto lens has optical zoom
            }
        )
        return status

    async def set_camera_mode(
        self,
        hdr: Optional[bool] = None,
        portrait: Optional[bool] = None,
        live_photos: Optional[bool] = None,
        stabilization: Optional[bool] = None,
    ) -> None:
        """Set iPhone camera modes."""
        if hdr is not None:
            self._hdr_mode = hdr
        if portrait is not None:
            self._portrait_mode = portrait
        if live_photos is not None:
            self._live_photos = live_photos
        if stabilization is not None:
            self._stabilization = stabilization

        logger.info(
            f"iPhone {self.config.name}: Camera modes updated - HDR: {self._hdr_mode}, "
            f"Portrait: {self._portrait_mode}, Live: {self._live_photos}, "
            f"Stabilization: {self._stabilization}"
        )

    async def switch_camera_lens(self, lens: str) -> None:
        """Switch between iPhone camera lenses."""
        valid_lenses = ["wide", "ultra_wide", "telephoto"]
        if lens not in valid_lenses:
            raise ValueError(f"Invalid lens. Must be one of: {', '.join(valid_lenses)}")

        # Check if the iPhone model supports the requested lens
        supported_lenses = self._get_supported_lenses()
        if lens not in supported_lenses:
            raise ValueError(f"iPhone {self._iphone_model} does not support {lens} lens")

        self._camera_lens = lens
        logger.info(f"iPhone {self.config.name}: Switched to {lens} lens")

    async def _get_supported_lenses(self) -> list:
        """Get lenses supported by this iPhone model."""
        # This is a simplified mapping - real implementation would be more comprehensive
        lens_support = {
            "iPhone 11": ["wide", "ultra_wide"],
            "iPhone 11 Pro": ["wide", "ultra_wide", "telephoto"],
            "iPhone 11 Pro Max": ["wide", "ultra_wide", "telephoto"],
            "iPhone 12": ["wide", "ultra_wide"],
            "iPhone 12 Pro": ["wide", "ultra_wide", "telephoto"],
            "iPhone 12 Pro Max": ["wide", "ultra_wide", "telephoto"],
            "iPhone 13": ["wide", "ultra_wide"],
            "iPhone 13 Pro": ["wide", "ultra_wide", "telephoto"],
            "iPhone 13 Pro Max": ["wide", "ultra_wide", "telephoto"],
            "iPhone 14": ["wide", "ultra_wide"],
            "iPhone 14 Pro": ["wide", "ultra_wide", "telephoto"],
            "iPhone 14 Pro Max": ["wide", "ultra_wide", "telephoto"],
        }

        # Default to wide and ultra_wide for unknown models
        return lens_support.get(self._iphone_model, ["wide", "ultra_wide"])

    async def take_live_photo(self) -> str:
        """Take a Live Photo (if enabled)."""
        if not self._live_photos:
            raise ValueError("Live Photos are not enabled for this camera")

        # In a real implementation, this would trigger a Live Photo capture
        logger.info(f"iPhone {self.config.name}: Live Photo captured")
        return f"live_photo_{self.config.name}"

    async def enable_portrait_mode(self) -> None:
        """Enable portrait mode with depth effect."""
        await self.set_camera_mode(portrait=True)
        logger.info(f"iPhone {self.config.name}: Portrait mode enabled")

    async def enable_hdr_mode(self) -> None:
        """Enable HDR (High Dynamic Range) mode."""
        await self.set_camera_mode(hdr=True)
        logger.info(f"iPhone {self.config.name}: HDR mode enabled")

    async def get_iphone_info(self) -> Dict:
        """Get detailed information about the iPhone."""
        return {
            "model": self._iphone_model,
            "ios_version": self._ios_version,
            "connection_method": self._connection_method,
            "webcam_app": self._webcam_app,
            "supported_lenses": await self._get_supported_lenses(),
            "camera_capabilities": {
                "hdr": True,
                "portrait_mode": True,
                "live_photos": True,
                "cinematic_mode": self._ios_version >= "13.0",  # iOS 13+
                "stabilization": True,
                "night_mode": self._ios_version >= "13.0",
                "deep_fusion": self._ios_version >= "15.1",
            },
            "current_settings": {
                "camera_lens": self._camera_lens,
                "hdr_mode": self._hdr_mode,
                "portrait_mode": self._portrait_mode,
                "live_photos": self._live_photos,
                "stabilization": self._stabilization,
            },
        }

    async def test_iphone_connection(self) -> Dict:
        """Test the iPhone connection and capabilities."""
        try:
            status = await self.get_status()
            iphone_info = await self.get_iphone_info()

            connection_test = {
                "webcam_functionality": status.get("connected", False),
                "resolution_supported": status.get("resolution") is not None,
                "app_connection": status.get("status") == "online",
                "iphone_model": self._iphone_model,
                "ios_version": self._ios_version,
                "connection_method": self._connection_method,
                "webcam_app": self._webcam_app,
                "supported_features": iphone_info["camera_capabilities"],
                "setup_difficulty": self._estimate_setup_difficulty(),
            }

            return {
                "success": True,
                "connection_test": connection_test,
                "recommendations": self._get_setup_recommendations(),
                "troubleshooting": self._get_troubleshooting_steps(),
            }

        except Exception as e:
            logger.exception(f"iPhone {self.config.name}: Connection test failed")
            return {
                "success": False,
                "error": str(e),
                "troubleshooting": self._get_troubleshooting_steps(),
            }

    def _estimate_setup_difficulty(self) -> str:
        """Estimate setup difficulty based on iPhone model and connection method."""
        if self._connection_method == "continuity":
            # macOS Continuity Camera - easiest
            return "easy"
        if self._connection_method == "wifi" and self._webcam_app in ["epoccam", "manycam"]:
            # Wireless apps - still easy
            return "easy"
        if self._connection_method == "usb":
            # USB connection - medium difficulty
            return "medium"
        return "unknown"

    def _get_setup_recommendations(self) -> list:
        """Get setup recommendations based on connection method and app."""
        recommendations = []

        if self._connection_method == "continuity":
            recommendations.extend(
                [
                    "Ensure iPhone and Mac are on same WiFi network",
                    "Sign into same iCloud account on both devices",
                    "Enable Handoff in System Settings > General",
                    "Bluetooth must be enabled on both devices",
                    "Keep devices within Bluetooth range initially",
                ]
            )

        elif self._webcam_app == "epoccam":
            recommendations.extend(
                [
                    "Download EpocCam app on iPhone from App Store",
                    "Download EpocCam drivers on computer",
                    "Connect iPhone and computer to same WiFi network",
                    "Launch EpocCam app on iPhone and select computer",
                    "Ensure firewall allows EpocCam connections",
                ]
            )

        elif self._webcam_app == "manycam":
            recommendations.extend(
                [
                    "Download ManyCam app on iPhone from App Store",
                    "Download ManyCam software on computer",
                    "Connect both devices to same network",
                    "Configure ManyCam virtual webcam in your applications",
                ]
            )

        elif self._connection_method == "usb":
            recommendations.extend(
                [
                    "Connect iPhone to computer with Lightning/USB-C cable",
                    "Trust computer when prompted on iPhone",
                    "Ensure iOS is updated to latest version",
                    "Check that webcam app supports USB mode",
                ]
            )

        # Add general iPhone recommendations
        recommendations.extend(
            [
                "Ensure iPhone battery is sufficiently charged",
                "Close other camera-using apps on iPhone",
                "Grant camera permissions to webcam app",
                "Keep iPhone screen on during use (Settings > Display & Brightness > Auto-Lock)",
            ]
        )

        return recommendations

    def _get_troubleshooting_steps(self) -> list:
        """Get troubleshooting steps for iPhone connection issues."""
        return [
            "Restart both iPhone and computer",
            "Check WiFi connection stability",
            "Ensure webcam app is updated to latest version",
            "Try different webcam app (EpocCam, ManyCam, Continuity)",
            "Check iPhone storage space (keep at least 1GB free)",
            "Disable VPN if using WiFi connection",
            "Reset network settings on iPhone if needed",
            "Try USB connection as fallback",
            "Check iOS version compatibility",
            "Ensure no other apps are using camera",
        ]
