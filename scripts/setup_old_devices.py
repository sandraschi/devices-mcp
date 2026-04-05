import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Setup Guide for Old Digicams and iPhones as Webcams
==================================================

This script provides step-by-step guidance for setting up old digital cameras
and iPhones as webcams in your Devices MCP system.
"""

import os


def print_header(title):
    """Print a formatted header."""
    logger.info(f"\n{'=' * 60}")
    logger.info(f"SETUP: {title}")
    logger.info(f"{'=' * 60}")


def print_section(title):
    """Print a section header."""
    logger.info(f"\n{title}")
    logger.info("-" * 40)


def setup_digicam_guide():
    """Guide for setting up digital cameras."""
    print_header("DIGITAL CAMERA (DIGICAM) SETUP GUIDE")

    logger.info("""
OVERVIEW
Old digital cameras (Canon, Nikon, Sony, etc.) can be repurposed as webcams
with better image quality than built-in laptop cameras.

REQUIREMENTS
- Digital camera with USB port or HDMI output
- Computer with USB ports or HDMI capture device
- Camera manufacturer's webcam software (recommended) OR generic drivers

SETUP METHODS
""")

    print_section("METHOD 1: USB Webcam Mode (Easiest)")
    logger.info("""
1. Check if your camera supports USB webcam mode:
   - Canon EOS: Use "EOS Webcam Utility Pro"
   - Nikon DSLR: Use "Nikon Webcam Utility"
   - Sony Alpha: Use "Imaging Edge Webcam"
   - Olympus/Pentax: May require third-party software

2. Download and install manufacturer software:
   - Canon: https://www.canon-europe.com/support/consumer_products/software/eos-webcam-utility-pro/
   - Nikon: https://downloadcenter.nikonimglib.com/en/products/184/Nikon_Webcam_Utility.html
   - Sony: https://www.sony.com/electronics/support/series/IMAGINGEDGE

3. Connect camera via USB and enable webcam mode
4. Run device detection: python scripts/detect_usb_devices.py
5. Add to config.yaml (see example below)
""")

    print_section("METHOD 2: HDMI Capture Device")
    logger.info("""
1. Get HDMI capture device:
   - Elgato Cam Link 4K ($120)
   - AVerMedia Live Gamer Portable 2 Plus ($100)
   - Razer Ripsaw HD ($100)

2. Connect camera HDMI output to capture device
3. Connect capture device to computer USB
4. Set camera to HDMI output mode
5. Run device detection script
""")

    print_section("DIGICAM CONFIGURATION EXAMPLE")
    logger.info("""
# Add to your config.yaml
cameras:
  canon_rebel:
    type: digicam
    device_id: 3                    # From device detection
    resolution: "1920x1080"         # Camera's native resolution
    fps: 30
    camera_model: "Canon EOS Rebel T7i"
    connection_type: "usb"          # usb, hdmi, wifi
    driver_software: "canon"        # canon, nikon, sony, generic
    original_megapixels: 24         # Camera's MP rating
    has_optical_zoom: true          # true if zoom lens
    max_optical_zoom: 8.0           # Max zoom level
    focus_mode: "auto"              # auto, manual, macro, infinity
    image_stabilization: true
    night_mode: false

# Restart server after configuration
""")


def setup_iphone_guide():
    """Guide for setting up iPhones as webcams."""
    print_header("IPHONE WEBCAM SETUP GUIDE")

    logger.info("""
OVERVIEW
Old iPhones make excellent webcams with superior image quality,
multiple lenses, and computational photography features.

REQUIREMENTS
- iPhone (iPhone 8 or newer recommended)
- iOS 13.0 or later
- Same WiFi network as computer
- Webcam app (Continuity, EpocCam, or ManyCam)

SETUP METHODS
""")

    print_section("METHOD 1: Continuity Camera (macOS - Easiest)")
    logger.info("""
1. Ensure macOS Monterey 12.0 or later
2. Connect iPhone and Mac to same WiFi network
3. Sign into same iCloud account on both devices
4. Enable Bluetooth and Handoff on both devices:
   - System Settings > General > AirDrop & Handoff > Transfer to Mac
5. On iPhone: Settings > General > AirPlay & Handoff > Continuity Camera
6. Run device detection: python scripts/detect_usb_devices.py
""")

    print_section("METHOD 2: EpocCam (Cross-Platform)")
    logger.info("""
1. Download EpocCam app on iPhone:
   - https://www.elgato.com/en/epoccam
2. Download EpocCam drivers on computer:
   - Windows: https://www.elgato.com/en/epoccam
   - macOS: Same app
3. Connect both devices to same WiFi network
4. Launch EpocCam app on iPhone
5. Select your computer from the app
6. Run device detection script
""")

    print_section("METHOD 3: ManyCam (Advanced Features)")
    logger.info("""
1. Download ManyCam on iPhone and computer:
   - https://manycam.com/
2. Connect devices to same network
3. Configure virtual webcam in ManyCam software
4. Select iPhone as video source
5. Run device detection script
""")

    print_section("IPHONE CONFIGURATION EXAMPLE")
    logger.info("""
# Add to your config.yaml
cameras:
  old_iphone_12:
    type: iphone
    device_id: 4                    # From device detection
    resolution: "1920x1080"         # iPhone camera resolution
    fps: 30
    iphone_model: "iPhone 12 Pro"   # Your model
    ios_version: "16.5"             # iOS version
    connection_method: "wifi"       # wifi, usb, continuity
    webcam_app: "continuity"        # continuity, epoccam, manycam
    camera_lens: "wide"             # wide, ultra_wide, telephoto
    hdr_mode: true                  # Enable HDR
    portrait_mode: false
    live_photos: false
    stabilization: true

# Restart server after configuration
""")


def troubleshooting_guide():
    """Common troubleshooting steps."""
    print_header("TROUBLESHOOTING GUIDE")

    print_section("DIGICAM ISSUES")
    logger.info("""
Camera not detected:
- Try different USB ports
- Update camera firmware
- Use manufacturer software instead of generic drivers
- Check USB cable and camera battery

Poor video quality:
- Set camera to highest resolution in webcam mode
- Adjust camera settings (ISO, shutter speed)
- Ensure good lighting
- Clean camera lens

Connection drops:
- Use powered USB hub
- Avoid USB extension cables
- Update camera drivers
- Check for USB power management issues
""")

    print_section("IPHONE ISSUES")
    logger.info("""
Continuity not working:
- Ensure same WiFi network
- Enable Bluetooth and Handoff
- Sign into same iCloud account
- Keep devices within Bluetooth range initially

EpocCam connection fails:
- Check firewall settings
- Ensure both devices on same network
- Restart EpocCam app on iPhone
- Update to latest app versions

Poor video quality:
- Close other apps on iPhone
- Ensure iPhone battery > 20%
- Keep iPhone screen on
- Good WiFi signal strength
""")


def main():
    """Main setup guide."""
    logger.info("OLD DEVICE WEBCAM SETUP GUIDE")
    logger.info("=" * 60)
    logger.info("Transform your old digital cameras and iPhones into high-quality webcams!")

    # Show menu
    while True:
        logger.info("\nSETUP OPTIONS:")
        logger.info("1. Digital Camera (Digicam) Setup Guide")
        logger.info("2. iPhone Webcam Setup Guide")
        logger.info("3. Troubleshooting Guide")
        logger.info("4. Run Device Detection")
        logger.info("5. Exit")

        choice = input("\nSelect option (1-5): ").strip()

        if choice == "1":
            setup_digicam_guide()
        elif choice == "2":
            setup_iphone_guide()
        elif choice == "3":
            troubleshooting_guide()
        elif choice == "4":
            logger.info("\nRunning device detection...")
            os.system("python scripts/detect_usb_devices.py")
        elif choice == "5":
            logger.info("\nHappy webcam repurposing!")
            break
        else:
            logger.info("Invalid choice. Please select 1-5.")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()
