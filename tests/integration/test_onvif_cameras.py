"""
Integration tests for ONVIF cameras with real hardware.

Tests real ONVIF camera connections, stream URLs, and stream endpoints.
Requires real cameras configured in config.yaml.

To run:
    pytest tests/integration/test_onvif_cameras.py -v -m integration

To skip:
    pytest tests/integration/test_onvif_cameras.py -v -m "not integration"

Note: If you get "permission error accessing a socket", this may be:
1. Windows firewall blocking socket access
2. Port already in use (check with: netstat -ano | findstr :2020)
3. ONVIF library trying to bind to a port
4. Multiple test instances running simultaneously
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

import logging

import yaml

# Setup logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mark all tests in this file as integration tests
pytestmark = pytest.mark.integration


def load_config():
    """Load config.yaml to get camera credentials."""
    config_path = project_root / "config.yaml"
    if not config_path.exists():
        return None

    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_onvif_cameras():
    """Get all ONVIF cameras from config."""
    config = load_config()
    if not config:
        return []

    cameras = config.get("cameras", {})
    onvif_cameras = []

    for name, cam_cfg in cameras.items():
        cam_type = cam_cfg.get("type", "").lower()
        params = cam_cfg.get("params", {})

        # Check if it's an ONVIF camera
        if cam_type == "onvif" or params.get("onvif_port"):
            onvif_cameras.append(
                {
                    "name": name,
                    "host": params.get("host"),
                    "port": params.get("onvif_port", 2020),
                    "username": params.get("username"),
                    "password": params.get("password"),
                }
            )

    return onvif_cameras


@pytest.fixture(scope="module")
def onvif_cameras():
    """Get ONVIF cameras from config."""
    cameras = get_onvif_cameras()
    if not cameras:
        pytest.skip("No ONVIF cameras configured in config.yaml")
    return cameras


@pytest.fixture(scope="module")
def camera_manager():
    """Get camera manager instance."""
    from devices_mcp.camera.manager import CameraManager

    return CameraManager()


@pytest.mark.asyncio
async def test_onvif_camera_connection(onvif_cameras):
    """Test ONVIF camera connection to real hardware."""
    for camera_info in onvif_cameras:
        try:
            from devices_mcp.camera.base import CameraConfig, CameraType
            from devices_mcp.camera.onvif_camera import ONVIFBasedCamera

            config = CameraConfig(
                name=camera_info["name"],
                type=CameraType.ONVIF,
                params={
                    "host": camera_info["host"],
                    "onvif_port": camera_info["port"],
                    "username": camera_info["username"],
                    "password": camera_info["password"],
                },
            )

            camera = ONVIFBasedCamera(config)

            # Test connection
            connected = await asyncio.wait_for(camera.connect(), timeout=15.0)
            assert connected, f"Failed to connect to {camera_info['name']}"

            # Test status
            status = await asyncio.wait_for(camera.get_status(), timeout=10.0)
            assert status.get("connected", False), f"Camera {camera_info['name']} not connected"

            logger.info(f"SUCCESS: {camera_info['name']}: Connected successfully")
            logger.info(f"   Model: {status.get('model', 'Unknown')}")
            logger.info(f"   Resolution: {status.get('resolution', 'Unknown')}")

        except TimeoutError:
            pytest.fail(f"Connection to {camera_info['name']} timed out")
        except OSError as e:
            if "permission" in str(e).lower() or "10013" in str(e) or "10048" in str(e):
                pytest.skip(
                    f"Socket permission error for {camera_info['name']}: {e}. "
                    f"This may be a Windows firewall or port conflict issue."
                )
            pytest.fail(f"Connection to {camera_info['name']} failed with OSError: {e}")
        except Exception as e:
            error_msg = str(e)
            if "permission" in error_msg.lower() or "socket" in error_msg.lower():
                pytest.skip(
                    f"Socket permission error for {camera_info['name']}: {e}. "
                    f"This may be a Windows firewall or port conflict issue."
                )
            pytest.fail(f"Connection to {camera_info['name']} failed: {e}")


@pytest.mark.asyncio
async def test_onvif_stream_url(onvif_cameras):
    """Test getting stream URL from real ONVIF cameras."""
    for camera_info in onvif_cameras:
        try:
            from devices_mcp.camera.base import CameraConfig, CameraType
            from devices_mcp.camera.onvif_camera import ONVIFBasedCamera

            config = CameraConfig(
                name=camera_info["name"],
                type=CameraType.ONVIF,
                params={
                    "host": camera_info["host"],
                    "onvif_port": camera_info["port"],
                    "username": camera_info["username"],
                    "password": camera_info["password"],
                },
            )

            camera = ONVIFBasedCamera(config)

            # Connect first
            await asyncio.wait_for(camera.connect(), timeout=15.0)

            # Get stream URL (should be fresh, not cached)
            stream_url = await asyncio.wait_for(camera.get_stream_url(), timeout=15.0)

            assert stream_url is not None, f"No stream URL returned for {camera_info['name']}"
            assert stream_url.startswith("rtsp://"), f"Invalid stream URL format: {stream_url}"
            assert camera_info["host"] in stream_url, "Stream URL doesn't contain camera host"

            logger.info(f"SUCCESS: {camera_info['name']}: Stream URL retrieved")
            logger.info(f"   URL: {stream_url[:60]}...")

            # Test getting stream URL again (should still work, fresh connection)
            stream_url2 = await asyncio.wait_for(camera.get_stream_url(), timeout=15.0)
            assert stream_url2 == stream_url, "Stream URL should be consistent"

        except TimeoutError:
            pytest.fail(f"Stream URL retrieval for {camera_info['name']} timed out")
        except OSError as e:
            if "permission" in str(e).lower() or "10013" in str(e) or "10048" in str(e):
                pytest.skip(f"Socket permission error for {camera_info['name']}: {e}")
            pytest.fail(f"Stream URL retrieval for {camera_info['name']} failed with OSError: {e}")
        except Exception as e:
            error_msg = str(e)
            if "permission" in error_msg.lower() or "socket" in error_msg.lower():
                pytest.skip(f"Socket permission error for {camera_info['name']}: {e}")
            pytest.fail(f"Stream URL retrieval for {camera_info['name']} failed: {e}")


@pytest.mark.asyncio
async def test_onvif_stream_endpoint(onvif_cameras):
    """Test stream endpoint with real ONVIF cameras."""
    for camera_info in onvif_cameras:
        try:
            from devices_mcp.core.server import TapoCameraServer

            # Get server instance
            server = await asyncio.wait_for(TapoCameraServer.get_instance(), timeout=10.0)

            # Get camera from manager
            camera = await asyncio.wait_for(server.camera_manager.get_camera(camera_info["name"]), timeout=5.0)

            assert camera is not None, f"Camera {camera_info['name']} not found in manager"

            # Test stream URL endpoint logic
            stream_url = await asyncio.wait_for(camera.get_stream_url(), timeout=15.0)
            assert stream_url is not None, f"No stream URL for {camera_info['name']}"

            logger.info(f"SUCCESS: {camera_info['name']}: Stream endpoint test passed")
            logger.info(f"   Stream URL available: {stream_url[:50]}...")

        except TimeoutError:
            pytest.fail(f"Stream endpoint test for {camera_info['name']} timed out")
        except OSError as e:
            if "permission" in str(e).lower() or "10013" in str(e) or "10048" in str(e):
                pytest.skip(f"Socket permission error for {camera_info['name']}: {e}")
            pytest.fail(f"Stream endpoint test for {camera_info['name']} failed with OSError: {e}")
        except Exception as e:
            error_msg = str(e)
            if "permission" in error_msg.lower() or "socket" in error_msg.lower():
                pytest.skip(f"Socket permission error for {camera_info['name']}: {e}")
            pytest.fail(f"Stream endpoint test for {camera_info['name']} failed: {e}")


@pytest.mark.asyncio
async def test_onvif_snapshot(onvif_cameras):
    """Test getting snapshot from real ONVIF cameras."""
    for camera_info in onvif_cameras:
        try:
            from devices_mcp.camera.base import CameraConfig, CameraType
            from devices_mcp.camera.onvif_camera import ONVIFBasedCamera

            config = CameraConfig(
                name=camera_info["name"],
                type=CameraType.ONVIF,
                params={
                    "host": camera_info["host"],
                    "onvif_port": camera_info["port"],
                    "username": camera_info["username"],
                    "password": camera_info["password"],
                },
            )

            camera = ONVIFBasedCamera(config)

            # Connect first
            await asyncio.wait_for(camera.connect(), timeout=15.0)

            # Get snapshot (capture_still returns PIL Image)
            snapshot_image = await asyncio.wait_for(camera.capture_still(), timeout=15.0)

            # Snapshot should be PIL Image
            if snapshot_image:
                from PIL import Image

                assert isinstance(snapshot_image, Image.Image), (
                    f"Snapshot should be PIL Image, got {type(snapshot_image)}"
                )
                assert snapshot_image.size[0] > 0 and snapshot_image.size[1] > 0, (
                    "Snapshot should have valid dimensions"
                )
                print(
                    f"SUCCESS: {camera_info['name']}: Snapshot retrieved ({snapshot_image.size[0]}x{snapshot_image.size[1]})"
                )
            else:
                logger.info(f"WARNING: {camera_info['name']}: Snapshot not supported (this is OK)")

        except TimeoutError:
            pytest.fail(f"Snapshot retrieval for {camera_info['name']} timed out")
        except OSError as e:
            if "permission" in str(e).lower() or "10013" in str(e) or "10048" in str(e):
                pytest.skip(f"Socket permission error for {camera_info['name']}: {e}")
            pytest.fail(f"Snapshot retrieval for {camera_info['name']} failed with OSError: {e}")
        except Exception as e:
            error_msg = str(e)
            if "permission" in error_msg.lower() or "socket" in error_msg.lower():
                pytest.skip(f"Socket permission error for {camera_info['name']}: {e}")
            pytest.fail(f"Snapshot retrieval for {camera_info['name']} failed: {e}")


@pytest.mark.asyncio
async def test_onvif_mjpeg_stream_endpoint(onvif_cameras):
    """Test MJPEG stream endpoint with real ONVIF cameras (simulates web request)."""
    for camera_info in onvif_cameras:
        try:
            from devices_mcp.core.server import TapoCameraServer

            # Get server instance (hardware init can take up to 30s)
            server = await asyncio.wait_for(TapoCameraServer.get_instance(), timeout=35.0)

            # Get camera from manager
            camera = await asyncio.wait_for(server.camera_manager.get_camera(camera_info["name"]), timeout=5.0)

            assert camera is not None, f"Camera {camera_info['name']} not found in manager"

            # Test stream URL retrieval (what the endpoint does)
            stream_url = await asyncio.wait_for(camera.get_stream_url(), timeout=15.0)
            assert stream_url is not None, f"No stream URL for {camera_info['name']}"

            # Verify stream URL is valid RTSP
            assert stream_url.startswith("rtsp://"), f"Invalid stream URL format: {stream_url}"

            # Test that we can get stream URL multiple times (fresh connections)
            for i in range(3):
                url = await asyncio.wait_for(camera.get_stream_url(), timeout=15.0)
                assert url == stream_url, f"Stream URL changed on iteration {i + 1}"

            logger.info(f"SUCCESS: {camera_info['name']}: MJPEG stream endpoint test passed")
            logger.info(f"   Stream URL: {stream_url[:60]}...")
            logger.info("   Multiple requests: OK (fresh connections)")

        except TimeoutError:
            pytest.fail(f"MJPEG stream endpoint test for {camera_info['name']} timed out")
        except OSError as e:
            if "permission" in str(e).lower() or "10013" in str(e) or "10048" in str(e):
                pytest.skip(f"Socket permission error for {camera_info['name']}: {e}")
            pytest.fail(f"MJPEG stream endpoint test for {camera_info['name']} failed with OSError: {e}")
        except Exception as e:
            error_msg = str(e)
            if "permission" in error_msg.lower() or "socket" in error_msg.lower():
                pytest.skip(f"Socket permission error for {camera_info['name']}: {e}")
            pytest.fail(f"MJPEG stream endpoint test for {camera_info['name']} failed: {e}")


@pytest.mark.asyncio
async def test_onvif_fresh_connection_each_time(onvif_cameras):
    """Test that each stream URL request creates a fresh connection (no stale auth)."""
    for camera_info in onvif_cameras:
        try:
            from devices_mcp.camera.base import CameraConfig, CameraType
            from devices_mcp.camera.onvif_camera import ONVIFBasedCamera

            config = CameraConfig(
                name=camera_info["name"],
                type=CameraType.ONVIF,
                params={
                    "host": camera_info["host"],
                    "onvif_port": camera_info["port"],
                    "username": camera_info["username"],
                    "password": camera_info["password"],
                },
            )

            # Create fresh camera instance
            camera1 = ONVIFBasedCamera(config)
            stream_url1 = await asyncio.wait_for(camera1.get_stream_url(), timeout=15.0)

            # Create another fresh instance (simulates new request)
            camera2 = ONVIFBasedCamera(config)
            stream_url2 = await asyncio.wait_for(camera2.get_stream_url(), timeout=15.0)

            # Both should work (fresh connections)
            assert stream_url1 is not None, "First stream URL should work"
            assert stream_url2 is not None, "Second stream URL should work"
            assert stream_url1 == stream_url2, "Stream URLs should be the same"

            logger.info(f"SUCCESS: {camera_info['name']}: Fresh connections work correctly")

        except TimeoutError:
            pytest.fail(f"Fresh connection test for {camera_info['name']} timed out")
        except OSError as e:
            if "permission" in str(e).lower() or "10013" in str(e) or "10048" in str(e):
                pytest.skip(f"Socket permission error for {camera_info['name']}: {e}")
            pytest.fail(f"Fresh connection test for {camera_info['name']} failed with OSError: {e}")
        except Exception as e:
            error_msg = str(e)
            if "permission" in error_msg.lower() or "socket" in error_msg.lower():
                pytest.skip(f"Socket permission error for {camera_info['name']}: {e}")
            pytest.fail(f"Fresh connection test for {camera_info['name']} failed: {e}")


@pytest.mark.asyncio
async def test_onvif_camera_manager_integration(onvif_cameras, camera_manager):
    """Test ONVIF cameras through camera manager."""
    try:
        # Add cameras to manager
        for camera_info in onvif_cameras:
            from devices_mcp.camera.base import CameraConfig, CameraType

            config = CameraConfig(
                name=camera_info["name"],
                type=CameraType.ONVIF,
                params={
                    "host": camera_info["host"],
                    "onvif_port": camera_info["port"],
                    "username": camera_info["username"],
                    "password": camera_info["password"],
                },
            )

            await asyncio.wait_for(camera_manager.add_camera(config), timeout=10.0)

        # List cameras
        cameras = await asyncio.wait_for(camera_manager.list_cameras(), timeout=5.0)

        onvif_found = [c for c in cameras if c.get("type") == "onvif"]
        assert len(onvif_found) == len(onvif_cameras), (
            f"Expected {len(onvif_cameras)} ONVIF cameras, found {len(onvif_found)}"
        )

        # Test getting each camera
        for camera_info in onvif_cameras:
            camera = await asyncio.wait_for(camera_manager.get_camera(camera_info["name"]), timeout=5.0)
            assert camera is not None, f"Camera {camera_info['name']} not found"

            # Test stream URL through manager
            stream_url = await asyncio.wait_for(camera.get_stream_url(), timeout=15.0)
            assert stream_url is not None, f"No stream URL for {camera_info['name']}"

        logger.info(f"SUCCESS: Camera manager integration: {len(onvif_cameras)} cameras working")

    except TimeoutError:
        pytest.fail("Camera manager integration test timed out")
    except OSError as e:
        if "permission" in str(e).lower() or "10013" in str(e) or "10048" in str(e):
            pytest.skip(f"Socket permission error in camera manager test: {e}")
        pytest.fail(f"Camera manager integration test failed with OSError: {e}")
    except Exception as e:
        error_msg = str(e)
        if "permission" in error_msg.lower() or "socket" in error_msg.lower():
            pytest.skip(f"Socket permission error in camera manager test: {e}")
        pytest.fail(f"Camera manager integration test failed: {e}")
