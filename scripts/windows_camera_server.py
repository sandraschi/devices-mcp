#!/usr/bin/env python3
"""
Windows USB Camera Server for Devices MCP.

This server runs on Windows host and provides HTTP access to USB cameras
that can't be accessed from Docker containers on Windows.
"""

import asyncio
import io
import logging
import os
import platform
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

import cv2
from PIL import Image

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from devices_mcp.utils.logging import setup_logging

# Suppress OpenCV warnings
os.environ["OPENCV_LOG_LEVEL"] = "ERROR"
# Suppress most OpenCV log messages if possible
# cv2.setLogLevel(0) is not available in all versions

logger = logging.getLogger(__name__)


class CameraManager:
    """Manages USB cameras on Windows."""

    def __init__(self):
        self.cameras = {}
        self.frames = {}
        self.capture_threads = {}
        self.lock = threading.Lock()
        self._auto_discovered = False

    def add_camera(self, camera_id: int, name: str, existing_cap=None):
        """Add a camera by device ID."""
        with self.lock:
            if camera_id in self.cameras:
                logger.warning(f"Camera {camera_id} already exists")
                if existing_cap:
                    existing_cap.release()
                return

            cap = existing_cap
            if not cap:
                cap = (
                    cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                    if platform.system() == "Windows"
                    else cv2.VideoCapture(camera_id, cv2.CAP_ANY)
                )

            if not cap.isOpened():
                logger.error(f"Failed to open camera {camera_id}")
                return

            self.cameras[camera_id] = {
                "name": name,
                "cap": cap,
                "last_frame": None,
                "last_frame_time": 0,
                "thread": None,
                "active": True,
                "error_count": 0,
            }

            # Start capture thread
            thread = threading.Thread(target=self._capture_loop, args=(camera_id,), daemon=True)
            thread.start()
            self.capture_threads[camera_id] = thread

            logger.info(f"Added camera {camera_id}: {name}")

    def auto_discover_cameras(self):
        """Automatically discover all available USB cameras."""
        if self._auto_discovered:
            logger.info("Auto-discovery already performed, skipping")
            return

        logger.info("Auto-discovering USB cameras for Windows server...")

        discovered_count = 0
        max_devices = 10

        for device_id in range(max_devices):
            try:
                cap = (
                    cv2.VideoCapture(device_id, cv2.CAP_DSHOW)
                    if platform.system() == "Windows"
                    else cv2.VideoCapture(device_id, cv2.CAP_ANY)
                )
                if cap.isOpened():
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        # Get camera info
                        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                        # Generate friendly name
                        camera_name = self._generate_camera_name(device_id, width, height)
                        # Add the camera directly without closing it
                        self.add_camera(device_id, camera_name, existing_cap=cap)
                        discovered_count += 1

                        logger.info(f"Auto-discovered camera {device_id}: {camera_name} ({width}x{height})")
                    else:
                        cap.release()
                else:
                    # Try different backend
                    cap.release()

            except Exception as e:
                logger.debug(f"Error checking camera device {device_id}: {e}")
                continue

        self._auto_discovered = True
        logger.info(f"Auto-discovery complete: found {discovered_count} USB camera(s)")

    def _generate_camera_name(self, device_id: int, width: int, height: int) -> str:
        """Generate a friendly name for a camera based on its properties."""
        resolution = f"{width}x{height}"

        # Classify camera type based on resolution
        if width >= 3840 and height >= 2160:
            camera_type = "4K Camera"
        elif width >= 1920 and height >= 1080:
            camera_type = "HD Webcam"
        elif width >= 1280 and height >= 720:
            camera_type = "HD Camera"
        elif width <= 640 and height <= 480:
            camera_type = "VGA Camera"
        else:
            camera_type = "Webcam"

        # Use common names for first few cameras
        common_names = [
            "Built-in Camera",
            "USB Webcam",
            "External Camera",
            "Document Camera",
            "Microscope Camera",
        ]

        if device_id < len(common_names):
            return f"{common_names[device_id]} ({resolution})"
        return f"{camera_type} {device_id} ({resolution})"

    def _capture_loop(self, camera_id: int):
        """Background capture loop for a camera with auto-reconnect."""
        camera = self.cameras.get(camera_id)
        if not camera:
            return

        while camera["active"]:
            try:
                cap = camera["cap"]
                ret, frame = cap.read()
                if ret:
                    # Reset error count on success
                    camera["error_count"] = 0

                    # Convert BGR to RGB and store
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_image = Image.fromarray(rgb_frame)

                    with self.lock:
                        camera["last_frame"] = pil_image
                        camera["last_frame_time"] = time.time()
                else:
                    camera["error_count"] += 1
                    logger.warning(f"No frame from camera {camera_id} (error count: {camera['error_count']})")

                    # Try to re-open if too many errors
                    if camera["error_count"] >= 10:
                        logger.info(f"Attempting to re-initialize camera {camera_id}...")
                        cap.release()
                        new_cap = (
                            cv2.VideoCapture(camera_id, cv2.CAP_DSHOW)
                            if platform.system() == "Windows"
                            else cv2.VideoCapture(camera_id, cv2.CAP_ANY)
                        )
                        camera["cap"] = new_cap
                        camera["error_count"] = 0
                        time.sleep(1.0)  # Grace period

            except Exception as e:
                logger.error(f"Error capturing from camera {camera_id}: {e}")
                camera["error_count"] += 1
                time.sleep(1.0)

            time.sleep(0.1)  # 10 FPS

    def get_snapshot(self, camera_id: int):
        """Get snapshot from camera."""
        with self.lock:
            camera = self.cameras.get(camera_id)
            if not camera or not camera["last_frame"]:
                return None
            return camera["last_frame"].copy()

    def get_mjpeg_stream(self, camera_id: int):
        """Get MJPEG stream generator for camera."""

        def generate():
            while True:
                frame = self.get_snapshot(camera_id)
                if frame:
                    # Convert to JPEG
                    buf = io.BytesIO()
                    frame.save(buf, format="JPEG", quality=80)
                    jpeg_data = buf.getvalue()

                    # MJPEG frame
                    yield b"--frame\r\n"
                    yield b"Content-Type: image/jpeg\r\n"
                    yield f"Content-Length: {len(jpeg_data)}\r\n\r\n".encode()
                    yield jpeg_data
                    yield b"\r\n"

                time.sleep(0.1)  # 10 FPS

        return generate()

    def close_camera(self, camera_id: int):
        """Close a camera."""
        with self.lock:
            camera = self.cameras.get(camera_id)
            if camera:
                camera["active"] = False
                if camera["cap"]:
                    camera["cap"].release()
                logger.info(f"Closed camera {camera_id}")

    def close_all(self):
        """Close all cameras."""
        for camera_id in list(self.cameras.keys()):
            self.close_camera(camera_id)


class CameraHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for camera server."""

    def __init__(self, *args, camera_manager=None, **kwargs):
        self.camera_manager = camera_manager
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path_parts = parsed_path.path.strip("/").split("/")

        if len(path_parts) >= 2 and path_parts[0] == "camera":
            try:
                camera_id = int(path_parts[1])

                if len(path_parts) >= 3 and path_parts[2] == "snapshot":
                    # Get snapshot
                    frame = self.camera_manager.get_snapshot(camera_id)
                    if frame:
                        buf = io.BytesIO()
                        frame.save(buf, format="JPEG", quality=80)
                        jpeg_data = buf.getvalue()

                        self.send_response(200)
                        self.send_header("Content-Type", "image/jpeg")
                        self.send_header("Content-Length", str(len(jpeg_data)))
                        self.end_headers()
                        self.wfile.write(jpeg_data)
                    else:
                        self.send_error(404, "No frame available")

                elif len(path_parts) >= 3 and path_parts[2] == "mjpeg":
                    # Get MJPEG stream
                    self.send_response(200)
                    self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()

                    try:
                        for frame_data in self.camera_manager.get_mjpeg_stream(camera_id):
                            self.wfile.write(frame_data)
                    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                        # Client disconnected
                        pass

                else:
                    self.send_error(404, "Invalid endpoint")

            except (ValueError, IndexError):
                self.send_error(400, "Invalid camera ID")

        elif parsed_path.path == "/status":
            # Status endpoint
            status = {"cameras": {}}

            for cam_id, camera in self.camera_manager.cameras.items():
                status["cameras"][str(cam_id)] = {
                    "name": camera["name"],
                    "active": camera["active"],
                    "has_frame": camera["last_frame"] is not None,
                    "last_frame_time": camera["last_frame_time"],
                }

            import json

            response = json.dumps(status).encode()

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        else:
            self.send_error(404, "Not found")

    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.info(format % args)


def run_server(camera_manager, port=10715):
    """Run the HTTP server."""

    def handler_class(*args, **kwargs):
        return CameraHTTPRequestHandler(*args, camera_manager=camera_manager, **kwargs)

    # Bind 127.0.0.1 so clients using WINDOWS_CAMERA_SERVER_URL=http://127.0.0.1:... always reach us
    # (localhost can resolve to IPv6 ::1 while the backend uses IPv4).
    server = HTTPServer(("127.0.0.1", port), handler_class)
    logger.info(f"Windows Camera Server started on http://127.0.0.1:{port}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
    finally:
        camera_manager.close_all()


async def main():
    """Main function."""
    setup_logging()
    logger.info("Starting Windows USB Camera Server")

    camera_manager = CameraManager()

    # Auto-discover all available USB cameras
    camera_manager.auto_discover_cameras()

    # Give cameras time to initialize
    await asyncio.sleep(2)

    # Check which cameras are working
    working_cameras = 0
    for cam_id, camera in camera_manager.cameras.items():
        if camera["last_frame"]:
            logger.info(f"Camera {cam_id} ({camera['name']}) is working")
            working_cameras += 1
        else:
            logger.warning(f"Camera {cam_id} ({camera['name']}) is not providing frames")

    if working_cameras == 0:
        logger.warning(
            "No working cameras found. Make sure USB cameras are connected and not in use by other applications."
        )
    else:
        logger.info(f"{working_cameras} camera(s) are working and ready for streaming")

    # Start HTTP server in a thread
    server_thread = threading.Thread(target=run_server, args=(camera_manager, 10715), daemon=True)
    server_thread.start()

    logger.info("Windows Camera Server running. Press Ctrl+C to stop.")
    logger.info("Available endpoints:")
    logger.info("  GET /status - Camera status and list of available cameras")

    if camera_manager.cameras:
        for cam_id in camera_manager.cameras.keys():
            logger.info(f"  GET /camera/{cam_id}/snapshot - Camera {cam_id} snapshot")
            logger.info(f"  GET /camera/{cam_id}/mjpeg - Camera {cam_id} MJPEG stream")
    else:
        logger.info("  No cameras detected. Connect USB cameras and restart the server.")

    logger.info("")
    logger.info("USB Camera Features:")
    logger.info("  [x] Auto-detection of all connected cameras")
    logger.info("  [x] No manual configuration required")
    logger.info("  [x] Always online (no connection procedures)")
    logger.info("  [x] MJPEG streaming for real-time video")
    logger.info("  [x] Automatic fallback and error recovery")

    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        camera_manager.close_all()


if __name__ == "__main__":
    asyncio.run(main())
