import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from devices_mcp.auth import get_current_user, is_auth_enabled
from devices_mcp.mcp_client import call_mcp_tool
from devices_mcp.utils.storage import EventStore, RecordingStore

from ..templates_manager import templates

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/login", response_class=HTMLResponse, name="login")
async def login_page(request: Request):
    """Serve the login page."""
    # If already logged in, redirect to dashboard
    if is_auth_enabled() and get_current_user(request):
        return RedirectResponse(url="/", status_code=302)
    # If auth disabled, redirect to dashboard
    if not is_auth_enabled():
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/lighting", response_class=HTMLResponse, name="lighting")
async def lighting_page(request: Request):
    """Serve the lighting control dashboard page."""
    logger.info("Lighting page requested")
    try:
        return templates.TemplateResponse(
            "lighting.html",
            {
                "request": request,
                "title": "Lighting Control - Devices MCP",
                "description": "Control Philips Hue lights, groups, and scenes",
            },
        )
    except Exception as e:
        logger.exception(f"Error rendering lighting template: {e}")
        raise


@router.get("/logs", response_class=HTMLResponse, name="logs")
async def log_management_page(request: Request):
    """Serve the log management dashboard page."""
    logger.info("Log management page requested")
    return templates.TemplateResponse(
        "log_management.html",
        {
            "request": request,
            "title": "Log Management - Devices MCP",
            "description": "Monitor and manage application log files",
        },
    )


@router.get("/onboarding", response_class=HTMLResponse, name="onboarding")
async def onboarding_page(request: Request):
    """Serve the onboarding dashboard page."""
    return templates.TemplateResponse(
        "onboarding.html",
        {
            "request": request,
            "title": "Device Onboarding - Devices MCP",
            "description": "Set up your Tapo P115 smart plugs, Nest Protect devices, Ring alarms, and USB webcams",
        },
    )


@router.get("/energy", response_class=HTMLResponse, name="energy")
async def energy_page(request: Request):
    """Serve the energy management dashboard page."""
    return templates.TemplateResponse(
        "energy.html",
        {
            "request": request,
            "title": "Energy Management - Devices MCP",
            "description": "Monitor and control Tapo P115 smart plugs with energy consumption tracking",
        },
    )


@router.get("/alarms", response_class=HTMLResponse, name="alarms")
async def alarms_page(request: Request):
    """Serve the alarms dashboard page."""
    return templates.TemplateResponse(
        "alarms.html",
        {
            "request": request,
            "title": "Security Alarms - Devices MCP",
            "description": "Monitor Nest Protect and Ring security devices",
        },
    )


@router.get("/stream/{camera_id}", response_class=HTMLResponse, name="stream_viewer")
async def stream_viewer_page(request: Request, camera_id: str):
    """Serve the stream viewer page for a camera."""
    custom_name = None
    camera_type = "unknown"

    try:
        from backend.api.camera_names import get_display_name

        display_info = await get_display_name(camera_id)
        custom_name = display_info.get("custom_name")
        camera_type = display_info.get("type", "unknown")
    except Exception as e:
        logger.debug(f"Could not get custom name for camera {camera_id}: {e}")

    # If we couldn't get type from display info, try to get it from MCP
    if camera_type == "unknown":
        try:
            result = await call_mcp_tool("camera_management", {"action": "info", "camera_name": camera_id})
            if result.get("success") and result.get("data"):
                camera_type = result["data"].get("type", "unknown")
        except Exception as e:
            logger.debug(f"Could not get camera type for {camera_id}: {e}")

    display_name = custom_name or camera_id.replace("_", " ").title()

    return templates.TemplateResponse(
        "stream_viewer.html",
        {
            "request": request,
            "title": f"{display_name} Stream - Devices MCP",
            "camera_id": camera_id,
            "camera_name": display_name,
            "camera_type": camera_type,
            "custom_name": custom_name,
        },
    )


@router.get("/appliance-monitor", response_class=HTMLResponse, name="appliance_monitor")
async def appliance_monitor_page(request: Request):
    """Serve the appliance monitoring dashboard page."""
    return templates.TemplateResponse(
        "appliance_monitor.html",
        {
            "request": request,
            "active_page": "appliance_monitor",
            "title": "Appliance Monitor - Devices MCP",
            "description": "Monitor appliance health through power consumption patterns",
        },
    )


@router.get("/weather", response_class=HTMLResponse, name="weather")
async def weather_page(request: Request):
    """Serve the weather monitoring dashboard page."""
    return templates.TemplateResponse(
        "weather.html",
        {
            "request": request,
            "active_page": "weather",
            "title": "Weather Monitoring - Devices MCP",
            "description": "Monitor Netatmo weather stations with temperature, humidity, CO2, and environmental data",
        },
    )


@router.get("/kitchen", response_class=HTMLResponse, name="kitchen")
async def kitchen_page(request: Request):
    """Serve the kitchen appliances dashboard page."""
    return templates.TemplateResponse(
        "kitchen.html",
        {
            "request": request,
            "title": "Kitchen - Devices MCP",
            "description": "Control and monitor kitchen appliances",
        },
    )


@router.get("/vienna-webcams", response_class=HTMLResponse, name="vienna_webcams")
async def vienna_webcams_page(request: Request):
    """Serve the Vienna public webcams dashboard page."""
    return templates.TemplateResponse(
        "vienna_webcams.html",
        {
            "request": request,
            "title": "Vienna Public Webcams - Devices MCP",
            "description": "Live views of Vienna landmarks and weather monitoring cameras",
        },
    )


@router.get("/robots", response_class=HTMLResponse, name="robots")
async def robots_page(request: Request):
    """Serve the robots dashboard page."""
    return templates.TemplateResponse(
        "robots.html",
        {
            "request": request,
            "title": "Robots - Devices MCP",
            "description": "Control and monitor robot vacuums and other robots",
        },
    )


@router.get("/ring", response_class=HTMLResponse, name="ring")
async def ring_page(request: Request):
    """Serve the Ring doorbell dashboard page."""
    return templates.TemplateResponse(
        "ring.html",
        {
            "request": request,
            "active_page": "ring",
            "title": "Ring Doorbell - Devices MCP",
            "description": "Monitor and control your Ring doorbell and alarm system",
        },
    )


@router.get("/nest", response_class=HTMLResponse, name="nest")
async def nest_page(request: Request):
    """Serve the Nest Protect dashboard page."""
    return templates.TemplateResponse(
        "nest.html",
        {
            "request": request,
            "active_page": "nest",
            "title": "Nest Protect - Devices MCP",
            "description": "Monitor fire and CO alarms from your Nest Protect devices",
        },
    )


@router.get("/", response_class=HTMLResponse, name="dashboard")
async def index(request: Request):
    """Serve the main dashboard page."""
    cameras = []
    online_cameras = 0
    total_cameras = 0
    security_devices = []
    security_alerts = []
    security_overview = {}
    recent_events = []

    # Try to load recent events via EventStore
    try:
        event_store = EventStore()
        recent_events = event_store.get_events(limit=10)
    except Exception as e:
        logger.warning(f"Failed to load recent events: {e}")
        recent_events = []

    try:
        # Get camera list from MCP
        result = await call_mcp_tool("camera_management", {"action": "list"})
        if result.get("success"):
            cameras = result.get("data", [])
            total_cameras = len(cameras)
            online_cameras = sum(1 for cam in cameras if cam.get("status") == "online")

            if len(cameras) == 0:
                # No cameras configured, try to auto-add USB webcam
                logger.info("No cameras configured, attempting to auto-add USB webcam for dashboard...")

                try:
                    add_result = await call_mcp_tool(
                        "camera_management",
                        {
                            "action": "add",
                            "camera_name": "usb_webcam_0",
                            "camera_type": "webcam",
                            "host": None,
                            "username": None,
                            "password": None,
                        },
                    )
                    if add_result.get("success"):
                        # Refresh camera count
                        result = await call_mcp_tool("camera_management", {"action": "list"})
                        if result.get("success"):
                            cameras = result.get("data", [])
                            total_cameras = len(cameras)
                            online_cameras = sum(1 for cam in cameras if cam.get("status") == "online")
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Dashboard camera data check issues: {e}, but dashboard loads anyway")

    # System status - simplified for immediate loading
    system_status = {
        "cpu_usage": 0,
        "memory_usage": 0,
        "disk_usage": 0,
        "network": {
            "upload": 0.0,
            "download": 0.0,
        },
    }

    # Safely serialize security devices and alerts
    def safe_serialize(obj):
        """Safely convert object to dict."""
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        if hasattr(obj, "dict"):
            return obj.dict()
        if isinstance(obj, dict):
            return obj
        return str(obj)

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "active_page": "dashboard",
            "online_cameras": online_cameras,
            "total_cameras": total_cameras,
            "storage_used": 0,
            "active_alerts": len(security_alerts),
            "active_recordings": 0,
            "cameras": cameras,
            "security_devices": [safe_serialize(device) for device in security_devices],
            "security_alerts": [safe_serialize(alert) for alert in security_alerts],
            "security_overview": security_overview or {},
            "system_status": system_status,
            "recent_events": recent_events,
        },
    )


@router.get("/list_cameras", response_class=HTMLResponse, name="list_cameras")
async def list_cameras(request: Request):
    """Serve the cameras list page."""
    return templates.TemplateResponse("dashboard.html", {"request": request, "active_page": "cameras"})


@router.get("/recordings", response_class=HTMLResponse, name="recordings")
async def recordings(request: Request):
    """Serve the recordings page."""
    try:
        from datetime import datetime

        recording_store = RecordingStore()
        stats = recording_store.get_storage_stats()
        recordings_list = recording_store.get_recordings(limit=50)

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_recordings = [r for r in recordings_list if datetime.fromisoformat(r.get("timestamp", "")) >= today]

        total_gb = stats.get("total_size_gb", 0)
        storage_free = f"{max(0, 100 - total_gb):.2f}GB"

        return templates.TemplateResponse(
            "recordings.html",
            {
                "request": request,
                "active_page": "recordings",
                "recordings": recordings_list,
                "total_recordings": stats.get("total_recordings", 0),
                "today_recordings": len(today_recordings),
                "storage_used": 0,
                "storage_free": storage_free,
            },
        )
    except Exception as e:
        logger.exception("Error loading recordings page")
        return templates.TemplateResponse(
            "recordings.html",
            {
                "request": request,
                "active_page": "recordings",
                "recordings": [],
                "total_recordings": 0,
                "today_recordings": 0,
                "storage_used": "0GB",
                "storage_free": "0GB",
                "error": str(e),
            },
        )


@router.get("/events", response_class=HTMLResponse, name="events")
async def events(request: Request):
    """Serve the events page."""
    try:
        event_store = EventStore()
        recent_events = event_store.get_events(limit=50)

        return templates.TemplateResponse(
            "events.html",
            {
                "request": request,
                "active_page": "events",
                "title": "System Events - Devices MCP",
                "events": recent_events,
            },
        )
    except Exception as e:
        logger.exception(f"Error serving events page: {e}")
        return templates.TemplateResponse(
            "events.html",
            {
                "request": request,
                "active_page": "events",
                "title": "System Events - Devices MCP",
                "events": [],
                "error": str(e),
            },
        )
