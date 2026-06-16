import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from devices_mcp.config import get_config
from devices_mcp.integrations.nest_client import NestClient, get_nest_client, init_nest_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/nest", tags=["nest"])


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
