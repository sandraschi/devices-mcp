"""Weather routes — Netatmo-backed where configured; no phantom WeatherManagementTool."""

import asyncio
import datetime
import html
import logging
import secrets
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

router = APIRouter()
logger = logging.getLogger(__name__)

_OAUTH_STATE_TTL_SEC = 600
_MAX_OAUTH_PENDING = 200
# state -> (expires_epoch, redirect_uri used for this flow)
_pending_netatmo_oauth: dict[str, tuple[float, str]] = {}


def _netatmo_section_from_config(config: dict[str, Any]) -> dict[str, Any]:
    return ((config.get("weather") or {}).get("integrations") or {}).get("netatmo") or {}


def _netatmo_token_cache_path(netatmo_cfg: dict[str, Any]) -> Path:
    from devices_mcp.integrations.netatmo_client import NetatmoService

    name = netatmo_cfg.get("token_file") or "netatmo_token.cache"
    return NetatmoService._adjust_token_path(name)


def _netatmo_has_refresh_token(netatmo_cfg: dict[str, Any]) -> bool:
    if (netatmo_cfg.get("refresh_token") or "").strip():
        return True
    p = _netatmo_token_cache_path(netatmo_cfg)
    try:
        return p.exists() and bool(p.read_text(encoding="utf-8", errors="replace").strip())
    except OSError:
        return False


def _netatmo_has_app_credentials(netatmo_cfg: dict[str, Any]) -> bool:
    return bool(netatmo_cfg.get("client_id") and netatmo_cfg.get("client_secret"))


def _purge_expired_oauth_states() -> None:
    now = time.time()
    dead = [s for s, (exp, _) in _pending_netatmo_oauth.items() if exp < now]
    for s in dead:
        del _pending_netatmo_oauth[s]
    while len(_pending_netatmo_oauth) > _MAX_OAUTH_PENDING:
        oldest = min(_pending_netatmo_oauth.items(), key=lambda x: x[1][0])[0]
        del _pending_netatmo_oauth[oldest]


def _oauth_callback_url(request: Request, netatmo_cfg: dict[str, Any]) -> str:
    override = (netatmo_cfg.get("oauth_callback_url") or "").strip()
    if override:
        return override.rstrip("/")
    return str(request.base_url).rstrip("/") + "/api/netatmo/oauth/callback"


def _netatmo_oauth_html_page(title: str, inner_html: str, redirect: str | None = None) -> str:
    meta = ""
    if redirect:
        meta = f'<meta http-equiv="refresh" content="3;url={html.escape(redirect, quote=True)}">'
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>{meta}
<style>
body{{font-family:system-ui,sans-serif;max-width:32rem;margin:2rem auto;padding:0 1.25rem;line-height:1.5}}
a{{color:#2563eb}}
</style></head><body>{inner_html}</body></html>"""


@router.get("/api/netatmo/status")
async def get_netatmo_status() -> dict[str, Any]:
    """Netatmo connection status for the Weather UI (OAuth refresh-token flow)."""
    from devices_mcp.config import get_config
    from devices_mcp.integrations.netatmo_client import PYATMO_AVAILABLE, NetatmoService

    raw = get_config()
    netatmo_cfg = _netatmo_section_from_config(raw)
    enabled = bool(netatmo_cfg.get("enabled", False))

    if not enabled:
        return {
            "enabled": False,
            "connected": False,
            "initialized": False,
            "message": "Netatmo is disabled in config.yaml (weather.integrations.netatmo.enabled).",
            "config_issue": True,
            "needs_init": False,
        }

    if not PYATMO_AVAILABLE:
        return {
            "enabled": True,
            "connected": False,
            "initialized": False,
            "pyatmo_available": False,
            "message": "Python package pyatmo is not installed. pip install pyatmo",
            "needs_init": False,
            "last_error": None,
        }

    if not _netatmo_has_app_credentials(netatmo_cfg):
        return {
            "enabled": True,
            "connected": False,
            "initialized": False,
            "needs_config": True,
            "needs_oauth": False,
            "message": (
                "Add a Netatmo API application: open the Netatmo developer portal, create an app, "
                "then put client_id and client_secret under weather.integrations.netatmo in config.yaml."
            ),
            "needs_init": False,
            "last_error": None,
        }

    if not _netatmo_has_refresh_token(netatmo_cfg):
        return {
            "enabled": True,
            "connected": False,
            "initialized": False,
            "needs_config": False,
            "needs_oauth": True,
            "message": (
                "Sign in with Netatmo in the browser once. After that, tokens are stored on this machine "
                "(netatmo_token.cache or your configured token_file)."
            ),
            "needs_init": False,
            "last_error": None,
        }

    inst = NetatmoService.get_existing_instance()
    if inst is None:
        return {
            "enabled": True,
            "connected": False,
            "initialized": False,
            "message": "Netatmo client not loaded yet. Click Connect to initialize.",
            "needs_init": True,
            "last_error": None,
        }

    if inst.is_api_ready():
        return {
            "enabled": True,
            "connected": True,
            "initialized": True,
            "message": "Netatmo weather station is connected.",
            "needs_init": False,
            "last_error": inst.last_error,
        }

    return {
        "enabled": True,
        "connected": False,
        "initialized": inst.initialized,
        "message": inst.last_error or "Netatmo is not connected. Click Connect to retry (check token and network).",
        "last_error": inst.last_error,
        "needs_init": True,
    }


@router.get("/api/netatmo/oauth/start")
async def netatmo_oauth_start(request: Request) -> dict[str, Any]:
    """Return Netatmo authorize URL (browser flow). Requires client_id + client_secret in config."""
    from devices_mcp.config import get_config

    raw = get_config()
    netatmo_cfg = _netatmo_section_from_config(raw)
    if not netatmo_cfg.get("enabled"):
        raise HTTPException(status_code=400, detail="Netatmo is disabled in config.yaml")
    if not _netatmo_has_app_credentials(netatmo_cfg):
        raise HTTPException(
            status_code=400,
            detail="Missing Netatmo client_id or client_secret in weather.integrations.netatmo",
        )

    _purge_expired_oauth_states()
    state = secrets.token_urlsafe(32)
    redirect_uri = _oauth_callback_url(request, netatmo_cfg)
    _pending_netatmo_oauth[state] = (time.time() + _OAUTH_STATE_TTL_SEC, redirect_uri)

    client_id = str(netatmo_cfg.get("client_id", "")).strip()
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "read_station",
        "response_type": "code",
        "state": state,
    }
    authorize_url = "https://api.netatmo.com/oauth2/authorize?" + urlencode(params)

    return {
        "authorize_url": authorize_url,
        "redirect_uri_used": redirect_uri,
        "hint": (
            "If Netatmo shows 'redirect_uri invalid', add this exact redirect URL in your Netatmo "
            "application settings. You can pin it in config as weather.integrations.netatmo.oauth_callback_url."
        ),
    }


@router.get("/api/netatmo/oauth/callback", response_class=HTMLResponse)
async def netatmo_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    """OAuth redirect target: exchange code, save refresh token, redirect back to the Weather page."""
    from devices_mcp.config import get_config

    raw = get_config()
    netatmo_cfg = _netatmo_section_from_config(raw)
    success_redirect = (netatmo_cfg.get("oauth_success_redirect") or "/app/weather?netatmo_oauth=ok").strip()

    if error:
        body = _netatmo_oauth_html_page(
            "Netatmo authorization failed",
            f'<h1>Authorization failed</h1><p>{html.escape(error)}</p><p><a href="{html.escape(success_redirect, quote=True)}">Back to Weather</a></p>',
        )
        return HTMLResponse(content=body, status_code=400)

    if not code or not state:
        body = _netatmo_oauth_html_page(
            "Netatmo authorization incomplete",
            f'<h1>Missing code or state</h1><p><a href="{html.escape(success_redirect, quote=True)}">Back to Weather</a></p>',
        )
        return HTMLResponse(content=body, status_code=400)

    _purge_expired_oauth_states()
    pending = _pending_netatmo_oauth.pop(state, None)
    if not pending:
        body = _netatmo_oauth_html_page(
            "Netatmo session expired",
            "<h1>Session expired</h1><p>Start again from the Weather page (Sign in with Netatmo).</p>",
        )
        return HTMLResponse(content=body, status_code=400)

    _expiry, redirect_uri = pending
    if time.time() > _expiry:
        body = _netatmo_oauth_html_page(
            "Netatmo session expired",
            "<h1>Session expired</h1><p>Start again from the Weather page.</p>",
        )
        return HTMLResponse(content=body, status_code=400)

    client_id = str(netatmo_cfg.get("client_id", "")).strip()
    client_secret = str(netatmo_cfg.get("client_secret", "")).strip()
    if not client_id or not client_secret:
        body = _netatmo_oauth_html_page(
            "Configuration error",
            "<h1>Missing credentials</h1><p>client_id / client_secret not set in config.</p>",
        )
        return HTMLResponse(content=body, status_code=500)

    token_data = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post("https://api.netatmo.com/oauth2/token", data=token_data)
        if resp.status_code != 200:
            err_txt = resp.text[:500]
            logger.warning("Netatmo token exchange failed: %s %s", resp.status_code, err_txt)
            body = _netatmo_oauth_html_page(
                "Token exchange failed",
                f"<h1>Could not complete sign-in</h1><pre>{html.escape(err_txt)}</pre>"
                f'<p><a href="{html.escape(success_redirect, quote=True)}">Back to Weather</a></p>',
            )
            return HTMLResponse(content=body, status_code=400)
        tokens = resp.json()
    except Exception as e:
        logger.exception("Netatmo OAuth token exchange error")
        body = _netatmo_oauth_html_page(
            "Network error",
            f"<h1>Request failed</h1><p>{html.escape(str(e))}</p>",
        )
        return HTMLResponse(content=body, status_code=500)

    refresh = (tokens.get("refresh_token") or "").strip()
    if not refresh:
        body = _netatmo_oauth_html_page(
            "Invalid token response",
            "<h1>No refresh token</h1><p>Netatmo did not return a refresh_token.</p>",
        )
        return HTMLResponse(content=body, status_code=500)

    cache_path = _netatmo_token_cache_path(netatmo_cfg)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(refresh, encoding="utf-8")
    except OSError as e:
        logger.exception("Failed to write Netatmo token cache")
        body = _netatmo_oauth_html_page(
            "Could not save token",
            f"<h1>Could not save token</h1><p>{html.escape(str(e))}</p>",
        )
        return HTMLResponse(content=body, status_code=500)

    try:
        from devices_mcp.integrations.netatmo_client import NetatmoService

        token_file = netatmo_cfg.get("token_file") or "netatmo_token.cache"
        await NetatmoService.reset_for_reconnect()
        await NetatmoService.get_instance(token_file)
    except Exception:
        logger.debug("Netatmo warm-up after OAuth failed", exc_info=True)

    inner = (
        "<h1>Netatmo connected</h1>"
        "<p>Saved your refresh token. Returning to the dashboard…</p>"
        f'<p><a href="{html.escape(success_redirect, quote=True)}">Open Weather</a> if you are not redirected.</p>'
    )
    body = _netatmo_oauth_html_page("Netatmo connected", inner, redirect=success_redirect)
    return HTMLResponse(content=body, status_code=200)


@router.post("/api/netatmo/init")
async def initialize_netatmo() -> dict[str, Any]:
    """Reconnect Netatmo (closes singleton, reloads config, runs OAuth + first sync)."""
    from devices_mcp.config import get_config
    from devices_mcp.integrations.netatmo_client import NetatmoService

    raw = get_config()
    netatmo_cfg = _netatmo_section_from_config(raw)
    if not netatmo_cfg.get("enabled"):
        raise HTTPException(status_code=400, detail="Netatmo is disabled in config.yaml")

    if not _netatmo_has_app_credentials(netatmo_cfg):
        raise HTTPException(
            status_code=400,
            detail="Missing client_id or client_secret in weather.integrations.netatmo",
        )
    if not _netatmo_has_refresh_token(netatmo_cfg):
        raise HTTPException(
            status_code=400,
            detail="No refresh token yet. Use “Sign in with Netatmo” on the Weather page first.",
        )

    token_file = netatmo_cfg.get("token_file") or "netatmo_token.cache"

    try:
        await NetatmoService.reset_for_reconnect()
        svc = await asyncio.wait_for(NetatmoService.get_instance(token_file), timeout=45.0)
    except TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Netatmo initialization timed out. Check network and api.netatmo.com access.",
        ) from None
    except Exception as e:
        logger.exception("Netatmo init failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    if svc.is_api_ready():
        stations_count: int | None = None
        try:
            stations = await asyncio.wait_for(svc.list_stations(), timeout=12.0)
            stations_count = len(stations)
        except Exception:
            logger.debug("Netatmo station list after init failed", exc_info=True)
        msg = (
            f"Connected ({stations_count} station(s))."
            if stations_count is not None
            else "Connected. Weather data should appear shortly."
        )
        return {
            "success": True,
            "connected": True,
            "message": msg,
            "stations_count": stations_count,
        }

    detail = svc.last_error or "Netatmo connection failed — check refresh token and logs."
    return {
        "success": False,
        "connected": False,
        "message": "Netatmo connection failed",
        "detail": detail,
    }


def _weather_payload_from_netatmo(weather_data: dict[str, Any]) -> dict[str, Any]:
    """Map NetatmoWeatherTool weather_data to the SPA Current card shape."""
    indoor = weather_data.get("indoor") or {}
    outdoor = weather_data.get("outdoor") or {}
    temp = indoor.get("temperature")
    if temp is None:
        temp = outdoor.get("temperature")
    humidity = indoor.get("humidity")
    if humidity is None:
        humidity = outdoor.get("humidity")
    pressure = indoor.get("pressure")
    co2 = indoor.get("co2")
    noise = indoor.get("noise")

    condition = "indoor"
    if co2 is not None:
        if co2 < 1000:
            condition = "good-air-quality"
        elif co2 < 1500:
            condition = "moderate-co2"
        else:
            condition = "high-co2"

    loc = str(weather_data.get("station_id") or "Netatmo")
    ts = weather_data.get("timestamp")
    if isinstance(ts, (int, float)):
        ts_iso = datetime.datetime.fromtimestamp(ts, tz=datetime.UTC).isoformat()
    else:
        ts_iso = datetime.datetime.now(tz=datetime.UTC).isoformat()

    return {
        "temperature": temp,
        "feels_like": temp,
        "humidity": humidity,
        "pressure": pressure,
        "wind_speed": outdoor.get("wind_strength") if isinstance(outdoor, dict) else None,
        "wind_direction": outdoor.get("wind_direction") if isinstance(outdoor, dict) else None,
        "condition": condition,
        "location": loc,
        "timestamp": ts_iso,
        "sunrise": None,
        "sunset": None,
        "co2_ppm": co2,
        "noise_db": noise,
    }


async def _primary_netatmo_station_id() -> str | None:
    """Select primary Netatmo station id (stable + user-preferred).

    Preference order:
    - weather.integrations.netatmo.primary_station_id
    - weather.integrations.netatmo.primary_station_name (case-insensitive substring match)
    - first station returned by the API
    """
    try:
        from devices_mcp.config import get_config
        from devices_mcp.integrations.netatmo_client import NetatmoService

        raw = get_config()
        netatmo_cfg = _netatmo_section_from_config(raw)
        preferred_id = str(netatmo_cfg.get("primary_station_id") or "").strip()
        preferred_name = str(netatmo_cfg.get("primary_station_name") or "").strip().lower()

        svc = await NetatmoService.get_instance()
        stations = await svc.list_stations()
        if not stations:
            return None

        if preferred_id:
            for s in stations:
                sid = s.get("station_id")
                if sid and str(sid) == preferred_id:
                    return str(sid)

        if preferred_name:
            for s in stations:
                name = str(s.get("station_name") or "")
                if preferred_name in name.lower():
                    sid = s.get("station_id")
                    return str(sid) if sid else None

        sid = stations[0].get("station_id")
        return str(sid) if sid else None
    except Exception:
        logger.debug("Could not resolve primary Netatmo station id", exc_info=True)
    return None


@router.get("/api/weather/current")
async def get_current_weather() -> dict[str, Any]:
    """Current conditions from Netatmo when enabled and authenticated."""
    try:
        from devices_mcp.tools.weather.netatmo_weather_tool import NetatmoWeatherTool

        tool = NetatmoWeatherTool()
        station_id = await _primary_netatmo_station_id()
        result = await tool.execute(operation="data", station_id=station_id)

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "Netatmo unavailable"),
                "weather": None,
            }

        wd = result.get("weather_data")
        if not isinstance(wd, dict) or not wd:
            return {
                "success": False,
                "error": "No weather payload from Netatmo",
                "weather": None,
            }

        indoor = wd.get("indoor") or {}
        outdoor = (wd.get("outdoor") or {}) if wd.get("outdoor") else {}
        if indoor.get("temperature") is None and outdoor.get("temperature") is None:
            return {
                "success": False,
                "error": "Netatmo not configured, token invalid, or no station reporting temperature.",
                "weather": None,
            }

        return {
            "success": True,
            "weather": _weather_payload_from_netatmo(wd),
        }
    except Exception as e:
        logger.exception("Error in get_current_weather: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/weather/modules")
async def get_weather_modules() -> dict[str, Any]:
    """Per-module current data from Netatmo (indoor, outdoor, extra indoor)."""
    try:
        from devices_mcp.tools.weather.netatmo_weather_tool import NetatmoWeatherTool

        tool = NetatmoWeatherTool()
        station_id = await _primary_netatmo_station_id()
        result = await tool.execute(operation="data", station_id=station_id)

        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Netatmo unavailable"), "modules": {}}

        wd = result.get("weather_data") or {}
        modules: dict[str, Any] = {}

        indoor = wd.get("indoor")
        if indoor and indoor.get("temperature") is not None:
            modules["indoor"] = {
                "name": "Indoor",
                "temperature": indoor.get("temperature"),
                "humidity": indoor.get("humidity"),
                "co2": indoor.get("co2"),
                "noise": indoor.get("noise"),
                "pressure": indoor.get("pressure"),
                "temp_trend": indoor.get("temp_trend"),
                "pressure_trend": indoor.get("pressure_trend"),
                "health_index": indoor.get("health_index", "Unknown"),
            }

        outdoor = wd.get("outdoor")
        if outdoor and outdoor.get("temperature") is not None:
            modules["outdoor"] = {
                "name": "Outdoor",
                "temperature": outdoor.get("temperature"),
                "humidity": outdoor.get("humidity"),
                "temp_trend": outdoor.get("temp_trend"),
            }

        extra = wd.get("extra_indoor")
        if extra:
            extras = extra if isinstance(extra, list) else [extra]
            for ex in extras:
                if ex.get("temperature") is not None:
                    name = ex.get("name", "Extra")
                    key = f"extra_{name.lower().replace(' ', '_')}"
                    modules[key] = {
                        "name": str(name).title(),
                        "temperature": ex.get("temperature"),
                        "humidity": ex.get("humidity"),
                        "co2": ex.get("co2"),
                        "battery": ex.get("battery_percent"),
                        "temp_trend": ex.get("temp_trend"),
                    }

        return {
            "success": True,
            "station_id": wd.get("station_id"),
            "modules": modules,
            "timestamp": wd.get("timestamp"),
        }
    except Exception as e:
        logger.exception("Error in get_weather_modules: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/weather/forecast")
async def get_weather_forecast(days: int = 7) -> dict[str, Any]:
    """7-day Vienna forecast from Open-Meteo (free, no API key)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": 48.2082,
                    "longitude": 16.3738,
                    "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "wind_speed_10m_max"],
                    "hourly": ["temperature_2m", "relative_humidity_2m"],
                    "timezone": "Europe/Vienna",
                    "forecast_days": min(days, 16),
                },
            )
            r.raise_for_status()
            data = r.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        tmax = daily.get("temperature_2m_max", [])
        tmin = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        wind = daily.get("wind_speed_10m_max", [])

        forecast = []
        for i, date in enumerate(dates):
            forecast.append(
                {
                    "date": date,
                    "temp_max": tmax[i] if i < len(tmax) else None,
                    "temp_min": tmin[i] if i < len(tmin) else None,
                    "precipitation": precip[i] if i < len(precip) else None,
                    "wind_max": wind[i] if i < len(wind) else None,
                }
            )

        hourly = data.get("hourly", {})
        h_times = hourly.get("time", [])
        h_temp = hourly.get("temperature_2m", [])
        h_hum = hourly.get("relative_humidity_2m", [])

        today = dates[0] if dates else None
        today_hourly = []
        for i, t in enumerate(h_times):
            if today and t.startswith(today):
                today_hourly.append(
                    {
                        "time": t.split("T")[1] if "T" in t else t,
                        "temperature": h_temp[i] if i < len(h_temp) else None,
                        "humidity": h_hum[i] if i < len(h_hum) else None,
                    }
                )

        return {
            "success": True,
            "location": "Vienna",
            "forecast": forecast,
            "today_hourly": today_hourly,
            "days": days,
        }
    except Exception as e:
        logger.exception("Failed to fetch Vienna forecast")
        return {"success": False, "error": str(e), "forecast": [], "days": days}


@router.get("/api/weather/history")
async def get_weather_history(days: int = 7, module: str | None = None) -> dict[str, Any]:
    """Daily averages from local SQLite per module (indoor, outdoor, extra_*)."""
    try:
        from devices_mcp.db import TimeSeriesDB

        station_id = await _primary_netatmo_station_id()
        if not station_id:
            return {"history": {}, "days": days, "success": True, "message": "No station id"}

        db = TimeSeriesDB()
        hours = max(24, days * 24)
        module_types = [module] if module else ["indoor", "outdoor"]

        history_by_module: dict[str, Any] = {}

        for mt in module_types:
            temp_rows = db.get_weather_history(
                station_id=station_id,
                module_type=mt,
                data_type="temperature",
                hours=hours,
            )
            hum_rows = db.get_weather_history(
                station_id=station_id,
                module_type=mt,
                data_type="humidity",
                hours=hours,
            )

            def _group_daily(rows):
                by_day: dict[str, list[float]] = defaultdict(list)
                for row in rows:
                    ts = row.get("timestamp")
                    val = row.get("value")
                    if ts is None or val is None:
                        continue
                    sec = float(ts)
                    if sec > 1e12:
                        sec /= 1000.0
                    dt = datetime.datetime.fromtimestamp(sec, tz=datetime.UTC)
                    by_day[dt.strftime("%Y-%m-%d")].append(float(val))
                return by_day

            temp_by_day = _group_daily(temp_rows)
            hum_by_day = _group_daily(hum_rows)

            all_dates = sorted(set(temp_by_day.keys()) | set(hum_by_day.keys()))[-days:]
            daily: list[dict[str, Any]] = []
            for d in all_dates:
                temps = temp_by_day.get(d, [])
                hums = hum_by_day.get(d, [])
                daily.append(
                    {
                        "date": d,
                        "temperature": round(sum(temps) / len(temps), 1) if temps else None,
                        "humidity": round(sum(hums) / len(hums), 1) if hums else None,
                    }
                )
            history_by_module[mt] = daily

        return {"history": history_by_module, "days": days, "success": True}
    except Exception as e:
        logger.exception("Error in get_weather_history: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/weather/stations")
async def get_weather_stations() -> dict[str, Any]:
    """List Netatmo stations (operation must be 'stations', not 'get_stations')."""
    try:
        from devices_mcp.tools.weather.netatmo_weather_tool import NetatmoWeatherTool

        tool = NetatmoWeatherTool()
        result = await tool.execute(operation="stations")

        if not result.get("success", False):
            logger.error("Failed to get weather stations: %s", result.get("error", "Unknown error"))
            raise HTTPException(status_code=500, detail="Failed to retrieve weather stations")

        return {"stations": result.get("stations", []), "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in get_weather_stations: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/weather/alerts")
async def get_weather_alerts() -> dict[str, Any]:
    """Alerts not implemented for the web UI; use Netatmo app."""
    return {
        "alerts": [],
        "success": True,
        "message": "Weather alerts are not exposed here; configure notifications in the Netatmo app.",
    }
