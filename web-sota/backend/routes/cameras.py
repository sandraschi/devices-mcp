import asyncio
import io
import logging
import os
import re

from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse, Response, StreamingResponse

from backend.utils.streaming import generate_rtsp_mjpeg_stream, generate_webcam_stream

logger = logging.getLogger(__name__)

router = APIRouter()


async def _windows_camera_server_has_device(base: str, device_id: int) -> bool:
    """True if the optional USB helper (scripts/windows_camera_server.py) is up and knows this index."""
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            r = await client.get(f"{base}/status", timeout=2.0)
            if r.status_code != 200:
                return False
            cams = (r.json() or {}).get("cameras") or {}
            return str(device_id) in cams
    except Exception:
        return False


@router.get("/api/cameras")
async def get_cameras():
    """Get list of cameras."""
    try:
        from devices_mcp.core.server import DevicesMCPServer

        # Shield singleton initialization from per-request timeout cancellation.
        # Otherwise wait_for cancels shared init and leaves startup in a bad state.
        server = await asyncio.wait_for(
            asyncio.shield(DevicesMCPServer.get_instance()),
            timeout=5.0,
        )
        cameras = await asyncio.wait_for(server.camera_manager.list_cameras(), timeout=8.0)

        # Ring integration
        try:
            from backend.api.ring import get_ring_client

            ring_client = get_ring_client()
            if ring_client and ring_client.is_initialized:
                doorbells = await asyncio.wait_for(ring_client.get_doorbells(), timeout=3.0)
                for doorbell in doorbells:
                    cameras.append(
                        {
                            "name": f"ring_{doorbell.id}",
                            "type": "ring",
                            "status": "online" if doorbell.is_online else "offline",
                            "model": doorbell.device_type,
                            "firmware": doorbell.extra_data.get("firmware", "N/A"),
                            "battery_life": doorbell.battery_level,
                            "streaming": True,
                            "capture_capable": True,
                            "groups": [],
                        }
                    )
        except Exception:
            logger.debug("Ring integration not available or failed")

        return {"success": True, "initializing": False, "cameras": cameras}
    except TimeoutError:
        # Clean warmup response: don't spam tracebacks while the singleton is still booting.
        init_state = {
            "initialized": bool(getattr(DevicesMCPServer, "_initialized", False)),
            "initializing": bool(getattr(DevicesMCPServer, "_initializing", False)),
            "hardware_initialized": bool(getattr(DevicesMCPServer, "_hardware_initialized", False)),
        }
        logger.warning("Cameras API timed out waiting for server init (state=%s)", init_state)
        return {
            "success": False,
            "initializing": True,
            "message": "Device server is still starting. Retry in a few seconds.",
            "init_state": init_state,
            "cameras": [],
        }
    except Exception as e:
        logger.exception("Error getting cameras list")
        return {"success": False, "initializing": False, "error": str(e), "cameras": []}


@router.get("/api/cameras/status")
async def get_cameras_status():
    """Get camera status summary."""
    try:
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()
        cameras = await server.camera_manager.list_cameras()
        total = len(cameras)
        online = sum(1 for cam in cameras if cam.get("status") == "online")
        return {
            "total": total,
            "online": online,
            "offline": total - online,
            "cameras": cameras,
            "initializing": False,
        }
    except TimeoutError:
        return {"success": False, "initializing": True, "total": 0, "online": 0, "offline": 0, "cameras": []}
    except Exception as e:
        return {"success": False, "initializing": False, "error": str(e), "total": 0, "online": 0, "offline": 0}


@router.get("/api/cameras/{camera_id}/stream")
async def get_camera_stream(camera_id: str):
    """Get camera video stream."""
    if not re.match(r"^[a-zA-Z0-9_-]{1,100}$", camera_id):
        return JSONResponse({"error": "Invalid camera_id format"}, status_code=400)

    try:
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()

        if hasattr(server, "camera_manager") and server.camera_manager:
            camera = server.camera_manager.cameras.get(camera_id)

            if camera_id.startswith("ring_"):
                return {"stream_url": None, "type": "webrtc", "note": "Ring camera uses WebRTC"}

            if camera:
                camera_type = camera.config.type
                if hasattr(camera_type, "value"):
                    camera_type = camera_type.value

                if camera_type in ["webcam", "microscope"]:
                    return StreamingResponse(
                        generate_webcam_stream(camera),
                        media_type="multipart/x-mixed-replace; boundary=frame",
                    )

                if camera_type in ["tapo", "onvif"]:
                    stream_url = await camera.get_stream_url()
                    if stream_url:
                        return {"stream_url": stream_url, "type": "rtsp"}

        return {"error": "Camera not found or not supported"}
    except Exception as e:
        return {"error": str(e)}


@router.get("/api/cameras/{camera_id}/mjpeg")
async def get_camera_mjpeg_stream(camera_id: str):
    """Get camera MJPEG stream for browser viewing."""
    if not re.match(r"^[a-zA-Z0-9_-]{1,100}$", camera_id):
        return Response(content="Invalid camera_id format", status_code=400)

    try:
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()

        if hasattr(server, "camera_manager") and server.camera_manager:
            camera = server.camera_manager.cameras.get(camera_id)
            if camera:
                camera_type = camera.config.type
                if hasattr(camera_type, "value"):
                    camera_type = camera_type.value

                # For webcam / USB microscope: proxy to windows_camera_server.py
                # (see scripts/windows_camera_server.py: port 10715, GET /camera/{id}/mjpeg)
                if camera_type in ("webcam", "microscope"):
                    device_id = int(camera.config.params.get("device_id", 0))
                    base = os.environ.get("WINDOWS_CAMERA_SERVER_URL", "http://127.0.0.1:10715").rstrip("/")
                    proxy_url = f"{base}/camera/{device_id}/mjpeg"
                    force_direct = os.environ.get("WEBCAM_MJPEG_FORCE_DIRECT", "").strip().lower() in (
                        "1",
                        "true",
                        "yes",
                        "on",
                    )

                    # Prefer helper when it is running (single capture owner). Otherwise OpenCV in this
                    # process so USB preview still works without start_windows_camera_server / 10715.
                    use_proxy = not force_direct and await _windows_camera_server_has_device(base, device_id)

                    if use_proxy:
                        logger.info(f"Proxying webcam MJPEG for {camera_id} to {proxy_url}")

                        import httpx

                        async def stream_proxy():
                            async with httpx.AsyncClient() as client:
                                try:
                                    async with client.stream("GET", proxy_url, timeout=None) as response:
                                        if response.status_code != 200:
                                            logger.error(
                                                "Webcam proxy failed with status %s",
                                                response.status_code,
                                            )
                                            return
                                        async for chunk in response.aiter_bytes():
                                            yield chunk
                                except Exception:
                                    logger.exception("Error in webcam proxy stream")

                        return StreamingResponse(
                            stream_proxy(),
                            media_type="multipart/x-mixed-replace; boundary=frame",
                            headers={
                                "Cache-Control": "no-cache",
                                "Pragma": "no-cache",
                                "Expires": "0",
                                "Connection": "keep-alive",
                            },
                        )

                    logger.info(
                        "Webcam MJPEG for %s: OpenCV direct (device_id=%s); "
                        "set WEBCAM_MJPEG_FORCE_DIRECT=0 and run USB helper on %s to use proxy",
                        camera_id,
                        device_id,
                        base,
                    )
                    return StreamingResponse(
                        generate_webcam_stream(camera),
                        media_type="multipart/x-mixed-replace; boundary=frame",
                        headers={
                            "Cache-Control": "no-cache",
                            "Pragma": "no-cache",
                            "Expires": "0",
                            "Connection": "keep-alive",
                        },
                    )

                # For RTSP/ONVIF cameras, transcode to MJPEG
                if camera_type in ("tapo", "onvif"):
                    try:
                        # Get stream URL
                        stream_url = await asyncio.wait_for(camera.get_stream_url(), timeout=15.0)
                        if not stream_url:
                            logger.error(f"Failed to get stream URL for {camera_id}")
                            return Response(
                                content=f"Failed to get stream URL for camera {camera_id}",
                                status_code=500,
                            )

                        # Add auth for ONVIF
                        if camera_type == "onvif":
                            from urllib.parse import urlparse

                            parsed = urlparse(stream_url)
                            username = camera.config.params.get("username", "")
                            password = camera.config.params.get("password", "")
                            if username and password:
                                # Rebuild RTSP URL with credentials
                                stream_url = (
                                    f"rtsp://{username}:{password}@{parsed.hostname}:{parsed.port or 554}{parsed.path}"
                                )
                                logger.info(f"ONVIF MJPEG: Added auth for {camera_id}")

                        logger.info(f"Starting MJPEG stream for {camera_id} ({camera_type})")
                        return StreamingResponse(
                            generate_rtsp_mjpeg_stream(stream_url),
                            media_type="multipart/x-mixed-replace; boundary=frame",
                            headers={
                                "Cache-Control": "no-cache",
                                "Connection": "keep-alive",
                            },
                        )
                    except TimeoutError:
                        logger.exception(f"Timeout getting stream for {camera_id}")
                        return Response(content="Stream timeout", status_code=504)
                    except Exception as e:
                        logger.exception(f"Stream error for {camera_id}: {e}")
                        return Response(content=str(e), status_code=500)

        return Response(content="Camera not found", status_code=404)
    except Exception as e:
        logger.exception(f"Error starting MJPEG stream for {camera_id}")
        return Response(content=str(e), status_code=500)


@router.get("/api/cameras/{camera_id}/snapshot")
async def get_camera_snapshot(camera_id: str):
    """Get camera snapshot."""
    if not re.match(r"^[a-zA-Z0-9_-]{1,100}$", camera_id):
        return Response(content="Invalid camera_id format", status_code=400)

    try:
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()

        if hasattr(server, "camera_manager") and server.camera_manager:
            camera = server.camera_manager.cameras.get(camera_id)
            if camera:
                image = await camera.capture_still()
                buffer = io.BytesIO()
                image.save(buffer, format="JPEG", quality=75)
                return Response(content=buffer.getvalue(), media_type="image/jpeg")

        return Response(content="Camera not found", status_code=404)
    except Exception as e:
        return Response(content=f"Error: {e!s}", status_code=500)


@router.post("/api/cameras/{camera_id}/control")
async def control_camera(camera_id: str, action: str = Form(...)):
    """Control camera actions."""
    valid_actions = ["start_stream", "stop_stream", "start_audio", "stop_audio", "snapshot"]
    if action not in valid_actions:
        return JSONResponse({"error": "Invalid action"}, status_code=400)

    try:
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()

        if hasattr(server, "camera_manager") and server.camera_manager:
            camera = server.camera_manager.cameras.get(camera_id)
            if camera:
                if action == "start_stream":
                    url = await camera.get_stream_url()
                    return {"success": True, "stream_url": url}
                if action == "stop_stream":
                    await camera.disconnect()
                    return {"success": True}
                if action == "snapshot":
                    image = await camera.capture_still()
                    buffer = io.BytesIO()
                    image.save(buffer, format="JPEG", quality=75)
                    return Response(content=buffer.getvalue(), media_type="image/jpeg")
                return {"success": True, "message": f"{action} triggered"}

        return {"error": "Camera not found"}
    except Exception as e:
        return {"error": str(e)}
