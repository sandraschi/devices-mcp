"""Motion detection API for ONVIF cameras."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/motion", tags=["motion"])


class MotionSubscriptionRequest(BaseModel):
    """Request to subscribe to motion events."""

    camera_id: str


@router.get("/status")
async def get_motion_status():
    """Get status of motion detection subscriptions."""
    from devices_mcp.integrations.onvif_events import get_subscription_status

    return await get_subscription_status()


@router.get("/events")
async def get_motion_events(camera_id: Optional[str] = None, limit: int = 20):
    """Get recent motion events."""
    from devices_mcp.integrations.onvif_events import get_recent_events

    events = get_recent_events(camera_id=camera_id, limit=limit)
    return {"events": events, "count": len(events)}


@router.post("/subscribe/{camera_id}")
async def subscribe_to_motion(camera_id: str):
    """Subscribe to motion events from a camera.

    Note: Not all cameras support ONVIF events. Tapo C200 has limited event support.
    """
    from devices_mcp.core.server import DevicesMCPServer
    from devices_mcp.integrations.onvif_events import subscribe_to_camera

    server = await DevicesMCPServer.get_instance()
    camera = await server.camera_manager.get_camera(camera_id)

    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

    # Check if ONVIF camera
    camera_type = camera.config.type
    if hasattr(camera_type, "value"):
        camera_type = camera_type.value

    if camera_type != "onvif":
        raise HTTPException(
            status_code=400,
            detail=f"Camera {camera_id} is not an ONVIF camera. Motion events only supported for ONVIF cameras.",
        )

    # Get camera connection details
    host = camera.config.params.get("host")
    port = camera.config.params.get("onvif_port", 2020)
    username = camera.config.params.get("username")
    password = camera.config.params.get("password")

    if not all([host, username, password]):
        raise HTTPException(status_code=400, detail="Missing camera credentials")

    # Subscribe
    success = await subscribe_to_camera(camera_id, host, port, username, password)

    if success:
        return {
            "success": True,
            "message": f"Subscribed to motion events from {camera_id}",
            "note": "Motion events will be stored and can be retrieved via /api/motion/events",
        }

    return {
        "success": False,
        "message": f"Failed to subscribe to {camera_id}. Camera may not support ONVIF events.",
        "note": "Tapo C200 cameras have limited ONVIF event support. "
        "Consider using the Tapo app for motion notifications.",
    }


@router.post("/unsubscribe/{camera_id}")
async def unsubscribe_from_motion(camera_id: str):
    """Unsubscribe from motion events."""
    from devices_mcp.integrations.onvif_events import unsubscribe_from_camera

    await unsubscribe_from_camera(camera_id)
    return {"success": True, "message": f"Unsubscribed from {camera_id}"}


@router.get("/capabilities")
async def get_motion_capabilities():
    """Get motion detection capabilities for different camera types."""
    return {
        "onvif_cameras": {
            "motion_detection": "Limited",
            "note": "ONVIF event support varies by camera model. Tapo C200 has basic Profile S support.",
            "alternatives": [
                "Use Tapo app for reliable motion notifications",
                "Motion detection via video analytics (future feature)",
                "Integration with Home Assistant for event aggregation",
            ],
        },
        "ring_doorbell": {
            "motion_detection": "Full",
            "note": "Ring provides motion and ding events via API. Already implemented on /alarms page.",
        },
        "tapo_app": {
            "motion_detection": "Full",
            "note": "The Tapo app provides the most reliable motion notifications with customizable zones and sensitivity.",
        },
        "recommendation": "For reliable motion alerts, use the Tapo app alongside this dashboard. "
        "This dashboard focuses on live viewing and camera control.",
    }


@router.post("/test/{camera_id}")
async def test_motion_support(camera_id: str):
    """Test if a camera supports ONVIF events."""
    from devices_mcp.core.server import DevicesMCPServer

    server = await DevicesMCPServer.get_instance()
    camera = await server.camera_manager.get_camera(camera_id)

    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

    # Check camera type
    camera_type = camera.config.type
    if hasattr(camera_type, "value"):
        camera_type = camera_type.value

    result = {
        "camera_id": camera_id,
        "camera_type": camera_type,
        "onvif_events_support": False,
        "details": {},
    }

    if camera_type != "onvif":
        result["note"] = "Not an ONVIF camera - events not supported"
        return result

    # Try to check ONVIF event capabilities
    try:
        import asyncio

        from onvif import ONVIFCamera

        host = camera.config.params.get("host")
        port = camera.config.params.get("onvif_port", 2020)
        username = camera.config.params.get("username")
        password = camera.config.params.get("password")

        loop = asyncio.get_event_loop()

        def check_events():
            cam = ONVIFCamera(host, port, username, password)
            try:
                events_service = cam.create_events_service()
                # Try to get event properties
                props = events_service.GetEventProperties()
                return {
                    "has_events_service": True,
                    "topics": [str(t) for t in getattr(props, "TopicSet", {})][:10]
                    if hasattr(props, "TopicSet")
                    else [],
                }
            except Exception as e:
                return {"has_events_service": False, "error": str(e)}

        details = await loop.run_in_executor(None, check_events)
        result["details"] = details
        result["onvif_events_support"] = details.get("has_events_service", False)

        if result["onvif_events_support"]:
            result["note"] = "Camera supports ONVIF events. You can subscribe to motion events."
        else:
            result["note"] = (
                "Camera does not support ONVIF events. Use Tapo app for motion notifications."
            )

    except Exception as e:
        result["error"] = str(e)
        result["note"] = "Failed to check event support"

    return result
