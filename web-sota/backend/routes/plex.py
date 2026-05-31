"""
Plex Webhook API endpoints and state management.
"""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from devices_mcp.core.messaging_service import MessageCategory, get_messaging_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/plex", tags=["plex"])

# In-memory store for current media state
_now_playing_state = {
    "active": False,
    "event": None,
    "user": None,
    "player": None,
    "media": None,
    "timestamp": None,
    "metadata": {},
}


@router.post("/webhook")
async def plex_webhook(request: Request):
    """
    Handle Plex webhook POST request.
    Plex sends data as multipart/form-data with a 'payload' field containing JSON.
    """
    try:
        # Plex sends a multipart/form-data request with a 'payload' field
        logger.info("Plex webhook received")
        payload_str = None

        # Check content type to determine how to parse the request
        content_type = request.headers.get("content-type", "").lower()

        if "multipart/form-data" in content_type:
            # Handle multipart/form-data (standard Plex format)
            try:
                form_data = await request.form()
                logger.info(f"Form data keys: {list(form_data.keys()) if form_data else 'None'}")
                payload_str = form_data.get("payload")
            except Exception as form_error:
                logger.warning(f"Failed to parse multipart form data: {form_error}")
        elif "application/json" in content_type:
            # Handle raw JSON (for testing/alternative clients)
            try:
                body = await request.body()
                logger.info(f"Raw body length: {len(body) if body else 0}")
                payload_str = body.decode("utf-8") if body else None
            except Exception as json_error:
                logger.warning(f"Failed to parse JSON body: {json_error}")
        else:
            # Try both methods as fallback
            try:
                form_data = await request.form()
                payload_str = form_data.get("payload")
            except:
                try:
                    body = await request.body()
                    payload_str = body.decode("utf-8") if body else None
                except:
                    pass

        logger.info(f"Payload string: {payload_str}")

        if not payload_str:
            logger.warning("Plex webhook received with no payload")
            raise HTTPException(status_code=400, detail="No payload found in request")

        payload = json.loads(payload_str)

        event = payload.get("event")
        user = payload.get("Account", {}).get("title")
        player = payload.get("Player", {}).get("title")
        metadata = payload.get("Metadata", {})
        media_title = metadata.get("title")

        # Update global state
        global _now_playing_state
        _now_playing_state.update(
            {
                "active": event in ["media.play", "media.resume"],
                "event": event,
                "user": user,
                "player": player,
                "media": media_title,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata,
            }
        )

        # Log to tapo_mcp.log
        logger.info(f"Plex Event: {event} | User: {user} | Player: {player} | Media: {media_title}")

        # Record in MessagingService for UI timeline (optional)
        try:
            messaging = get_messaging_service()
            if messaging:
                messaging.info(
                    category=MessageCategory.MEDIA_EVENT,
                    source=f"Plex:{player or 'Unknown'}",
                    title=f"Media {event.split('.')[-1].capitalize()}",
                    description=f"{user or 'Someone'} is {event.split('.')[-1]}ing '{media_title}' on {player or 'a player'}.",
                    details={
                        "event": event,
                        "user": user,
                        "player": player,
                        "media": media_title,
                        "metadata": metadata,
                    },
                )
        except Exception as e:
            logger.warning(f"Failed to record Plex event in messaging service: {e}")

        return {"status": "success", "event": event}

    except json.JSONDecodeError as e:
        logger.exception(f"Failed to decode Plex webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from e
    except Exception as e:
        logger.exception(f"Error processing Plex webhook: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}") from e


@router.get("/now-playing")
async def get_now_playing():
    """
    Get the current media being played.
    """
    return _now_playing_state


@router.get("/status")
async def get_plex_status():
    """
    Get current Plex integration status.
    """
    return {
        "status": "Plex webhook listener active",
        "last_event": _now_playing_state.get("event"),
        "active_stream": _now_playing_state.get("active"),
    }
