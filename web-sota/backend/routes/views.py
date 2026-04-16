import asyncio
import logging
from datetime import datetime, timedelta

import psutil
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter()

AUTO_WEBCAM_RETRY_INTERVAL = timedelta(seconds=10)
_last_webcam_attempt: datetime | None = None


@router.get("/", response_class=HTMLResponse, name="dashboard")
async def index_page(request: Request):
    """Serve the main dashboard page."""
    templates = getattr(request.app.state, "templates", None)
    if templates is None:
        return HTMLResponse(
            content="<h1>Server misconfiguration</h1><p>Templates not loaded. Check backend/server.py and templates directory.</p>",
            status_code=500,
        )

    # Initialize variables to avoid undefined errors in template
    cameras = []
    online_cameras = 0
    total_cameras = 0
    security_devices = []
    security_alerts = []
    security_overview = {}

    try:
        # Get real camera data from the MCP server
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()

        # Load camera list and security data in parallel
        camera_task = asyncio.wait_for(server.camera_manager.list_cameras(), timeout=5.0)

        # Prepare security data loading task
        security_task = None
        try:
            from devices_mcp.security import security_manager

            # Use app state or global manager
            if not hasattr(security_manager, "_initialized"):
                # Configuration is normally handled at startup
                pass

            # Create security data loading task with timeout
            security_task = asyncio.wait_for(
                asyncio.gather(
                    security_manager.get_all_devices(),
                    security_manager.get_all_alerts(),
                    security_manager.get_system_overview(),
                    return_exceptions=True,
                ),
                timeout=5.0,
            )
        except Exception as e:
            logger.warning(f"Failed to prepare security data: {e}")

        # Wait for camera data
        cameras = await camera_task
        total_cameras = len(cameras)
        online_cameras = sum(1 for cam in cameras if cam.get("status") == "online")

        # Wait for security data if task was created
        if security_task:
            try:
                sec_devices, sec_alerts, sec_overview = await security_task
                security_devices = sec_devices if not isinstance(sec_devices, Exception) else []
                security_alerts = sec_alerts if not isinstance(sec_alerts, Exception) else []
                security_overview = sec_overview if not isinstance(sec_overview, Exception) else {}
            except Exception as e:
                logger.warning(f"Failed to load security data: {e}")

        # If no cameras configured, try to auto-add USB webcam
        if total_cameras == 0 and server:
            try:
                global _last_webcam_attempt
                now = datetime.utcnow()
                if _last_webcam_attempt is None or now - _last_webcam_attempt >= AUTO_WEBCAM_RETRY_INTERVAL:
                    _last_webcam_attempt = now
                    logger.info("Auto-adding USB webcam...")
                    config = {
                        "name": "usb_webcam_0",
                        "type": "webcam",
                        "params": {"device_id": 0},
                    }
                    success = await asyncio.wait_for(server.camera_manager.add_camera(config), timeout=5.0)
                    if success:
                        cameras = await asyncio.wait_for(server.camera_manager.list_cameras(), timeout=5.0)
                        total_cameras = len(cameras)
                        online_cameras = sum(1 for cam in cameras if cam.get("status") == "online")
            except Exception as e:
                logger.warning(f"Error auto-adding webcam: {e}")

    except Exception as e:
        logger.exception(f"Dashboard data error: {e}")

    # System metrics
    try:
        import os

        _root = os.path.abspath(os.sep) if os.name != "nt" else (os.environ.get("SystemDrive", "C:") + os.sep)
        disk = psutil.disk_usage(_root)
        storage_used = round(disk.percent, 1)

        system_status = {
            "cpu_usage": round(psutil.cpu_percent(interval=0.1), 1),
            "memory_usage": round(psutil.virtual_memory().percent, 1),
            "disk_usage": storage_used,
            "network": {"upload": 0.0, "download": 0.0},
        }

        try:
            net_io = psutil.net_io_counters()
            system_status["network"]["upload"] = round(net_io.bytes_sent / (1024 * 1024), 2)
            system_status["network"]["download"] = round(net_io.bytes_recv / (1024 * 1024), 2)
        except Exception:
            pass
    except Exception:
        storage_used = 0
        system_status = {
            "cpu_usage": 0,
            "memory_usage": 0,
            "disk_usage": 0,
            "network": {"upload": 0, "download": 0},
        }

    def safe_serialize(obj):
        if hasattr(obj, "dict"):
            return obj.dict()
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return obj if isinstance(obj, dict) else str(obj)

    try:
        return templates.TemplateResponse(
            "simple_dashboard.html",
            {
                "request": request,
                "active_page": "dashboard",
                "online_cameras": online_cameras,
                "total_cameras": total_cameras,
                "storage_used": storage_used,
                "active_alerts": len(security_alerts),
                "active_recordings": 0,
                "cameras": cameras,
                "security_devices": [safe_serialize(d) for d in security_devices],
                "security_alerts": [safe_serialize(a) for a in security_alerts],
                "security_overview": security_overview or {},
                "system_status": system_status,
                "title": "Home - Devices MCP",
            },
        )
    except Exception as e:
        logger.exception("Index page render failed: %s", e)
        return HTMLResponse(
            content=f"<h1>Error rendering dashboard</h1><pre>{type(e).__name__}: {e}</pre>",
            status_code=500,
        )


@router.get("/cameras", response_class=HTMLResponse, name="cameras")
async def cameras_page(request: Request):
    """Serve the cameras page."""
    templates = request.app.state.templates
    cameras = []
    online_cameras = 0
    total_cameras = 0
    load_error = None
    try:
        from devices_mcp.core.server import DevicesMCPServer

        # Prevent route timeout from cancelling shared server initialization.
        server = await asyncio.wait_for(
            asyncio.shield(DevicesMCPServer.get_instance()),
            timeout=10.0,
        )
        cameras = await asyncio.wait_for(server.camera_manager.list_cameras(), timeout=10.0)
        total_cameras = len(cameras)
        online_cameras = sum(1 for c in cameras if c.get("status") == "online")
    except TimeoutError as e:
        load_error = "Device server is still starting. Wait a moment and refresh the page."
        logger.warning("Cameras page: timeout waiting for server: %s", e)
    except Exception as e:
        load_error = "Could not load camera list. Restart the dashboard and refresh; check server log for errors."
        logger.warning("Cameras page data: %s", e, exc_info=True)
    return templates.TemplateResponse(
        "cameras.html",
        {
            "request": request,
            "title": "Cameras - Devices MCP",
            "cameras": cameras,
            "online_cameras": online_cameras,
            "total_cameras": total_cameras,
            "load_error": load_error,
        },
    )


@router.get("/settings", response_class=HTMLResponse, name="settings")
async def settings_page(request: Request):
    """Serve the settings page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "title": "Settings - Devices MCP",
        },
    )


@router.get("/health", response_class=HTMLResponse)
async def health_page(request: Request):
    """Serve the health monitoring page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "health.html",
        {
            "request": request,
            "title": "System Health - Devices MCP",
        },
    )


@router.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page(request: Request):
    """Serve the onboarding page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "onboarding.html",
        {
            "request": request,
            "title": "Onboarding - Devices MCP",
        },
    )


@router.get("/energy", response_class=HTMLResponse)
async def energy_page(request: Request):
    """Serve the energy management page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "energy.html",
        {
            "request": request,
            "title": "Energy Management - Devices MCP",
        },
    )


@router.get("/events", response_class=HTMLResponse, name="events")
async def events_page(request: Request):
    """Serve the events history page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "events.html",
        {
            "request": request,
            "title": "Event History - Devices MCP",
        },
    )


@router.get("/recordings", response_class=HTMLResponse, name="recordings")
async def recordings_page(request: Request):
    """Serve the recordings page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "recordings.html",
        {
            "request": request,
            "title": "Recordings - Devices MCP",
        },
    )


@router.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    """Serve the logs viewer page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "log_management.html",
        {
            "request": request,
            "title": "Log Viewer - Devices MCP",
        },
    )


@router.get("/alarms", response_class=HTMLResponse)
async def alarms_page(request: Request):
    """Serve the alarm management page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "alarms.html",
        {
            "request": request,
            "title": "Alarms & Notifications - Devices MCP",
        },
    )


@router.get("/lighting", response_class=HTMLResponse)
async def lighting_page(request: Request):
    """Serve the lighting control dashboard page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "lighting.html",
        {
            "request": request,
            "title": "Lighting Control - Devices MCP",
        },
    )


@router.get("/cameras/{camera_id}/view", response_class=HTMLResponse)
async def stream_viewer_page(request: Request, camera_id: str):
    """Serve the stream viewer page for a camera."""
    templates = request.app.state.templates

    # Get camera name if possible
    camera_name = camera_id
    try:
        from devices_mcp.core.server import DevicesMCPServer

        server = await DevicesMCPServer.get_instance()
        if hasattr(server, "camera_manager"):
            camera = server.camera_manager.cameras.get(camera_id)
            if camera:
                camera_name = camera.config.name
    except Exception:
        pass

    return templates.TemplateResponse(
        "stream_viewer.html",
        {
            "request": request,
            "camera_id": camera_id,
            "camera_name": camera_name,
            "title": f"Live View: {camera_name} - Devices MCP",
        },
    )


@router.get("/plex", response_class=HTMLResponse, name="plex")
async def plex_page(request: Request):
    """Serve the Plex Media page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "plex.html",
        {
            "request": request,
            "title": "Plex Media - Devices MCP",
        },
    )


@router.get("/weather", response_class=HTMLResponse)
async def weather_page(request: Request):
    """Serve the weather page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "weather.html",
        {
            "request": request,
            "active_page": "weather",
            "title": "Weather - Devices MCP",
        },
    )


@router.get("/ring", response_class=HTMLResponse)
async def ring_page(request: Request):
    """Serve the Ring doorbell page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "ring.html",
        {
            "request": request,
            "active_page": "ring",
            "title": "Ring - Devices MCP",
        },
    )


@router.get("/nest", response_class=HTMLResponse)
async def nest_page(request: Request):
    """Serve the Nest thermostat page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "nest.html",
        {
            "request": request,
            "active_page": "nest",
            "title": "Nest - Devices MCP",
        },
    )


@router.get("/robots", response_class=HTMLResponse)
async def robots_page(request: Request):
    """Serve the Robots/Vacuum page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "robots.html",
        {
            "request": request,
            "active_page": "robots",
            "title": "Robots - Devices MCP",
        },
    )


@router.get("/robots/dreame-d20", response_class=HTMLResponse)
async def dreame_d20_page(request: Request):
    """Serve the Dreame D20 Pro dashboard page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "dreame-d20.html",
        {
            "request": request,
            "active_page": "robots",
            "title": "Dreame D20 Pro - Devices MCP",
        },
    )


@router.get("/robots/yahboom", response_class=HTMLResponse)
async def yahboom_page(request: Request):
    """Serve the Yahboom ROS 2 dashboard page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "yahboom.html",
        {
            "request": request,
            "active_page": "robots",
            "title": "Yahboom ROS 2 - Devices MCP",
        },
    )


@router.get("/security", response_class=HTMLResponse)
async def security_page(request: Request):
    """Serve the Security page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "security.html",
        {
            "request": request,
            "active_page": "security",
            "title": "Security - Devices MCP",
        },
    )


@router.get("/storage", response_class=HTMLResponse)
async def storage_page(request: Request):
    """Serve the Storage page."""
    templates = request.app.state.templates
    # Using a generic dashboard for storage if specific one missing, or dashboard itself
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "storage",
            "title": "Storage - Devices MCP",
        },
    )


@router.get("/system-info", response_class=HTMLResponse)
async def system_info_page(request: Request):
    """Serve the System Info page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "system_info.html",
        {
            "request": request,
            "active_page": "system",
            "title": "System Information - Devices MCP",
        },
    )


@router.get("/help", response_class=HTMLResponse, name="help")
async def help_page(request: Request):
    """Serve the Help page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "help.html",
        {
            "request": request,
            "active_page": "help",
            "title": "Help - Devices MCP",
        },
    )


@router.get("/vienna-webcams", response_class=HTMLResponse)
async def vienna_webcams_page(request: Request):
    """Serve the Vienna Webcams page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "vienna_webcams.html",
        {
            "request": request,
            "active_page": "webcams",
            "title": "Vienna Webcams - Devices MCP",
        },
    )


@router.get("/kitchen", response_class=HTMLResponse)
async def kitchen_page(request: Request):
    """Serve the Kitchen devices page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "kitchen.html",
        {
            "request": request,
            "active_page": "kitchen",
            "title": "Kitchen - Devices MCP",
        },
    )


@router.get("/appliance-monitor", response_class=HTMLResponse)
async def appliance_monitor_page(request: Request):
    """Serve the Appliance Monitor page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "appliance_monitor.html",
        {
            "request": request,
            "active_page": "appliances",
            "title": "Appliance Monitor - Devices MCP",
        },
    )
