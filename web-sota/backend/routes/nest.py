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
        oauth_url = NestClient.get_oauth_url()
        return {
            "initialized": False,
            "error": "Nest not connected",
            "has_token": bool(cfg.get("refresh_token") or _cached_token_exists()),
            "oauth_url": oauth_url,
            "setup_instructions": [
                "1. Open the OAuth URL in a browser",
                "2. Sign in with your Google account (same as Nest)",
                "3. Copy the authorization code",
                "4. Paste the code below and click 'Exchange Code'",
                "5. Refresh token will be saved to nest_token.cache",
            ],
        }

    return await client.get_summary()


class CodeExchangeRequest(BaseModel):
    code: str


@router.post("/oauth/exchange")
async def exchange_oauth_code(req: CodeExchangeRequest):
    """Exchange OAuth authorization code for refresh token."""
    client = get_nest_client()
    if not client:
        client = NestClient()
    success = await client.exchange_code(req.code)
    if not success:
        raise HTTPException(status_code=400, detail="Code exchange failed. Make sure you copied the full code.")
    await client.initialize()
    return {"success": True, "message": "Nest authenticated. Devices will appear shortly."}


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
    )
    return client
