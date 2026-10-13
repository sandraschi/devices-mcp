"""Withings API client (weight + blood pressure, automatic sync).

OAuth2 flow (same shape as the Netatmo integration):
1. User creates a free app at developer.withings.com -> client_id/secret go to
   ``health.withings`` in config.yaml.
2. UI "Connect" opens authorize_url() -> user approves -> Withings redirects to
   our redirect_uri with ?code=....
3. POST /api/wellness/withings/callback?code=... exchanges + stores tokens in
   ~/.config/devices-mcp/withings_token.json (gitignored by *.cache-adjacent
   convention - actually check .gitignore; tokens never committed).
4. Supervisor syncs measurements every 15 min into health_metrics
   (source="withings"); UI shows them like manual entries.

Measure types used: 1 body weight, 9 diastolic, 10 systolic, 11 heart pulse.
Values are value * 10^unit (weight arrives in grams, unit -3).
"""

import json
import logging
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

_AUTH_BASE = "https://account.withings.com/oauth2_user/authorize2"
_TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
_MEASURE_URL = "https://wbsapi.withings.net/measure"
_SCOPE = "userinfo,user.metrics"

_TOKEN_PATH = Path("~/.config/devices-mcp/withings_token.json").expanduser()

# Withings measure types -> (health metric, unit)
_MEASURE_MAP = {
    1: ("weight_kg", "kg"),
    9: ("dia_mmhg", "mmHg"),
    10: ("sys_mmhg", "mmHg"),
    11: ("pulse_bpm", "bpm"),
}


class WithingsClient:
    """Process-shared Withings API client (singleton like NetatmoService)."""

    _instance: "WithingsClient | None" = None

    def __init__(self) -> None:
        self._tokens: dict[str, Any] = {}
        self._load_tokens()

    @classmethod
    def get_instance(cls) -> "WithingsClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -- config -----------------------------------------------------------
    def _conf(self) -> dict[str, Any]:
        try:
            from devices_mcp.config import get_config

            return (get_config() or {}).get("health", {}).get("withings", {}) or {}
        except Exception:
            return {}

    def is_configured(self) -> bool:
        conf = self._conf()
        return bool(conf.get("client_id") and conf.get("client_secret"))

    def is_connected(self) -> bool:
        return bool(self._tokens.get("refresh_token"))

    # -- tokens -----------------------------------------------------------
    def _load_tokens(self) -> None:
        try:
            if _TOKEN_PATH.exists():
                data = json.loads(_TOKEN_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self._tokens = data
        except Exception as e:
            logger.debug("Withings tokens unreadable: %s", e)

    def _save_tokens(self) -> None:
        try:
            _TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            _TOKEN_PATH.write_text(json.dumps(self._tokens, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Could not persist Withings tokens: %s", e)

    # -- OAuth ------------------------------------------------------------
    def authorize_url(self, state: str = "devices-mcp") -> str:
        """URL the user visits to approve access (empty when unconfigured)."""
        conf = self._conf()
        if not self.is_configured():
            return ""
        params = {
            "response_type": "code",
            "client_id": conf["client_id"],
            "redirect_uri": conf.get("redirect_uri", "http://127.0.0.1:10717/api/wellness/withings/callback"),
            "scope": _SCOPE,
            "state": state,
        }
        return f"{_AUTH_BASE}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange an authorization code for tokens. Returns status dict."""
        conf = self._conf()
        if not self.is_configured():
            return {"success": False, "error": "Withings not configured (health.withings.client_id/secret)"}
        payload = {
            "action": "requesttoken",
            "grant_type": "authorization_code",
            "client_id": conf["client_id"],
            "client_secret": conf["client_secret"],
            "code": code,
            "redirect_uri": conf.get("redirect_uri", "http://127.0.0.1:10717/api/wellness/withings/callback"),
        }
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(_TOKEN_URL, data=payload)
                data = resp.json()
        except Exception as e:
            logger.exception("Withings token exchange failed:")
            return {"success": False, "error": str(e)}
        body = data.get("body") or {}
        if data.get("status") != 0 or not body.get("access_token"):
            return {"success": False, "error": f"Withings refused the code: {data}"}
        self._tokens = {
            "access_token": body["access_token"],
            "refresh_token": body.get("refresh_token", ""),
            "expires_in": body.get("expires_in", 10800),
            "expires_at": time.time() + int(body.get("expires_in", 10800)),
            "userid": body.get("userid", ""),
            "scope": body.get("scope", ""),
        }
        self._save_tokens()
        logger.info("Withings OAuth connected (userid %s)", self._tokens.get("userid"))
        return {"success": True, "userid": self._tokens.get("userid")}

    async def _ensure_token(self) -> str:
        """Valid access token (refreshes when expired). Raises on failure."""
        if not self._tokens.get("refresh_token"):
            raise RuntimeError("Withings not connected - authorize first")
        if time.time() < float(self._tokens.get("expires_at", 0)) - 60:
            return str(self._tokens["access_token"])
        conf = self._conf()
        payload = {
            "action": "requesttoken",
            "grant_type": "refresh_token",
            "client_id": conf["client_id"],
            "client_secret": conf["client_secret"],
            "refresh_token": self._tokens["refresh_token"],
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(_TOKEN_URL, data=payload)
            data = resp.json()
        body = data.get("body") or {}
        if data.get("status") != 0 or not body.get("access_token"):
            raise RuntimeError(f"Withings token refresh failed: {data}")
        self._tokens.update(
            {
                "access_token": body["access_token"],
                "refresh_token": body.get("refresh_token", self._tokens["refresh_token"]),
                "expires_in": body.get("expires_in", 10800),
                "expires_at": time.time() + int(body.get("expires_in", 10800)),
            }
        )
        self._save_tokens()
        return str(self._tokens["access_token"])

    # -- measurements -----------------------------------------------------
    async def fetch_since(self, lastupdate: int = 0) -> list[dict[str, Any]]:
        """Raw measure groups newer than lastupdate (unix ts)."""
        token = await self._ensure_token()
        params = {
            "action": "getmeas",
            "meastypes": "1,9,10,11",
            "category": 1,
            "lastupdate": lastupdate,
        }
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.get(_MEASURE_URL, params=params, headers={"Authorization": f"Bearer {token}"})
            data = resp.json()
        if data.get("status") != 0:
            raise RuntimeError(f"Withings getmeas failed: {data}")
        return (data.get("body") or {}).get("measuregrps", []) or []

    def last_sync_ts(self) -> int:
        return int(self._tokens.get("last_sync_ts", 0))

    async def sync_to_db(self, db: Any) -> dict[str, Any]:
        """Incremental sync into health_metrics (source='withings')."""
        since = self.last_sync_ts()
        groups = await self.fetch_since(since)
        stored = 0
        newest = since
        for grp in groups:
            ts = int(grp.get("date", 0))
            newest = max(newest, ts)
            from datetime import UTC, datetime

            taken = datetime.fromtimestamp(ts, UTC)
            for m in grp.get("measures", []) or []:
                mapped = _MEASURE_MAP.get(int(m.get("type", -1)))
                if not mapped:
                    continue
                metric, unit = mapped
                value = float(m.get("value", 0)) * (10 ** int(m.get("unit", 0)))
                db.store_health_metric(metric, value, unit, "withings", "", taken)
                stored += 1
        self._tokens["last_sync_ts"] = newest
        self._save_tokens()
        return {"success": True, "stored": stored, "groups": len(groups), "newest": newest}


def get_withings_client() -> WithingsClient:
    return WithingsClient.get_instance()
