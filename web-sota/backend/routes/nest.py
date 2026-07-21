import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devices_mcp.config import get_config
from devices_mcp.integrations.homeassistant_client import HomeAssistantClient
from devices_mcp.integrations.nest_client import NestClient, get_nest_client, init_nest_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/nest", tags=["nest"])


@router.get("/ha-status")
async def get_nest_via_ha():
    """Get Nest Protect devices via Home Assistant REST API.

    Requires Home Assistant running with Nest integration configured.
    Configure HA_URL and HA_ACCESS_TOKEN in .env or config.yaml.
    """
    cfg = get_config() or {}
    ha_cfg = cfg.get("security", {}).get("integrations", {}).get("homeassistant", {})
    if not ha_cfg.get("enabled"):
        return {"initialized": False, "source": "ha", "error": "Home Assistant integration not enabled"}
    url = ha_cfg.get("url", "http://localhost:8123")
    token = ha_cfg.get("access_token", "")
    if not token:
        return {"initialized": False, "source": "ha", "error": "HA_ACCESS_TOKEN not configured"}
    client = HomeAssistantClient(base_url=url, access_token=token)
    if not await client.initialize():
        return {"initialized": False, "source": "ha", "error": f"Cannot connect to Home Assistant at {url}"}
    try:
        devices = await client.get_nest_protect_devices()
        await client.close()
        device_list = [d.to_dict() for d in devices]
        smoke_alarm = any(d.smoke_status == "emergency" for d in devices)
        co_alarm = any(d.co_status == "emergency" for d in devices)
        low_battery = [d.friendly_name for d in devices if d.battery_level is not None and d.battery_level < 20]
        return {
            "initialized": True,
            "source": "ha",
            "total_devices": len(devices),
            "online_count": len(devices),
            "smoke_status": "alarm" if smoke_alarm else "clear",
            "co_status": "alarm" if co_alarm else "clear",
            "all_ok": not smoke_alarm and not co_alarm,
            "battery_warnings": low_battery,
            "devices": device_list,
            "message": f"via Home Assistant ({len(devices)} Nest Protect devices)",
        }
    except Exception as e:
        await client.close()
        logger.exception("HA Nest query failed")
        return {"initialized": False, "source": "ha", "error": str(e)}


def _get_config() -> dict:
    cfg = get_config() or {}
    return cfg.get("nest", cfg.get("security", {}).get("integrations", {}).get("nest", {}))


@router.get("/status")
async def get_nest_status():
    """Get Nest Protect system status and all devices."""
    client = get_nest_client()
    if not client or not client.is_initialized:
        cfg = _get_config()
        oauth_url = ""
        has_custom_creds = bool(cfg.get("client_id"))
        try:
            tmp = NestClient(
                client_id=cfg.get("client_id"),
                client_secret=cfg.get("client_secret"),
            )
            oauth_url = tmp.get_oauth_url()
        except Exception:
            pass
        return {
            "initialized": False,
            "error": "Nest not connected",
            "has_token": bool(cfg.get("refresh_token") or _cached_token_exists()),
            "oauth_url": oauth_url,
            "has_custom_creds": has_custom_creds,
        }

    return await client.get_summary()


class CodeExchangeRequest(BaseModel):
    code: str


@router.post("/oauth/exchange")
async def exchange_oauth_code(req: CodeExchangeRequest):
    """Exchange OAuth authorization code for refresh token."""
    cfg = _get_config()
    client = get_nest_client()
    if not client:
        client = NestClient(
            client_id=cfg.get("client_id"),
            client_secret=cfg.get("client_secret"),
        )
    success = await client.exchange_code(req.code)
    if not success:
        raise HTTPException(status_code=400, detail="Code exchange failed. Make sure you copied the full code.")
    await client.initialize()
    return {"success": True, "message": "Nest authenticated. Devices will appear shortly."}


class TokenRequest(BaseModel):
    refresh_token: str


@router.post("/token")
async def save_nest_token(req: TokenRequest):
    """Save a Nest refresh token (paste from browser / another setup)."""
    from pathlib import Path

    cfg = _get_config()
    token_file = cfg.get("token_file", "nest_token.cache")
    Path(token_file).write_text(__import__("json").dumps({"refresh_token": req.refresh_token}))
    client = await init_nest_client(
        refresh_token=req.refresh_token,
        token_file=token_file,
        cache_ttl=cfg.get("cache_ttl", 60),
    )
    if client and client.is_initialized:
        return {"success": True, "message": f"Token saved. Found {len(client._devices)} Nest Protect device(s)."}
    return {"success": False, "message": "Token saved but initialization failed. Check the token is valid."}


def _cached_token_exists() -> bool:
    import json
    from pathlib import Path

    cfg = _get_config()
    token_file = cfg.get("token_file", "nest_token.cache")
    p = Path(token_file)
    if p.exists():
        try:
            d = json.loads(p.read_text())
            return bool(d.get("refresh_token"))
        except Exception:
            pass
    return False


async def _auto_init() -> NestClient | None:
    cfg = _get_config()
    if not cfg.get("enabled", True):
        return None
    token = cfg.get("refresh_token")
    client = await init_nest_client(
        refresh_token=token,
        token_file=cfg.get("token_file", "nest_token.cache"),
        cache_ttl=cfg.get("cache_ttl", 60),
        client_id=cfg.get("client_id"),
        client_secret=cfg.get("client_secret"),
    )
    return client
