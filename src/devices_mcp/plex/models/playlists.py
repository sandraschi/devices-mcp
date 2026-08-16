"""
Playlist-related Pydantic models for PlexMCP.

This module contains models related to Plex playlists and their analytics.
"""

from typing import Any

from pydantic import BaseModel, Field


class PlexPlaylist(BaseModel):
    """Plex playlist information"""

    key: str = Field(description="Playlist key/ID")
    title: str = Field(description="Playlist name")
    type: str = Field(description="Playlist type (video, audio, photo)")
    summary: str | None = Field(description="Playlist description")
    duration: int | None = Field(description="Total playlist duration")
    item_count: int = Field(description="Number of items in playlist")
    smart: bool = Field(description="Is this a smart playlist")
    created_at: int = Field(description="Creation timestamp")
    updated_at: int = Field(description="Last updated timestamp")
    owner: str | None = Field(description="Playlist owner username")


class PlaylistCreateRequest(BaseModel):
    """Request model for creating playlists"""

    name: str = Field(description="Playlist name")
    summary: str | None = Field(description="Playlist description")
    items: list[str] | None = Field(description="List of media keys to add")
    smart_rules: dict[str, Any] | None = Field(description="Smart playlist rules (genre, year, rating, etc)")
    library_id: str | None = Field(description="Library to create smart playlist from")


class PlaylistAnalytics(BaseModel):
    """Playlist usage analytics and recommendations"""

    playlist_id: str = Field(description="Playlist key")
    name: str = Field(description="Playlist name")
    total_plays: int = Field(description="Total play count")
    unique_users: int = Field(description="Number of unique users who played")
    avg_completion_rate: float = Field(description="Average completion percentage")
    popular_items: list[str] = Field(description="Most played items in playlist")
    skip_rate: float = Field(description="Percentage of items skipped")
    recommendations: list[str] = Field(description="Suggested improvements")
    last_played: int | None = Field(description="Last play timestamp")
    simulated: bool = Field(default=False, description="True when usage stats are NOT real (explicit honesty flag)")
    note: str = Field(default="", description="Explanation when simulated=True")
