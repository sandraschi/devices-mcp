import asyncio
import logging
import os
import platform
from collections.abc import AsyncGenerator

import cv2

logger = logging.getLogger(__name__)


async def generate_webcam_stream(camera) -> AsyncGenerator[bytes, None]:
    """Generate MJPEG stream from webcam.

    OpenCV calls run in asyncio.to_thread so the uvicorn event loop is not blocked
    (blocking here previously froze every other API request / page spinner).
    """
    cap = None
    try:
        device_id = getattr(camera, "_device_id", 0)
        # Windows: default MSMF backend often fails on USB UVC devices; DirectShow is more reliable.
        if platform.system() == "Windows":
            cap = await asyncio.to_thread(cv2.VideoCapture, device_id, cv2.CAP_DSHOW)
        else:
            cap = await asyncio.to_thread(cv2.VideoCapture, device_id, cv2.CAP_ANY)

        if not cap.isOpened():
            logger.error(f"Could not open webcam device {device_id} for streaming")
            return

        config = getattr(camera, "config", None)
        params = (
            getattr(config, "params", {})
            if config is not None and not isinstance(config, dict)
            else (config.get("params", {}) if isinstance(config, dict) else {})
        )
        if not isinstance(params, dict):
            params = {}
        resolution = params.get("resolution", "640x480")
        width, height = map(int, resolution.split("x"))

        await asyncio.to_thread(cap.set, cv2.CAP_PROP_FRAME_WIDTH, width)
        await asyncio.to_thread(cap.set, cv2.CAP_PROP_FRAME_HEIGHT, height)
        await asyncio.to_thread(cap.set, cv2.CAP_PROP_FPS, 10)

        logger.info(f"Streaming webcam {device_id} at {width}x{height}")

        while True:
            ret, frame = await asyncio.to_thread(cap.read)
            if not ret:
                await asyncio.sleep(0.1)
                continue

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 80]
            result, encoded_img = await asyncio.to_thread(cv2.imencode, ".jpg", frame, encode_param)

            if result:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded_img.tobytes() + b"\r\n")
            await asyncio.sleep(0.1)

    except Exception:
        logger.exception("Error generating webcam stream")
        yield (
            b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
            + b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9"
            + b"\r\n"
        )
    finally:
        if cap:
            await asyncio.to_thread(cap.release)


async def generate_rtsp_mjpeg_stream(rtsp_url: str) -> AsyncGenerator[bytes, None]:
    """Generate MJPEG stream from RTSP URL for browser viewing."""
    logger.info(f"Opening RTSP stream: {rtsp_url[:60]}...")

    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|analyzeduration;1000000|probesize;1000000"

    cap = await asyncio.to_thread(cv2.VideoCapture, rtsp_url, cv2.CAP_FFMPEG)
    try:
        if not cap.isOpened():
            logger.error(f"Failed to open RTSP stream: {rtsp_url[:60]}...")
            return

        consecutive_failures = 0
        max_failures = 50

        while consecutive_failures < max_failures:
            ret, frame = await asyncio.to_thread(cap.read)
            if not ret:
                consecutive_failures += 1
                await asyncio.sleep(0.1)
                continue

            consecutive_failures = 0

            height, width = frame.shape[:2]
            if width > 1280:
                scale = 1280 / width
                new_w, new_h = int(width * scale), int(height * scale)
                frame = await asyncio.to_thread(cv2.resize, frame, (new_w, new_h))

            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            result, encoded_img = await asyncio.to_thread(cv2.imencode, ".jpg", frame, encode_param)

            if result:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + encoded_img.tobytes() + b"\r\n")

            await asyncio.sleep(0.05)
    except Exception as e:
        logger.exception(f"Error generating RTSP MJPEG stream: {e}")
    finally:
        await asyncio.to_thread(cap.release)
        logger.info("RTSP stream released")
