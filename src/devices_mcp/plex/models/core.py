"""
Core Pydantic models for PlexMCP.

This module contains the core data models used throughout the PlexMCP application.
"""

from typing import Optional

from pydantic import BaseModel, Field


class PlexServerStatus(BaseModel):
    """Plex server status information"""

    name: str = Field(description="Server name")
    version: str = Field(description="Plex server version")
    platform: str = Field(description="Platform (Linux, Windows, etc)")
    updated_at: int = Field(description="Last updated timestamp")
    size: int = Field(description="Database size")
    my_plex_username: Optional[str] = Field(description="MyPlex account username")
    my_plex_mapping_state: str = Field(description="MyPlex mapping status")
    connected: bool = Field(description="Connection status")


class MediaLibrary(BaseModel):
    """Plex media library information"""

    key: str = Field(description="Library key/ID")
    title: str = Field(description="Library name")
    type: str = Field(description="Library type (movie, show, music, etc)")
    agent: str = Field(description="Metadata agent")
    scanner: str = Field(description="Library scanner")
    language: str = Field(description="Primary language")
    uuid: str = Field(description="Library UUID")
    created_at: int = Field(description="Creation timestamp")
    updated_at: int = Field(description="Last updated timestamp")
    count: int = Field(description="Number of items in library")


class MediaItem(BaseModel):
    """Individual media item (movie, episode, etc)"""

    key: str = Field(description="Media key/ID")
    title: str = Field(description="Media title")
    type: str = Field(description="Media type")
    year: Optional[int] = Field(default=None, description="Release year")
    summary: Optional[str] = Field(default=None, description="Plot summary")
    rating: Optional[float] = Field(default=None, description="User rating")
    thumb: Optional[str] = Field(default=None, description="Thumbnail URL")
    art: Optional[str] = Field(default=None, description="Background art URL")
    duration: Optional[int] = Field(default=None, description="Duration in milliseconds")
    added_at: int = Field(description="Date added to library")
    updated_at: int = Field(description="Last updated timestamp")
