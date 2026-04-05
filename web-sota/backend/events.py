import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Query, Request

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=Dict[str, Any])
async def get_events(
    request: Request, limit: int = Query(50, ge=1, le=1000), type: Optional[str] = None
):
    """Get system events."""
    server = request.app.state.server
    # events are stored in server.events usually, or a DB.
    # checking server.py logic (recalled from snippet), it returned self.events[-limit:]

    events = getattr(server, "events", [])

    filtered = events
    if type:
        filtered = [e for e in events if e.get("type") == type]

    # Reverse to get newest first usually, or slice
    return {"events": filtered[-limit:], "total": len(events)}


@router.get("/recent")
async def get_recent_events(request: Request):
    """Get very recent events (last 10)."""
    server = request.app.state.server
    events = getattr(server, "events", [])
    return {"events": events[-10:], "count": min(len(events), 10)}


@router.post("")
async def create_event(request: Request, event: Dict[str, Any] = Body(...)):
    """Manually create an event (e.g. from webhook)."""
    server = request.app.state.server

    # Enrich event
    if "timestamp" not in event:
        event["timestamp"] = datetime.now().isoformat()

    if not hasattr(server, "events"):
        server.events = []

    server.events.append(event)

    # Limit size
    if len(server.events) > 1000:
        server.events.pop(0)

    return {"status": "success", "event": event}
