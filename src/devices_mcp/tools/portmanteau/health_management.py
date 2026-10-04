"""Health Management Portmanteau Tool.

Personal health metrics (weight, blood pressure, glucose, workouts) with manual
entry today and vendor sync later (Withings OAuth, FTMS BLE). Storage is the
shared TimeSeriesDB health_metrics table, so trends come for free.

PORTMANTEAU PATTERN RATIONALE:
Weight/BP/glucose/workouts share one lifecycle (validate, store with source,
trend over time). One tool with an action enum beats four tools.
"""

import logging
import time
from typing import Any, Literal

from fastmcp import FastMCP

from devices_mcp.db.timeseries import TimeSeriesDB
from devices_mcp.utils.response_builders import build_success_response

logger = logging.getLogger(__name__)


def _err(message: str) -> dict[str, Any]:
    logger.warning("health_management: %s", message)
    return {"success": False, "message": message, "timestamp": time.time()}


HEALTH_ACTIONS = {
    "log_weight": "Log body weight in kg",
    "log_bp": "Log blood pressure (systolic/diastolic mmHg, optional pulse)",
    "log_glucose": "Log blood glucose (mg/dL, or mmol/L with unit flag)",
    "log_workout": "Log a workout (minutes + optional km/kcal/avg HR)",
    "trends": "Latest + min/max/avg per metric over a window",
    "list": "Raw data points (newest last)",
    "delete": "Delete one data point by id (mistyped entries)",
}

# Plausible human ranges; out-of-range values are rejected, not stored.
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


def _check_range(metric: str, value: float) -> str | None:
    bounds = _RANGES.get(metric)
    if bounds and not (bounds[0] <= value <= bounds[1]):
        return f"{value} outside plausible range {bounds[0]}-{bounds[1]} for {metric}"
    return None


def register_health_management_tool(mcp: FastMCP) -> None:
    """Register the health management portmanteau tool."""

    @mcp.tool()
    async def health_management(
        action: Literal["log_weight", "log_bp", "log_glucose", "log_workout", "trends", "list", "delete"],
        value: float | None = None,
        systolic: float | None = None,
        diastolic: float | None = None,
        pulse: float | None = None,
        unit: str | None = None,
        minutes: float | None = None,
        km: float | None = None,
        kcal: float | None = None,
        avg_hr: float | None = None,
        kind: str | None = None,
        metric: str | None = None,
        days: int = 90,
        row_id: int | None = None,
        source: str = "manual",
        notes: str = "",
    ) -> dict[str, Any]:
        """
        Log and trend personal health metrics (weight, blood pressure, glucose, workouts).

        ## Return Format
        Dict with success, operation, summary, result, recommendations, next_steps.

        Args:
            action (Literal, required): One of "log_weight", "log_bp", "log_glucose",
                "log_workout", "trends", "list", "delete".
                - "log_weight": requires value (kg).
                - "log_bp": requires systolic + diastolic (mmHg); pulse optional.
                - "log_glucose": requires value; unit "mgdl" (default) or "mmol" (converted).
                - "log_workout": requires minutes; km/kcal/avg_hr/kind optional.
                - "trends": optional metric + days (default 90).
                - "list": optional metric + days.
                - "delete": requires row_id.
            value (float): Single-value metrics (weight kg, glucose).
            systolic/diastolic/pulse (float): BP parts.
            unit (str): "mgdl" or "mmol" for glucose.
            minutes/km/kcal/avg_hr/kind: workout parts ("walk", "bike", "run", ...).
            metric (str): metric key filter for trends/list.
            days (int): lookback window.
            row_id (int): data point id for delete.
            source (str): "manual" (default), "withings", "ftms" later.
            notes (str): free text (e.g. "after lunch", "Zojirushi rice day").
        """
        try:
            db = TimeSeriesDB()

            if action == "log_weight":
                if value is None:
                    return _err("log_weight needs value (kg)")
                err = _check_range("weight_kg", value)
                if err:
                    return _err(err)
                rid = db.store_health_metric("weight_kg", value, "kg", source, notes)
                return build_success_response(
                    operation="health_log_weight",
                    summary=f"Logged weight {value} kg (id {rid})",
                    result={"id": rid, "metric": "weight_kg", "value": value},
                )

            if action == "log_bp":
                if systolic is None or diastolic is None:
                    return _err("log_bp needs systolic + diastolic (mmHg)")
                for m, v in (("sys_mmhg", systolic), ("dia_mmhg", diastolic)):
                    err = _check_range(m, v)
                    if err:
                        return _err(err)
                ids = [
                    db.store_health_metric("sys_mmhg", systolic, "mmHg", source, notes),
                    db.store_health_metric("dia_mmhg", diastolic, "mmHg", source, notes),
                ]
                if pulse is not None:
                    err = _check_range("pulse_bpm", pulse)
                    if err:
                        return _err(err)
                    ids.append(db.store_health_metric("pulse_bpm", pulse, "bpm", source, notes))
                return build_success_response(
                    operation="health_log_bp",
                    summary=f"Logged BP {systolic}/{diastolic} mmHg"
                    + (f" + pulse {pulse}" if pulse is not None else ""),
                    result={"ids": ids, "systolic": systolic, "diastolic": diastolic, "pulse": pulse},
                )

            if action == "log_glucose":
                if value is None:
                    return _err("log_glucose needs value")
                mgdl = value * 18.018 if (unit or "mgdl").lower() in ("mmol", "mmol/l") else value
                err = _check_range("glucose_mgdl", mgdl)
                if err:
                    return _err(err)
                rid = db.store_health_metric("glucose_mgdl", mgdl, "mg/dL", source, notes)
                return build_success_response(
                    operation="health_log_glucose",
                    summary=f"Logged glucose {mgdl:.0f} mg/dL (id {rid})",
                    result={"id": rid, "metric": "glucose_mgdl", "value": mgdl},
                )

            if action == "log_workout":
                if minutes is None:
                    return _err("log_workout needs minutes")
                parts = {"workout_min": minutes}
                if km is not None:
                    parts["workout_km"] = km
                if kcal is not None:
                    parts["workout_kcal"] = kcal
                if avg_hr is not None:
                    parts["workout_avgbpm"] = avg_hr
                ids = []
                for m, v in parts.items():
                    err = _check_range(m, v)
                    if err:
                        return _err(err)
                    unit_map = {
                        "workout_min": "min",
                        "workout_km": "km",
                        "workout_kcal": "kcal",
                        "workout_avgbpm": "bpm",
                    }
                    ids.append(db.store_health_metric(m, v, unit_map[m], source, kind or notes))
                label = kind or "workout"
                return build_success_response(
                    operation="health_log_workout",
                    summary=f"Logged {label}: {minutes} min"
                    + (f", {km} km" if km is not None else "")
                    + (f", {kcal} kcal" if kcal is not None else ""),
                    result={"ids": ids, "kind": kind, "minutes": minutes},
                )

            if action == "trends":
                rows = db.get_health_history(metric=metric, days=days)
                by_metric: dict[str, list[float]] = {}
                for row in rows:
                    by_metric.setdefault(row["metric"], []).append(row["value"])
                summary = {}
                for m, vals in by_metric.items():
                    summary[m] = {
                        "count": len(vals),
                        "latest": vals[-1],
                        "min": min(vals),
                        "max": max(vals),
                        "avg": round(sum(vals) / len(vals), 2),
                    }
                return build_success_response(
                    operation="health_trends",
                    summary=f"Trends over {days}d: {', '.join(f'{m} n={s["count"]} latest={s["latest"]}' for m, s in summary.items()) or 'no data'}",
                    result={"metrics": summary, "days": days},
                )

            if action == "list":
                rows = db.get_health_history(metric=metric, days=days)
                return build_success_response(
                    operation="health_list",
                    summary=f"{len(rows)} data point(s)",
                    result={"points": rows[-200:]},
                )

            if action == "delete":
                if row_id is None:
                    return _err("delete needs row_id (see list)")
                ok = db.delete_health_metric(row_id)
                if not ok:
                    return _err(f"No data point with id {row_id}")
                return build_success_response(
                    operation="health_delete",
                    summary=f"Deleted data point {row_id}",
                    result={"id": row_id},
                )

            return _err(f"Unknown action '{action}'")

        except Exception as e:
            logger.exception("health_management failed:")
            return _err(f"health_management failed: {e}")
