"""
Playlist-related Pydantic models for PlexMCP.

This module contains models related to Plex playlists and their analytics.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PlexPlaylist(BaseModel):
    """Plex playlist information"""

    key: str = Field(description="Playlist key/ID")
    title: str = Field(description="Playlist name")
    type: str = Field(description="Playlist type (video, audio, photo)")
    summary: Optional[str] = Field(description="Playlist description")
    duration: Optional[int] = Field(description="Total playlist duration")
    item_count: int = Field(description="Number of items in playlist")
    smart: bool = Field(description="Is this a smart playlist")
    created_at: int = Field(description="Creation timestamp")
    updated_at: int = Field(description="Last updated timestamp")
    owner: Optional[str] = Field(description="Playlist owner username")


class PlaylistCreateRequest(BaseModel):
    """Request model for creating playlists"""

    name: str = Field(description="Playlist name")
    summary: Optional[str] = Field(description="Playlist description")
    items: Optional[List[str]] = Field(description="List of media keys to add")
    smart_rules: Optional[Dict[str, Any]] = Field(
        description="Smart playlist rules (genre, year, rating, etc)"
    )
    library_id: Optional[str] = Field(description="Library to create smart playlist from")


class PlaylistAnalytics(BaseModel):
    """Playlist usage analytics and recommendations"""

    playlist_id: str = Field(description="Playlist key")
    name: str = Field(description="Playlist name")
    total_plays: int = Field(description="Total play count")
    unique_users: int = Field(description="Number of unique users who played")
    avg_completion_rate: float = Field(description="Average completion percentage")
    popular_items: List[str] = Field(description="Most played items in playlist")
    skip_rate: float = Field(description="Percentage of items skipped")
    recommendations: List[str] = Field(description="Suggested improvements")
    last_played: Optional[int] = Field(description="Last play timestamp")
