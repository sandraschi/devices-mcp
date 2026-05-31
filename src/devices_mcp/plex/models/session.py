"""Pydantic models for Plex sessions and playback."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SessionState(StrEnum):
    """Possible states of a Plex session."""

    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    BUFFERING = "buffering"
    ERROR = "error"


class MediaType(StrEnum):
    """Types of media in Plex."""

    MOVIE = "movie"
    EPISODE = "episode"
    TRACK = "track"
    PHOTO = "photo"
    CLIP = "clip"
    PLAYLIST = "playlist"


class MediaItem(BaseModel):
    """Base model for media items in Plex."""

    id: str = Field(..., description="Unique identifier for the media item")
    type: MediaType = Field(..., description="Type of media")

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id_to_str(cls, v):
        """Convert id to string if it's an integer (Plex API returns int)."""
        return str(v) if v is not None else v

    title: str = Field(..., description="Title of the media")
    year: int | None = Field(None, description="Release year")
    thumb: str | None = Field(None, description="URL to thumbnail image")
    duration: int | None = Field(None, description="Duration in milliseconds")
    added_at: int | None = Field(None, description="Timestamp when added to library")
    updated_at: int | None = Field(None, description="Timestamp of last update")


class Session(BaseModel):
    """Model representing an active Plex playback session."""

    session_key: str = Field(..., description="Unique identifier for the session")
    user_id: int = Field(..., description="ID of the user")
    username: str = Field(..., description="Username of the user")
    player: str = Field(..., description="Name of the player/client")
    state: SessionState = Field(..., description="Current playback state")
    progress: int = Field(0, description="Playback progress in milliseconds")
    view_offset: int = Field(0, description="Current position in the media")
    duration: int = Field(0, description="Total duration of the media in milliseconds")
    media: MediaItem = Field(..., description="The media being played")
    extra_metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the session")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the session was created")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="When the session was last updated")


class SessionList(BaseModel):
    """Model representing a list of active sessions."""

    sessions: list[Session] = Field(default_factory=list, description="List of active sessions")
    total: int = Field(0, description="Total number of sessions")
