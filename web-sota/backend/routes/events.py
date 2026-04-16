"""
Device and automation event log API (JSONL-backed, same store as ingestion tools).

Storage: ``DEVICES_MCP_EVENTS_DIR`` or ``<cwd>/data/events/events.jsonl`` (see EventStore).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["events"])


def _store():
    from devices_mcp.utils.storage import EventStore

    return EventStore()


class EventCreate(BaseModel):
    """POST /api/events body."""

    type: str = Field(..., min_length=1, max_length=128, description="Event type key")
    message: str = ""
    camera_id: str | None = Field(None, max_length=256)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = Field(
        "api",
        max_length=64,
        description="Origin: api, mcp, supervisor, ring, tapo, etc.",
    )


class EventsListResponse(BaseModel):
    events: list[dict[str, Any]]
    total: int
    limit: int
    offset: int
    storage_path: str


@router.get("/api/events", response_model=EventsListResponse)
async def get_events(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=100_000),
    event_type: str | None = Query(None, description="Filter by type"),
    camera_id: str | None = Query(None, description="Filter by camera / device id"),
    source: str | None = Query(None, description="Filter by source"),
    hours: int = Query(24, ge=1, le=168, description="Only events newer than now - hours"),
    until_hours_ago: int | None = Query(
        None,
        ge=0,
        le=168,
        description="Optional upper bound: events older than this many hours (sliding window)",
    ),
):
    """List events with filters and pagination (newest first)."""
    store = _store()
    since = datetime.now(UTC) - timedelta(hours=hours)
    until: datetime | None = None
    if until_hours_ago is not None:
        until = datetime.now(UTC) - timedelta(hours=until_hours_ago)

    try:
        events = store.get_events(
            limit=limit,
            offset=offset,
            event_type=event_type,
            camera_id=camera_id,
            since=since,
            until=until,
            source=source,
        )
        # Total matching without offset (for UI): approximate via stats + filter is expensive;
        # return full count for same filters with a second bounded read.
        all_for_count = store.get_events(
            limit=500_000,
            offset=0,
            event_type=event_type,
            camera_id=camera_id,
            since=since,
            until=until,
            source=source,
        )
        total_matching = len(all_for_count)
    except OSError as e:
        logger.exception("Error reading events")
        raise HTTPException(status_code=500, detail=str(e)) from e

    return {
        "events": events,
        "total": total_matching,
        "limit": limit,
        "offset": offset,
        "storage_path": str(store.events_file),
    }


@router.get("/api/events/recent")
async def get_recent_events(
    limit: int = Query(50, ge=1, le=200),
):
    """Recent events (newest first), no time window filter."""
    store = _store()
    try:
        events = store.get_events(limit=limit, offset=0)
        return {
            "events": events,
            "total": len(events),
            "storage_path": str(store.events_file),
        }
    except OSError as e:
        logger.exception("Error fetching recent events")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/events/stats")
async def get_event_stats():
    """Aggregates for dashboards."""
    store = _store()
    try:
        return {"success": True, **store.stats(), "types": store.distinct_types()}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/events/types")
async def get_event_types():
    """Distinct event type values present in the log."""
    store = _store()
    try:
        return {"types": store.distinct_types()}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/events/{event_id}")
async def get_event(event_id: str):
    """Fetch one event by id."""
    store = _store()
    ev = store.get_event_by_id(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail="Event not found")
    return ev


@router.post("/api/events", response_model=dict)
async def create_event(body: EventCreate):
    """Append a new event (ingestion, webhooks, or manual)."""
    store = _store()
    try:
        event = store.add_event(
            event_type=body.type,
            camera_id=body.camera_id,
            message=body.message,
            metadata=body.metadata,
            source=body.source,
        )
        return {"success": True, "event": event}
    except OSError as e:
        logger.exception("Error creating event")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/api/events/{event_id}")
async def delete_event(event_id: str):
    """Remove a single event by id."""
    store = _store()
    if store.delete_event(event_id):
        return {"success": True, "deleted": event_id}
    raise HTTPException(status_code=404, detail="Event not found")


@router.post("/api/events/purge")
async def purge_old_events(
    days: int = Query(30, ge=1, le=3650, description="Delete events older than this many days"),
):
    """Rewrite storage without rows older than the cutoff (UTC)."""
    store = _store()
    try:
        removed = store.clear_old_events(days=days)
        return {"success": True, "removed": removed, "older_than_days": days}
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
