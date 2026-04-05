"""Plex quality and transcoding tools for FastMCP 2.10.1."""

import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ..app import mcp
from ..models.quality import BandwidthAnalysis, QualityProfile, TranscodingStatus


def _get_plex_service():
    from ..services.plex_service import PlexService

    base_url = os.getenv("PLEX_URL") or os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    token = os.getenv("PLEX_TOKEN")
    if not token:
        raise RuntimeError("PLEX_TOKEN environment variable is required")
    return PlexService(base_url=base_url, token=token)


class GetTranscodeSettingsRequest(BaseModel):
    """Request model for getting transcode settings."""

    profile_name: Optional[str] = Field(None, description="Name of the quality profile to retrieve")


@mcp.tool()
async def get_transcode_settings(request: GetTranscodeSettingsRequest) -> Dict[str, Any]:
    """Get current transcode settings for a quality profile.

    Args:
        request: Transcode settings parameters

    Returns:
        Dictionary with transcode settings
    """
    plex = _get_plex_service()
    return await plex.get_transcode_settings(profile_name=request.profile_name)


class UpdateTranscodeSettingsRequest(BaseModel):
    """Request model for updating transcode settings."""

    profile_name: str = Field(..., description="Name of the quality profile to update")
    settings: Dict[str, Any] = Field(..., description="Dictionary of settings to update")


@mcp.tool()
async def update_transcode_settings(request: UpdateTranscodeSettingsRequest) -> bool:
    """Update transcode settings for a quality profile.

    Args:
        request: Update parameters

    Returns:
        True if update was successful, False otherwise
    """
    plex = _get_plex_service()
    return await plex.update_transcode_settings(
        profile_name=request.profile_name, settings=request.settings
    )


@mcp.tool()
async def get_transcoding_status() -> TranscodingStatus:
    """Get current transcoding status.

    Returns:
        Current transcoding status information
    """
    plex = _get_plex_service()
    return await plex.get_transcoding_status()


class GetBandwidthUsageRequest(BaseModel):
    """Request model for getting bandwidth usage."""

    time_range: str = Field(
        "day", description="Time range for bandwidth data (hour, day, week, month)"
    )


@mcp.tool()
async def get_bandwidth_usage(request: GetBandwidthUsageRequest) -> BandwidthAnalysis:
    """Get bandwidth usage statistics.

    Args:
        request: Bandwidth query parameters

    Returns:
        Bandwidth usage analysis
    """
    plex = _get_plex_service()
    return await plex.get_bandwidth_usage(time_range=request.time_range)


class SetStreamQualityRequest(BaseModel):
    """Request model for setting stream quality."""

    profile_name: str = Field(..., description="Name of the quality profile")
    quality: str = Field(..., description="Quality setting (e.g., '1080p', '720p', '480p')")
    bitrate: Optional[int] = Field(None, description="Maximum bitrate in kbps")


@mcp.tool()
async def set_stream_quality(request: SetStreamQualityRequest) -> bool:
    """Set streaming quality settings for a profile.

    Args:
        request: Quality settings

    Returns:
        True if update was successful, False otherwise
    """
    plex = _get_plex_service()
    return await plex.set_stream_quality(
        profile_name=request.profile_name, quality=request.quality, bitrate=request.bitrate
    )


class GetThrottlingStatusRequest(BaseModel):
    """Request model for getting throttling status."""

    profile_name: Optional[str] = Field(None, description="Name of the quality profile")


@mcp.tool()
async def get_throttling_status(request: GetThrottlingStatusRequest) -> Dict[str, Any]:
    """Get current throttling status and settings.

    Args:
        request: Throttling query parameters

    Returns:
        Dictionary with throttling status and settings
    """
    plex = _get_plex_service()
    return await plex.get_throttling_status(profile_name=request.profile_name)


class SetThrottlingRequest(BaseModel):
    """Request model for setting throttling."""

    profile_name: str = Field(..., description="Name of the quality profile")
    enabled: bool = Field(..., description="Whether to enable throttling")
    download_limit: Optional[int] = Field(None, description="Download limit in kbps")
    upload_limit: Optional[int] = Field(None, description="Upload limit in kbps")


@mcp.tool()
async def set_throttling(request: SetThrottlingRequest) -> bool:
    """Configure throttling settings.

    Args:
        request: Throttling configuration

    Returns:
        True if update was successful, False otherwise
    """
    plex = _get_plex_service()
    return await plex.set_throttling(
        profile_name=request.profile_name,
        enabled=request.enabled,
        download_limit=request.download_limit,
        upload_limit=request.upload_limit,
    )


@mcp.tool()
async def list_quality_profiles() -> List[QualityProfile]:
    """List all available quality profiles.

    Returns:
        List of quality profiles
    """
    plex = _get_plex_service()
    return await plex.list_quality_profiles()


class CreateQualityProfileRequest(BaseModel):
    """Request model for creating a quality profile."""

    name: str = Field(..., description="Name of the new profile")
    settings: Dict[str, Any] = Field(..., description="Profile settings")
    is_default: bool = Field(False, description="Set as default profile")


@mcp.tool()
async def create_quality_profile(request: CreateQualityProfileRequest) -> bool:
    """Create a new quality profile.

    Args:
        request: Profile creation parameters

    Returns:
        True if creation was successful, False otherwise
    """
    plex = _get_plex_service()
    return await plex.create_quality_profile(
        name=request.name, settings=request.settings, is_default=request.is_default
    )


class DeleteQualityProfileRequest(BaseModel):
    """Request model for deleting a quality profile."""

    profile_name: str = Field(..., description="Name of the profile to delete")


@mcp.tool()
async def delete_quality_profile(request: DeleteQualityProfileRequest) -> bool:
    """Delete a quality profile.

    Args:
        request: Profile deletion parameters

    Returns:
        True if deletion was successful, False otherwise
    """
    plex = _get_plex_service()
    return await plex.delete_quality_profile(profile_name=request.profile_name)
