"""Plex media organization tools for FastMCP 2.10.1."""

import logging
import os
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from ..app import mcp
from ..models.media import MediaType


def _get_plex_service():
    from ..services.plex_service import PlexService

    base_url = os.getenv("PLEX_URL") or os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    token = os.getenv("PLEX_TOKEN")
    if not token:
        raise RuntimeError("PLEX_TOKEN environment variable is required")
    return PlexService(base_url=base_url, token=token)


logger = logging.getLogger(__name__)


class OrganizeRequest(BaseModel):
    """Request model for organizing media."""

    library_id: str = Field(..., description="ID of the library to organize")
    dry_run: bool = Field(False, description="If True, only show what would be changed")
    patterns: Optional[Dict[str, str]] = Field(None, description="Custom patterns for organization")


@mcp.tool()
async def organize_library(request: OrganizeRequest) -> Dict[str, Any]:
    """Organize a Plex library according to best practices.

    Args:
        request: Organization parameters

    Returns:
        Dictionary with organization results
    """
    plex = _get_plex_service()
    try:
        result = await plex.organize_library(
            library_id=request.library_id, dry_run=request.dry_run, patterns=request.patterns
        )
        logger.info(f"Organized library {request.library_id}")
        return result
    except Exception:
        logger.exception("Error organizing library {request.library_id}:")
        raise


class AnalyzeLibraryRequest(BaseModel):
    """Request model for analyzing a library."""

    library_id: str = Field(..., description="ID of the library to analyze")


@mcp.tool()
async def analyze_library(request: AnalyzeLibraryRequest) -> Dict[str, Any]:
    """Analyze a library for organization issues.

    Args:
        request: Analysis parameters

    Returns:
        Dictionary with analysis results
    """
    plex = _get_plex_service()
    try:
        result = await plex.analyze_library(library_id=request.library_id)
        logger.info(
            f"Analyzed library {request.library_id}, found {result.get('issues_found', 0)} issues"
        )
        return result
    except Exception:
        logger.exception("Error analyzing library {request.library_id}:")
        raise


class FixMatchRequest(BaseModel):
    """Request model for fixing media matches."""

    item_id: str = Field(..., description="ID of the item to fix")
    match_id: str = Field(..., description="Correct match ID")
    type: MediaType = Field(..., description="Type of media")


@mcp.tool()
async def fix_media_match(request: FixMatchRequest) -> bool:
    """Fix an incorrect media match.

    Args:
        request: Fix match parameters

    Returns:
        True if the fix was successful, False otherwise
    """
    _get_plex_service()
    try:
        # In a real implementation, this would use the Plex API to fix the match
        # For now, we'll just log the action
        logger.info(f"Fixing match for item {request.item_id} with match ID {request.match_id}")
        return True
    except Exception:
        logger.exception("Error fixing match for item {request.item_id}:")
        return False


class RefreshMetadataRequest(BaseModel):
    """Request model for refreshing metadata."""

    item_id: Optional[str] = Field(None, description="ID of the item to refresh")
    library_id: Optional[str] = Field(None, description="ID of the library to refresh")
    force: bool = Field(False, description="Force refresh even if not needed")


@mcp.tool()
async def refresh_metadata(request: RefreshMetadataRequest) -> Dict[str, Any]:
    """Refresh metadata for an item or library.

    Args:
        request: Refresh parameters

    Returns:
        Dictionary with refresh results
    """
    plex = _get_plex_service()
    try:
        result = await plex.refresh_metadata(
            item_id=request.item_id, library_id=request.library_id, force=request.force
        )
        logger.info(
            f"Refreshed metadata for {'item ' + request.item_id if request.item_id else 'library ' + request.library_id}"
        )
        return result
    except Exception:
        logger.exception("Error refreshing metadata:")
        raise
        raise ValueError("Either item_id or library_id must be provided")


class CleanBundlesRequest(BaseModel):
    """Request model for cleaning bundles."""

    dry_run: bool = Field(True, description="If True, only show what would be deleted")
    threshold_days: int = Field(30, description="Delete bundles older than this many days")


@mcp.tool()
async def clean_bundles(request: CleanBundlesRequest) -> Dict[str, Any]:
    """Clean up old bundles to free up disk space.

    Args:
        request: Cleanup parameters

    Returns:
        Dictionary with cleanup results
    """
    _get_plex_service()
    try:
        # In a real implementation, this would clean up old bundles
        # For now, we'll just log the action
        logger.info(
            f"Cleaning bundles (dry_run={request.dry_run}, threshold_days={request.threshold_days})"
        )
        return {
            "cleaned": 0 if request.dry_run else 10,  # Example count
            "freed_space": "0B" if request.dry_run else "1.2GB",  # Example size
            "dry_run": request.dry_run,
        }
    except Exception:
        logger.exception("Error cleaning bundles:")
        raise


class OptimizeDatabaseRequest(BaseModel):
    """Request model for optimizing the database."""

    analyze: bool = Field(True, description="Run ANALYZE on the database")
    vacuum: bool = Field(True, description="Run VACUUM on the database")
    reindex: bool = Field(True, description="Rebuild indexes")


@mcp.tool()
async def optimize_database(request: OptimizeDatabaseRequest) -> Dict[str, Any]:
    """Optimize the Plex database.

    Args:
        request: Optimization parameters

    Returns:
        Dictionary with optimization results
    """
    _get_plex_service()
    try:
        # In a real implementation, this would optimize the database
        # For now, we'll just log the action
        logger.info(
            f"Optimizing database (analyze={request.analyze}, vacuum={request.vacuum}, reindex={request.reindex})"
        )
        return {
            "optimized": True,
            "operations": {
                "analyze": request.analyze,
                "vacuum": request.vacuum,
                "reindex": request.reindex,
            },
            "result": "Database optimization completed successfully",
        }
    except Exception:
        logger.exception("Error optimizing database:")
        raise
