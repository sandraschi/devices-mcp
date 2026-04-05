"""
Playback-related Pydantic models for PlexMCP.

This module contains models related to Plex playback, sessions, and remote control.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class PlexSession(BaseModel):
    """Active Plex playback session"""

    session_key: str = Field(description="Session identifier")
    user: str = Field(description="Username")
    player: str = Field(description="Player name")
    state: str = Field(description="Playback state (playing, paused, etc)")
    title: str = Field(description="Media title being played")
    progress: Optional[int] = Field(description="Playback progress in seconds")
    duration: Optional[int] = Field(description="Total duration in seconds")


class PlexClient(BaseModel):
    """Available Plex client device"""

    name: str = Field(description="Client name")
    host: str = Field(description="Client host/IP")
    machine_identifier: str = Field(description="Unique client ID")
    product: str = Field(description="Client product (Plex Web, etc)")
    platform: str = Field(description="Client platform")
    platform_version: str = Field(description="Platform version")
    device: str = Field(description="Device type")


class RemotePlaybackRequest(BaseModel):
    """Request model for remote playback control"""

    client_id: str = Field(description="Target client machine identifier")
    action: str = Field(
        description="Playback action (play, pause, stop, seek, next, previous, volume)"
    )
    media_key: Optional[str] = Field(description="Media key for play action")
    seek_offset: Optional[int] = Field(description="Seek position in milliseconds")
    volume_level: Optional[int] = Field(description="Volume level (0-100)")


class CastRequest(BaseModel):
    """Request model for casting media to device"""

    client_id: str = Field(description="Target client machine identifier")
    media_key: str = Field(description="Media key to cast")
    start_offset: Optional[int] = Field(description="Start position in milliseconds")
    queue_items: Optional[List[str]] = Field(description="Additional items to queue after current")
    replace_queue: bool = Field(default=True, description="Replace existing queue")


class PlaybackControlResult(BaseModel):
    """Result of remote playback control operation"""

    status: str = Field(description="Operation status (success, error, unavailable)")
    client_id: str = Field(description="Target client identifier")
    action: str = Field(description="Action performed")
    current_state: Optional[str] = Field(description="Current playback state")
    position: Optional[int] = Field(description="Current playback position")
    duration: Optional[int] = Field(description="Total media duration")
    volume: Optional[int] = Field(description="Current volume level")
    message: str = Field(description="Status message or error details")
