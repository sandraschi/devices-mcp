import logging

logger = logging.getLogger(__name__)

"""Helper script to find Tapo camera credentials.

This script tries common credential combinations to help identify
what credentials your Tapo camera uses after reset.
"""

import sys

from pytapo import Tapo


def try_credentials(ip, username, password):
    """Try to connect with given credentials."""
    try:
        logger.info(f"  Trying {username}/{password}...", end=" ")
        camera = Tapo(ip, username, password)
        camera.getBasicInfo()
        logger.info("[SUCCESS!]")
        return True
    except Exception as e:
        error_msg = str(e)
        if "Temporary Suspension" in error_msg:
            logger.info("[LOCKED OUT - Wait 30 min]")
            return "locked"
        if "Invalid authentication" in error_msg:
            logger.info("[FAILED]")
            return False
        logger.info(f"[ERROR: {error_msg[:50]}]")
        return False


def find_credentials(ip):
    """Try common credential combinations."""
    logger.info(f"\nSearching for credentials for camera at {ip}...")
    logger.info("=" * 60)

    # Common combinations to try
    combinations = [
        # Default after reset (most common)
        ("admin", "admin"),
        # Cloud account
        ("sandraschipal@hotmail.com", "Sec0860ta#"),
        # Variations
        ("admin", ""),
        ("", "admin"),
    ]

    for username, password in combinations:
        result = try_credentials(ip, username, password)
        if result is True:
            logger.info("\n[SUCCESS] Found working credentials!")
            logger.info(f"Username: {username}")
            logger.info(f"Password: {password}")
            logger.info("\nUpdate your config.yaml with these credentials.")
            return (username, password)
        if result == "locked":
            logger.info("\n[STOPPED] Camera is locked out. Wait 30 minutes or power cycle camera.")
            return None

    logger.info("\n" + "=" * 60)
    logger.info("[FAILED] None of the common credentials worked.")
    logger.info("\nTry manually:")
    logger.info("1. Check the camera label/sticker for default credentials")
    logger.info("2. Check device manual for default username/password")
    logger.info("3. In Tapo app: Camera -> Advanced -> Local Device Settings")
    logger.info("4. Password might be in TPL[numbers] format from label")
    logger.info("=" * 60)
    return None


if __name__ == "__main__":
    if len(sys.argv) > 1:
        ip = sys.argv[1]
    else:
        ip = "192.168.0.164"  # Kitchen camera

    logger.info("Tapo Camera Credential Finder")
    logger.info(f"Testing camera at {ip}")
    logger.info("\nWARNING: Too many failed attempts will lock the camera!")
    logger.info("This script tries common combinations carefully.\n")

    result = find_credentials(ip)

    if result:
        logger.info(f"\nWorking credentials found: {result[0]}/{result[1]}")
        sys.exit(0)
    else:
        logger.info("\nManual credential lookup required.")
        sys.exit(1)
