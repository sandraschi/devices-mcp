"""
Public alerts API: Meteoalarm/Vienna plus indoor air (Netatmo CO₂) when configured.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devices_mcp.integrations.indoor_air_alerts import get_netatmo_co2_alerts
from devices_mcp.integrations.vienna_alerts_client import (
    Alert,
    AlertSeverity,
    AlertType,
    alerts_client,
    summarize_alerts,
)
from devices_mcp.utils import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


async def _merged_active_alerts(use_cache: bool = True) -> list[Alert]:
    """Vienna/Meteoalarm alerts plus Netatmo CO₂ (always evaluated fresh)."""
    base = await alerts_client.get_all_alerts(use_cache=use_cache)
    indoor = await get_netatmo_co2_alerts()
    combined = indoor + base
    combined.sort(key=lambda a: list(AlertSeverity).index(a.severity), reverse=True)
    return combined


class AlertResponse(BaseModel):
    """Single alert response model."""

    id: str
    source: str
    alert_type: str
    severity: str
    severity_color: str
    severity_icon: str
    title: str
    description: str
    region: str
    start_time: str | None
    end_time: str | None
    issued_time: str
    is_active: bool


class AlertsSummaryResponse(BaseModel):
    """Alerts summary for dashboard."""

    total_alerts: int
    highest_severity: str
    highest_severity_color: str
    highest_severity_icon: str
    severity_counts: dict[str, int]
    alerts: list[dict]
    last_updated: str
    status: str  # "ok", "warning", "danger"


class AlertsListResponse(BaseModel):
    """Full list of alerts."""

    alerts: list[dict]
    total: int
    sources: list[str]


@router.get("/summary", response_model=AlertsSummaryResponse)
async def get_alerts_summary():
    """Get a summary of current alerts for dashboard display.

    Returns the top 5 most severe alerts and overall statistics.
    """
    try:
        merged = await _merged_active_alerts(use_cache=True)
        return AlertsSummaryResponse(**summarize_alerts(merged))
    except Exception as e:
        logger.exception("Failed to get alerts summary")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/all", response_model=AlertsListResponse)
async def get_all_alerts(use_cache: bool = True):
    """Get all active alerts.

    Args:
        use_cache: Whether to use cached results (default: True)
    """
    try:
        alerts = await _merged_active_alerts(use_cache=use_cache)
        return AlertsListResponse(
            alerts=[a.to_dict() for a in alerts],
            total=len(alerts),
            sources=list({a.source for a in alerts}),
        )
    except Exception as e:
        logger.exception("Failed to get alerts")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/refresh", response_model=AlertsListResponse)
async def refresh_alerts():
    """Force refresh alerts from all sources (bypasses cache)."""
    try:
        alerts = await _merged_active_alerts(use_cache=False)
        return AlertsListResponse(
            alerts=[a.to_dict() for a in alerts],
            total=len(alerts),
            sources=list({a.source for a in alerts}),
        )
    except Exception as e:
        logger.exception("Failed to refresh alerts")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/types")
async def get_alert_types():
    """Get available alert types."""
    return {
        "types": [{"value": t.value, "name": t.name} for t in AlertType],
    }


@router.get("/severities")
async def get_alert_severities():
    """Get severity levels with colors."""
    from devices_mcp.integrations.vienna_alerts_client import SEVERITY_COLORS, SEVERITY_ICONS

    return {
        "severities": [
            {
                "value": s.value,
                "name": s.name,
                "color": SEVERITY_COLORS[s],
                "icon": SEVERITY_ICONS[s],
            }
            for s in AlertSeverity
        ],
    }
