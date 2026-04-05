"""Plex media tools for FastMCP 2.10.1."""

import os
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field

from ..app import mcp
from ..models.media import MediaItem


def _get_plex_service():
    """Get PlexService instance with proper environment variable handling."""
    from ..services.plex_service import PlexService

    base_url = os.getenv("PLEX_URL") or os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    token = os.getenv("PLEX_TOKEN")

    if not token:
        raise RuntimeError("PLEX_TOKEN environment variable is required")

    return PlexService(base_url=base_url, token=token)


class MediaSearchRequest(BaseModel):
    """Request model for advanced media search.

    This model supports a wide range of filtering and sorting options for precise media searches.
    All parameters are optional except where noted.
    """

    # Basic search parameters
    query: str = Field(
        "",
        description="General search term that searches across multiple fields (title, description, etc.)",
    )
    limit: int = Field(
        100, ge=1, le=1000, description="Maximum number of results to return (1-1000)"
    )
    offset: int = Field(
        0, ge=0, description="Pagination offset for retrieving subsequent pages of results"
    )
    library_id: Optional[str] = Field(
        None, description="Optional library ID to search within a specific library"
    )

    # Media type and basic filters
    media_type: Optional[
        Literal["movie", "show", "season", "episode", "artist", "album", "track", "photo"]
    ] = Field(None, description="Filter by specific media type")
    title: Optional[str] = Field(
        None, description="Filter by title (supports wildcards with * for partial matches)"
    )

    # Date/Year filters
    year: Optional[Union[int, List[int], str]] = Field(
        None,
        description="Filter by specific year, list of years, or year range (e.g., '2020-2022')",
    )
    decade: Optional[int] = Field(
        None, ge=1900, le=2100, description="Filter by decade (e.g., 2020 for 2020s)"
    )
    min_year: Optional[int] = Field(
        None, ge=1900, le=2100, description="Minimum release year (inclusive)"
    )
    max_year: Optional[int] = Field(
        None, ge=1900, le=2100, description="Maximum release year (inclusive)"
    )

    # People filters
    actor: Optional[Union[str, List[str]]] = Field(None, description="Filter by actor name(s)")
    director: Optional[Union[str, List[str]]] = Field(
        None, description="Filter by director name(s)"
    )

    # Content classification
    genre: Optional[Union[str, List[str]]] = Field(None, description="Filter by genre(s)")
    content_rating: Optional[Union[str, List[str]]] = Field(
        None, description="Filter by content rating(s) (e.g., 'PG', 'R', 'TV-MA')"
    )
    studio: Optional[Union[str, List[str]]] = Field(None, description="Filter by studio(s)")
    country: Optional[Union[str, List[str]]] = Field(
        None, description="Filter by country/countries of origin"
    )
    language: Optional[Union[str, List[str]]] = Field(
        None, description="Filter by language code(s) (e.g., 'en', 'ja', 'es')"
    )
    collection: Optional[Union[str, List[str]]] = Field(
        None, description="Filter by collection name(s)"
    )

    # Rating filters
    min_rating: Optional[float] = Field(None, ge=0, le=10, description="Minimum user rating (0-10)")
    max_rating: Optional[float] = Field(None, ge=0, le=10, description="Maximum user rating (0-10)")

    # Status filters
    unwatched: Optional[bool] = Field(None, description="If True, only return unwatched items")

    # Sorting
    sort_by: Optional[
        Literal[
            "titleSort",
            "title",
            "year",
            "rating",
            "audienceRating",
            "viewCount",
            "lastViewedAt",
            "addedAt",
            "updatedAt",
            "duration",
            "mediaHeight",
            "mediaWidth",
            "mediaBitrate",
        ]
    ] = Field("titleSort", description="Field to sort results by")
    sort_dir: Optional[Literal["asc", "desc"]] = Field(
        "asc", description="Sort direction: 'asc' for ascending, 'desc' for descending"
    )


@mcp.tool()
async def search_media(request: MediaSearchRequest) -> Dict[str, Any]:
    """Search for media items in the Plex library with advanced filtering.

    Advanced Search Parameters:
    -------------------------
    - query (str): General search term (searches across multiple fields)
    - limit (int, default=100): Maximum number of results (1-1000)
    - offset (int, default=0): Pagination offset
    - library_id (str): Optional library ID to search within
    - media_type (str): Filter by type (movie, show, season, episode, artist, album, track, photo)
    - title (str): Filter by title (supports wildcards with *)
    - year (int/list/str): Filter by specific year or list of years
    - decade (int): Filter by decade (e.g., 2020 for 2020s)
    - genre (str/list): Filter by genre (single or list)
    - actor (str/list): Filter by actor (single or list)
    - director (str/list): Filter by director (single or list)
    - content_rating (str/list): Filter by content rating (e.g., 'PG', 'R', 'TV-MA')
    - studio (str/list): Filter by studio
    - country (str/list): Filter by country
    - language (str/list): Filter by language code (e.g., 'en', 'ja')
    - collection (str/list): Filter by collection
    - min_rating (float): Minimum user rating (0-10)
    - max_rating (float): Maximum user rating (0-10)
    - min_year (int): Minimum release year
    - max_year (int): Maximum release year
    - unwatched (bool): Only show unwatched items
    - sort_by (str): Field to sort by (default: 'titleSort')
    - sort_dir (str): Sort direction ('asc' or 'desc', default: 'asc')

    Sortable Fields:
    - titleSort, title, year, rating, audienceRating, viewCount, lastViewedAt,
      addedAt, updatedAt, duration, mediaHeight, mediaWidth, mediaBitrate

    Examples:
    --------
    # Basic search
    {"query": "Star Wars"}

    # Search with multiple filters
    {
        "media_type": "movie",
        "genre": ["Action", "Adventure"],
        "min_year": 2010,
        "min_rating": 7.5,
        "sort_by": "rating",
        "sort_dir": "desc"
    }

    # Search by actors and unwatched
    {
        "media_type": "movie",
        "actor": ["Leonardo DiCaprio", "Meryl Streep"],
        "unwatched": true
    }

    # Search in a specific collection
    {
        "collection": "Marvel Cinematic Universe",
        "sort_by": "year",
        "sort_dir": "asc"
    }

    Returns:
        Dictionary containing:
        - items: List of matching media items
        - total: Total number of matches
        - offset: Current pagination offset
        - limit: Number of items per page
        - filters: Applied filters
    """
    plex = _get_plex_service()
    return await plex.search_media(
        query=request.query,
        limit=request.limit,
        offset=request.offset,
        library_id=request.library_id,
        media_type=request.media_type,
        title=request.title,
        year=request.year,
        decade=request.decade,
        genre=request.genre,
        actor=request.actor,
        director=request.director,
        content_rating=request.content_rating,
        studio=request.studio,
        country=request.country,
        language=request.language,
        collection=request.collection,
        min_rating=request.min_rating,
        max_rating=request.max_rating,
        min_year=request.min_year,
        max_year=request.max_year,
        unwatched=request.unwatched,
        sort_by=request.sort_by or "titleSort",
        sort_dir=request.sort_dir or "asc",
    )


class MediaInfoRequest(BaseModel):
    """Request model for getting media information."""

    media_id: str = Field(..., description="ID of the media item")


@mcp.tool()
async def get_media_info(request: MediaInfoRequest) -> Optional[MediaItem]:
    """Get detailed information about a specific media item.

    Args:
        request: Media information request

    Returns:
        Detailed media information or None if not found
    """
    plex = _get_plex_service()
    return await plex.get_media_info(request.media_id)


class LibraryItemsRequest(BaseModel):
    """Request model for getting library items."""

    library_id: str = Field(..., description="ID of the library")
    limit: int = Field(100, description="Maximum number of items to return")
    offset: int = Field(0, description="Offset for pagination")


@mcp.tool()
async def get_library_items(request: LibraryItemsRequest) -> List[MediaItem]:
    """Get items from a specific library.

    Args:
        request: Library items request parameters

    Returns:
        List of media items in the specified library
    """
    plex = _get_plex_service()
    return await plex.get_library_items(
        library_id=request.library_id, limit=request.limit, offset=request.offset
    )
