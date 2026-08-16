"""Fleet-standard v1 API aliases - SOTA endpoints the e2e audit expects.

Maps the standard surface (GET /api/v1/models, GET /api/v1/settings)
onto this repo's real handlers so the fleet auditor and webapp probes
find them.
"""

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["v1 aliases"])


@router.get("/models", summary="List available LLM models (fleet standard alias)")
async def v1_models():
    from .llm import list_models

    result = await list_models()
    models = result.get("models", []) if isinstance(result, dict) else []
    return {**result, "chat": [m.get("name") for m in models]}


@router.get("/settings", summary="Settings summary (fleet standard alias)")
async def v1_settings():
    from .settings_prefs import get_llm_settings, get_logging_settings

    llm = await get_llm_settings()
    configured = bool(
        isinstance(llm, dict) and llm.get("providers") and any(p.get("available") for p in llm["providers"])
    )
    return {
        "llm": llm,
        "logging": await get_logging_settings(),
        "configured": configured,
    }
