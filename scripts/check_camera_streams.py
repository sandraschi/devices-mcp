"""Check what streaming methods the camera supports."""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from devices_mcp.camera.onvif_camera import ONVIFCameraWrapper

logger = logging.getLogger(__name__)


async def check_camera_streams(host: str, username: str, password: str):
    """Check what streaming methods the camera supports."""
    logger.info(f"Checking streams for camera at {host}")

    try:
        wrapper = ONVIFCameraWrapper(host, 2020, username, password)
        wrapper.connect()

        # Get media service
        media_service = wrapper._camera.create_media_service()
        profiles = media_service.GetProfiles()

        logger.info(f"Found {len(profiles)} profiles:")
        for i, profile in enumerate(profiles):
            logger.info(
                f"  Profile {i}: {profile.Name} - {profile.VideoEncoderConfiguration.Encoding}"
            )

            # Get stream URI for this profile
            try:
                stream_uri = media_service.GetStreamUri(
                    {
                        "StreamSetup": {
                            "Stream": "RTP-Unicast",
                            "Transport": {"Protocol": "RTSP", "Tunnel": 0},
                        },
                        "ProfileToken": profile.token,
                    }
                )

                uri = stream_uri.Uri
                logger.info(f"    RTSP URI: {uri}")

                # Try different protocols
                for protocol in ["HTTP", "RTSP", "UDP"]:
                    try:
                        stream_uri_alt = media_service.GetStreamUri(
                            {
                                "StreamSetup": {
                                    "Stream": "RTP-Unicast",
                                    "Transport": {"Protocol": protocol, "Tunnel": 0},
                                },
                                "ProfileToken": profile.token,
                            }
                        )
                        logger.info(f"    {protocol} URI: {stream_uri_alt.Uri}")
                    except Exception as e:
                        logger.info(f"    {protocol} not supported: {e}")

            except Exception as e:
                logger.info(f"    Error getting stream URI: {e}")

    except Exception as e:
        logger.info(f"Error connecting to camera: {e}")
        import traceback

        traceback.print_exc()


async def main():
    """Check kitchen camera streams."""
    await check_camera_streams("192.168.0.164", "sandraschi", "Sec1000kitchen")


if __name__ == "__main__":
    asyncio.run(main())
