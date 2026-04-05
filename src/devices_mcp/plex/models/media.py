"""
Media models for PlexMCP.

This module contains Pydantic models for representing media items and related data.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class MediaType(str, Enum):
    """Enumeration of media types in Plex."""

    MOVIE = "movie"
    SHOW = "show"
    SEASON = "season"
    EPISODE = "episode"
    ARTIST = "artist"
    ALBUM = "album"
    TRACK = "track"
    PHOTO = "photo"
    COLLECTION = "collection"
    PLAYLIST = "playlist"
    TAG = "tag"
    ACTOR = "actor"
    ROLE = "role"
    DIRECTOR = "director"
    OTHER = "other"


class MediaItem(BaseModel):
    """Represents a media item in Plex."""

    # Core fields
    id: str = Field(..., description="Unique identifier for the media item")
    title: str = Field(..., description="Title of the media item")

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id_to_str(cls, v):
        """Convert id to string if it's an integer (Plex API returns int)."""
        return str(v) if v is not None else v

    type: MediaType = Field(..., description="Type of media")
    summary: Optional[str] = Field(None, description="Summary/description of the media")
    thumb: Optional[str] = Field(None, description="URL to the thumbnail image")
    art: Optional[str] = Field(None, description="URL to the artwork image")

    # Metadata
    year: Optional[int] = Field(None, description="Release year")
    rating: Optional[float] = Field(None, description="Content rating (0-10)")
    audience_rating: Optional[float] = Field(None, description="Audience rating (0-10)")
    content_rating: Optional[str] = Field(
        None, description="Content rating (e.g., 'TV-MA', 'PG-13')"
    )
    studio: Optional[str] = Field(None, description="Studio that produced the content")
    tagline: Optional[str] = Field(None, description="Tagline for the media")

    # Dates
    added_at: Optional[float] = Field(
        None, description="Timestamp when the item was added to the library"
    )
    updated_at: Optional[float] = Field(
        None, description="Timestamp when the item was last updated"
    )
    originally_available_at: Optional[float] = Field(
        None, description="Original release date as timestamp"
    )
    last_viewed_at: Optional[float] = Field(
        None, description="Timestamp when the item was last viewed"
    )

    # Media info
    duration: Optional[float] = Field(None, description="Duration in minutes")
    media_info: Dict[str, Any] = Field(
        default_factory=dict, description="Technical media information"
    )

    # People
    directors: List[str] = Field(default_factory=list, description="List of directors")
    writers: List[str] = Field(default_factory=list, description="List of writers")
    actors: List[Dict[str, str]] = Field(
        default_factory=list, description="List of actors with roles"
    )
    genres: List[str] = Field(default_factory=list, description="List of genres")

    # Type-specific fields
    # For movies
    original_title: Optional[str] = Field(
        None, description="Original title (for non-English movies)"
    )

    # For TV shows
    child_count: Optional[int] = Field(
        None, description="Number of child items (seasons or episodes)"
    )
    leaf_count: Optional[int] = Field(None, description="Number of leaf items (episodes)")
    viewed_leaf_count: Optional[int] = Field(None, description="Number of viewed leaf items")

    # For seasons and episodes
    show_title: Optional[str] = Field(None, description="Title of the parent show")
    season_number: Optional[int] = Field(None, description="Season number")
    episode_number: Optional[int] = Field(None, description="Episode number")
    season_episode: Optional[str] = Field(
        None, description="Formatted season and episode (e.g., 'S01E03')"
    )

    # For music
    album_title: Optional[str] = Field(None, description="Album title (for tracks)")
    artist_title: Optional[str] = Field(None, description="Artist name (for tracks/albums)")
    track_number: Optional[int] = Field(None, description="Track number (for tracks)")

    # View status
    view_count: Optional[int] = Field(None, description="Number of times the item has been viewed")
    last_viewed_at: Optional[float] = Field(
        None, description="When the item was last viewed (timestamp)"
    )

    # Additional metadata
    chapter_source: Optional[str] = Field(None, description="Source of chapter information")
    original_title: Optional[str] = Field(
        None, description="Original title (for non-English content)"
    )

    # Library section info
    library_section_id: Optional[str] = Field(None, description="ID of the library section")
    library_section_title: Optional[str] = Field(None, description="Title of the library section")

    # Plex-specific fields
    guid: Optional[str] = Field(None, description="Plex GUID")
    rating_key: Optional[str] = Field(None, description="Plex rating key")
    key: Optional[str] = Field(None, description="Plex key")

    class Config:
        json_encoders = {
            # Handle datetime serialization
            datetime: lambda v: v.timestamp() if v else None
        }
        use_enum_values = True
        allow_population_by_field_name = True


class LibrarySection(BaseModel):
    """Represents a Plex library section."""

    id: str = Field(..., description="Section ID")
    title: str = Field(..., description="Section title")
    type: str = Field(..., description="Section type (movie, show, artist, photo)")
    agent: str = Field(..., description="Metadata agent")
    scanner: str = Field(..., description="Scanner used for this section")
    language: str = Field(..., description="Language")
    updated_at: Optional[float] = Field(None, description="When the section was last updated")
    created_at: Optional[float] = Field(None, description="When the section was created")
    scanned_at: Optional[float] = Field(None, description="When the section was last scanned")
    content: Optional[str] = Field(None, description="Content type")
    content_changed_at: Optional[float] = Field(
        None, description="When the content was last changed"
    )


class MediaFilter(BaseModel):
    """Filter criteria for media queries."""

    field: str = Field(..., description="Field to filter on")
    operator: str = Field(
        "=", description="Comparison operator (e.g., '=', '!=', '>', '<', '>=', '<=', '~', '!~')"
    )
    value: Any = Field(..., description="Value to compare against")


class SortOrder(str, Enum):
    """Sort order for media queries."""

    ASC = "asc"
    DESC = "desc"


class MediaQuery(BaseModel):
    """Query parameters for searching/filtering media."""

    query: Optional[str] = Field(None, description="Search query string")
    media_type: Optional[MediaType] = Field(None, description="Filter by media type")
    section_id: Optional[str] = Field(None, description="Filter by library section ID")
    filters: List[MediaFilter] = Field(default_factory=list, description="Additional filters")
    sort_by: Optional[str] = Field(None, description="Field to sort by")
    sort_order: SortOrder = Field(SortOrder.ASC, description="Sort order")
    limit: int = Field(20, description="Maximum number of results to return")
    offset: int = Field(0, description="Offset for pagination")
