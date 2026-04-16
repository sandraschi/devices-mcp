"""
Messages API endpoints for alert/notification system.

Provides REST API for querying alerts, acknowledging messages,
and exporting metrics for Prometheus.
"""

import logging
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from devices_mcp.core.messaging_service import (
    MessageCategory,
    MessageSeverity,
    get_messaging_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/messages", tags=["messages"])


class AcknowledgeRequest(BaseModel):
    """Request to acknowledge messages."""

    message_ids: list[str] | None = None
    severity: str | None = None  # Acknowledge all of this severity
    acknowledge_all: bool = False


@router.get("/")
async def get_messages(
    severity: str | None = Query(None, description="Filter by severity (info, warning, alarm)"),
    category: str | None = Query(None, description="Filter by category"),
    source: str | None = Query(None, description="Filter by source device"),
    since_minutes: int = Query(60, description="Messages from last N minutes"),
    limit: int = Query(100, description="Max messages to return"),
    unacknowledged_only: bool = Query(False, description="Only unacknowledged messages"),
) -> dict[str, Any]:
    """
    Get messages with optional filtering.

    Query Parameters:
    - severity: info, warning, or alarm
    - category: device_connection, device_status, sensor_reading, etc.
    - source: Device ID
    - since_minutes: Only messages from last N minutes
    - limit: Max messages
    - unacknowledged_only: Only unacknowledged
    """
    try:
        messaging = get_messaging_service()

        from datetime import datetime, timedelta

        since = datetime.now() - timedelta(minutes=since_minutes)

        sev = MessageSeverity(severity) if severity else None
        cat = MessageCategory(category) if category else None
        ack = False if unacknowledged_only else None

        messages = messaging.get_messages(
            severity=sev, category=cat, source=source, since=since, limit=limit, acknowledged=ack
        )

        return {"count": len(messages), "messages": [m.to_dict() for m in messages]}

    except Exception as e:
        logger.exception("Error getting messages")
        return {"count": 0, "messages": [], "error": str(e)}


@router.get("/alarms")
async def get_unacknowledged_alarms() -> dict[str, Any]:
    """Get all unacknowledged ALARM messages."""
    try:
        messaging = get_messaging_service()
        alarms = messaging.get_unacknowledged_alarms()

        return {"count": len(alarms), "alarms": [m.to_dict() for m in alarms]}
    except Exception as e:
        logger.exception("Error getting alarms")
        return {"count": 0, "alarms": [], "error": str(e)}


@router.post("/acknowledge")
async def acknowledge_messages(request: AcknowledgeRequest) -> dict[str, Any]:
    """
    Acknowledge one or more messages.

    Body:
    - message_ids: List of message IDs to ack
    - severity: Ack all of this severity (info, warning, alarm)
    - acknowledge_all: Ack everything
    """
    try:
        messaging = get_messaging_service()
        count = 0

        if request.acknowledge_all:
            count = messaging.acknowledge_all()
        elif request.severity:
            sev = MessageSeverity(request.severity)
            count = messaging.acknowledge_all(severity=sev)
        elif request.message_ids:
            for msg_id in request.message_ids:
                if messaging.acknowledge_message(msg_id):
                    count += 1

        return {"success": True, "acknowledged_count": count}
    except Exception as e:
        logger.exception("Error acknowledging messages")
        return {"success": False, "error": str(e)}


@router.get("/metrics")
async def get_message_metrics() -> dict[str, Any]:
    """Get messaging metrics for monitoring."""
    try:
        messaging = get_messaging_service()
        return messaging.get_metrics()
    except Exception as e:
        logger.exception("Error getting message metrics")
        return {"error": str(e)}


@router.get("/prometheus")
async def get_prometheus_metrics() -> str:
    """
    Export metrics in Prometheus text format.

    Scrape this endpoint with Prometheus:
    ```yaml
    scrape_configs:
      - job_name: 'devices_mcp'
        static_configs:
          - targets: ['localhost:7777']
        metrics_path: '/api/messages/prometheus'
    ```
    """
    try:
        messaging = get_messaging_service()
        return messaging.export_prometheus_metrics()
    except Exception as e:
        logger.exception("Error exporting Prometheus metrics")
        return f"# Error: {e}\n"
