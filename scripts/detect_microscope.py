"""Detect and configure USB microscopes."""

import logging
import sys

import cv2

logger = logging.getLogger(__name__)


def detect_usb_devices():
    """Detect all available USB camera devices."""
    logger.info("USB Camera Device Detection")
    logger.info("=" * 50)

    devices_found = []

    # Test device IDs from 0 to 9 (typical range)
    for device_id in range(10):
        cap = cv2.VideoCapture(device_id, cv2.CAP_DSHOW)  # Use DirectShow on Windows

        if cap.isOpened():
            # Get device info
            ret, frame = cap.read()
            if ret and frame is not None:
                height, width = frame.shape[:2]

                # Try to get device name (limited info available)
                device_info = {
                    "device_id": device_id,
                    "resolution": f"{width}x{height}",
                    "type": "unknown",
                }

                # Basic heuristics for microscope detection
                if width >= 1280 and height >= 720:  # HD resolution common for microscopes
                    device_info["type"] = "potential_microscope"
                    device_info["suggested_config"] = "microscope"
                else:
                    device_info["type"] = "webcam"
                    device_info["suggested_config"] = "webcam"

                devices_found.append(device_info)

                logger.info(f"[CAMERA] Device {device_id}: {width}x{height} - {device_info['type']}")

            cap.release()
        else:
            logger.info(f"[NOT FOUND] Device {device_id}: Not available")

    logger.info("\n" + "=" * 50)
    logger.info("Configuration Suggestions:")
    logger.info("=" * 50)

    for device in devices_found:
        if device["suggested_config"] == "microscope":
            logger.info(f"""
# USB Microscope Configuration (Device {device["device_id"]})
microscope_{device["device_id"]}:
  type: microscope
  device_id: {device["device_id"]}
  resolution: "{device["resolution"]}"
  fps: 15  # Lower FPS for better quality
  magnification: 50.0  # Starting magnification
  focus_mode: "auto"
  led_brightness: 75
  calibration_factor: 0.01  # Calibrate for accurate measurements
""")
        else:
            logger.info(f"""
# Webcam Configuration (Device {device["device_id"]})
webcam_{device["device_id"]}:
  type: webcam
  device_id: {device["device_id"]}
  resolution: "{device["resolution"]}"
  fps: 30
""")

    return devices_found


def main():
    """Main detection function."""
    logger.info("USB Microscope Detection Tool")
    logger.info("This tool helps you find and configure USB microscopes.")
    logger.info()

    devices = detect_usb_devices()

    if not devices:
        logger.info("\n[ERROR] No camera devices found!")
        logger.info("Make sure your USB microscope is connected and powered on.")
        return 1

    microscopes = [d for d in devices if d["suggested_config"] == "microscope"]
    if microscopes:
        logger.info(f"\n[SUCCESS] Found {len(microscopes)} potential microscope(s)!")
        logger.info("Add the configuration above to your config.yaml file.")
        logger.info("Then restart the Devices MCP server.")
    else:
        logger.info("\n[WARNING] No microscopes detected, but found other cameras.")
        logger.info("Your microscope might use a different device ID or require special drivers.")

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
