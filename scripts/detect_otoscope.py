#!/usr/bin/env python3
"""USB Otoscope Detection and Configuration Tool."""

import logging
import sys
from pathlib import Path

import cv2

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def detect_usb_cameras(max_devices=10):
    """Detect all available USB camera devices."""
    logger.info("USB Camera Device Detection")
    logger.info("=" * 50)
    detected_devices = []
    for i in range(max_devices):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            backend = cap.getBackendName()

            # Try to read a frame to confirm it's a working camera
            ret, _frame = cap.read()
            if ret:
                device_info = {
                    "device_id": i,
                    "resolution": f"{width}x{height}",
                    "backend": backend,
                    "is_working": True,
                }
                detected_devices.append(device_info)
                logger.info(f"[CAMERA] Device {i}: {width}x{height} - {backend} (Working)")
            else:
                logger.info(
                    f"[CAMERA] Device {i}: {width}x{height} - {backend} (Not working, possibly in use or no stream)"
                )
            cap.release()
        else:
            logger.info(f"[NOT FOUND] Device {i}: Not available")
    return detected_devices


def suggest_otoscope_config(detected_devices):
    """Suggests configuration for detected otoscopes."""
    logger.info("\nConfiguration Suggestions:")
    logger.info("=" * 50)

    otoscope_configs = []
    for device in detected_devices:
        # Heuristic: Otoscopes often have specific resolutions or are lower-res cameras
        # This can be refined based on common otoscope characteristics
        if device["is_working"] and device["resolution"] in ["640x480", "800x600", "1024x768"]:
            config_entry = f"""
# USB Otoscope Configuration (Device {device["device_id"]})
otoscope{device["device_id"]}:
  type: otoscope
  device_id: {device["device_id"]}
  resolution: "{device["resolution"]}"
  fps: 30
  light_intensity: 80  # LED brightness (0-100)
  focus_mode: "auto"   # auto, manual, or fixed
  specimen_type: "ear" # ear, throat, nose, mouth, skin, other
  magnification: 1.0   # Digital magnification
  # calibration_data: {{}}  # Will be set during first use
"""
            otoscope_configs.append(config_entry)
            logger.info(config_entry)

    if not otoscope_configs:
        logger.info("No potential otoscope devices detected based on common resolutions.")
        logger.info("Otoscope cameras typically use 640x480 or 800x600 resolution.")
        logger.info("If your otoscope uses a different resolution, you can manually configure it as type: otoscope")


def main():
    """Main detection function."""
    logger.info("USB Otoscope Detection Tool")
    logger.info("This tool helps you find and configure USB otoscope cameras.")
    logger.info()

    detected_devices = detect_usb_cameras()
    suggest_otoscope_config(detected_devices)

    return 0


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n\n[INTERRUPTED] Detection cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.info(f"\n[FATAL ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
