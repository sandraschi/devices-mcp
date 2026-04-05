"""
Devices MCP API v1

This module contains all the v1 API endpoints.
"""

from fastapi import APIRouter

from .endpoints import cameras, media, ptz, system

# Create the main router for v1 API
router = APIRouter()

# Include all endpoint routers
router.include_router(cameras.router, prefix="/cameras", tags=["cameras"])
router.include_router(ptz.router, prefix="/ptz", tags=["ptz"])
router.include_router(media.router, prefix="/media", tags=["media"])
router.include_router(system.router, prefix="/system", tags=["system"])

__all__ = ["router"]
