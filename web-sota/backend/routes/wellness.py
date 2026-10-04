"""Personal wellness endpoints (weight, BP, glucose, workouts).

Manual entry today; vendor sync (Withings OAuth, FTMS BLE) later. Storage is the
shared TimeSeriesDB health_metrics table - the same DB/trend pattern as energy.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devices_mcp.db import TimeSeriesDB

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wellness", tags=["wellness"])

_METRICS = {
    "weight_kg",
    "sys_mmhg",
    "dia_mmhg",
    "pulse_bpm",
    "glucose_mgdl",
    "workout_min",
    "workout_km",
    "workout_kcal",
    "workout_avgbpm",
}

_RANGES = {
    "weight_kg": (20.0, 400.0),
    "sys_mmhg": (50.0, 300.0),
    "dia_mmhg": (30.0, 200.0),
    "pulse_bpm": (20.0, 250.0),
    "glucose_mgdl": (10.0, 1000.0),
    "workout_min": (0.0, 1440.0),
    "workout_km": (0.0, 500.0),
    "workout_kcal": (0.0, 20000.0),
    "workout_avgbpm": (20.0, 250.0),
}


class WellnessLog(BaseModel):
    metric: str
    value: float
    unit: str = ""
    source: str = "manual"
    notes: str = ""


class BpLog(BaseModel):
    systolic: float
    diastolic: float
    pulse: float | None = None
    source: str = "manual"
    notes: str = ""


class WorkoutLog(BaseModel):
    minutes: float
    kind: str = ""
    km: float | None = None
    kcal: float | None = None
    avg_hr: float | None = None
    source: str = "manual"
    notes: str = ""


def _check(metric: str, value: float) -> None:
    bounds = _RANGES.get(metric)
    if bounds and not (bounds[0] <= value <= bounds[1]):
        raise HTTPException(
            status_code=400,
            detail=f"{value} outside plausible range {bounds[0]}-{bounds[1]} for {metric}",
        )


@router.post("/log", summary="Log one metric value")
async def log_metric(entry: WellnessLog) -> dict[str, Any]:
    """Log a single metric (weight_kg, glucose_mgdl, ...)."""
    if entry.metric not in _METRICS:
        raise HTTPException(status_code=400, detail=f"Unknown metric. Use: {sorted(_METRICS)}")
    value = entry.value
    unit = entry.unit
    if entry.metric == "glucose_mgdl" and unit.lower() in ("mmol", "mmol/l"):
        value = value * 18.018
        unit = "mg/dL"
    _check(entry.metric, value)
    db = TimeSeriesDB()
    rid = db.store_health_metric(entry.metric, value, unit, entry.source, entry.notes)
    return {"success": True, "id": rid, "metric": entry.metric, "value": value}


@router.post("/bp", summary="Log blood pressure")
async def log_bp(entry: BpLog) -> dict[str, Any]:
    """Log systolic/diastolic (+ optional pulse)."""
    _check("sys_mmhg", entry.systolic)
    _check("dia_mmhg", entry.diastolic)
    db = TimeSeriesDB()
    ids = [
        db.store_health_metric("sys_mmhg", entry.systolic, "mmHg", entry.source, entry.notes),
        db.store_health_metric("dia_mmhg", entry.diastolic, "mmHg", entry.source, entry.notes),
    ]
    if entry.pulse is not None:
        _check("pulse_bpm", entry.pulse)
        ids.append(db.store_health_metric("pulse_bpm", entry.pulse, "bpm", entry.source, entry.notes))
    return {
        "success": True,
        "ids": ids,
        "systolic": entry.systolic,
        "diastolic": entry.diastolic,
        "pulse": entry.pulse,
    }


@router.post("/workout", summary="Log a workout")
async def log_workout(entry: WorkoutLog) -> dict[str, Any]:
    """Log minutes (+ optional km/kcal/avg HR)."""
    _check("workout_min", entry.minutes)
    db = TimeSeriesDB()
    ids = [db.store_health_metric("workout_min", entry.minutes, "min", entry.source, entry.kind or entry.notes)]
    for metric, val, unit in (
        ("workout_km", entry.km, "km"),
        ("workout_kcal", entry.kcal, "kcal"),
        ("workout_avgbpm", entry.avg_hr, "bpm"),
    ):
        if val is not None:
            _check(metric, val)
            ids.append(db.store_health_metric(metric, val, unit, entry.source, entry.kind or entry.notes))
    return {"success": True, "ids": ids, "minutes": entry.minutes, "kind": entry.kind}


@router.get("/trends", summary="Latest + min/max/avg per metric")
async def wellness_trends(metric: str | None = None, days: int = 90) -> dict[str, Any]:
    """Trend summary over a lookback window."""
    db = TimeSeriesDB()
    rows = db.get_health_history(metric=metric, days=days)
    by_metric: dict[str, list[float]] = {}
    for row in rows:
        by_metric.setdefault(row["metric"], []).append(row["value"])
    summary = {}
    for name, vals in by_metric.items():
        summary[name] = {
            "count": len(vals),
            "latest": vals[-1],
            "min": min(vals),
            "max": max(vals),
            "avg": round(sum(vals) / len(vals), 2),
        }
    return {"success": True, "metrics": summary, "days": days}


@router.get("/list", summary="Raw data points")
async def wellness_list(metric: str | None = None, days: int = 90) -> dict[str, Any]:
    """Data points, newest last (capped at 500)."""
    db = TimeSeriesDB()
    rows = db.get_health_history(metric=metric, days=days)
    return {"success": True, "count": len(rows), "points": rows[-500:]}


@router.delete("/{row_id}", summary="Delete one data point")
async def wellness_delete(row_id: int) -> dict[str, Any]:
    """Delete a mistyped entry by id (see list)."""
    db = TimeSeriesDB()
    if not db.delete_health_metric(row_id):
        raise HTTPException(status_code=404, detail=f"No data point with id {row_id}")
    return {"success": True, "id": row_id}
