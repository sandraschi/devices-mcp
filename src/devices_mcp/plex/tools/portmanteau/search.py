"""
PlexMCP Advanced Search Portmanteau Tool

Consolidates all search-related operations into a single comprehensive interface.
FastMCP 2.13+ compliant with comprehensive docstrings and AI-friendly error messages.
"""

import os
from typing import Any, Dict, List, Literal, Optional, Union

from ...app import mcp
from ...utils import get_logger

logger = get_logger(__name__)

# In-memory storage for recent searches and saved searches
_recent_searches: List[Dict[str, Any]] = []
_saved_searches: Dict[str, Dict[str, Any]] = {}


def _get_plex_service():
    """Get PlexService instance with proper environment variable handling."""
    from ...services.plex_service import PlexService

    base_url = os.getenv("PLEX_URL") or os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    token = os.getenv("PLEX_TOKEN")

    if not token:
        raise RuntimeError(
            "PLEX_TOKEN environment variable is required. "
            "Get your token from Plex Web App (Settings → Account → Authorized Devices) "
            "or visit https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/ "
            "for detailed instructions."
        )

    return PlexService(base_url=base_url, token=token)


@mcp.tool()
async def plex_search(
    operation: Literal["search", "advanced_search", "suggest", "recent_searches", "save_search"],
    query: Optional[str] = None,
    library_id: Optional[str] = None,
    media_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    title: Optional[str] = None,
    year: Optional[Union[int, List[int], str]] = None,
    decade: Optional[int] = None,
    genre: Optional[Union[str, List[str]]] = None,
    actor: Optional[Union[str, List[str]]] = None,
    director: Optional[Union[str, List[str]]] = None,
    content_rating: Optional[Union[str, List[str]]] = None,
    studio: Optional[Union[str, List[str]]] = None,
    country: Optional[Union[str, List[str]]] = None,
    language: Optional[Union[str, List[str]]] = None,
    collection: Optional[Union[str, List[str]]] = None,
    min_rating: Optional[float] = None,
    max_rating: Optional[float] = None,
    min_year: Optional[int] = None,
    max_year: Optional[int] = None,
    unwatched: Optional[bool] = None,
    sort_by: str = "titleSort",
    sort_dir: str = "asc",
    search_name: Optional[str] = None,
    max_recent: int = 10,
    summary_contains: Optional[str] = None,
) -> Dict[str, Any]:
    """Comprehensive search management tool for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 5 separate tools (one per search operation), this tool consolidates related
    search operations into a single interface. This design:
    - Prevents tool explosion (5 tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with search tasks
    - Enables consistent search interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - search: Basic text search across media libraries
    - advanced_search: Complex multi-criteria search with extensive filtering
    - suggest: Get search suggestions/autocomplete based on partial query
    - recent_searches: Retrieve recently performed searches
    - save_search: Save a search query for future reuse

    OPERATIONS DETAIL:

    search: Basic text search
    - Parameters: query (required), library_id (optional), media_type (optional), limit (default: 100)
    - Returns: List of matching media items with basic metadata
    - Use when: You need a simple text search across titles, descriptions, etc.

    advanced_search: Complex multi-criteria search
    - Parameters: All search filters (title, year, genre, actor, director, etc.), sorting options
    - Returns: Paginated results with total count and applied filters
    - Use when: You need precise filtering with multiple criteria

    suggest: Search suggestions/autocomplete
    - Parameters: query (required, partial text), limit (default: 10)
    - Returns: List of suggested search terms or matching items
    - Use when: Building search UI or providing autocomplete functionality

    recent_searches: Get recent search history
    - Parameters: max_recent (default: 10)
    - Returns: List of recently performed searches with timestamps
    - Use when: Showing search history or allowing users to repeat searches

    save_search: Save a search query
    - Parameters: search_name (required), query and filters (required)
    - Returns: Confirmation with saved search details
    - Use when: Users want to save frequently used search queries

    Prerequisites:
    - Plex Media Server running and accessible
    - Valid PLEX_TOKEN environment variable set
    - PLEX_SERVER_URL configured (or defaults to http://localhost:32400)

    Args:
        operation (str): The search operation to perform. Required. Must be one of: "search", "advanced_search", "suggest", "recent_searches", "save_search"
        query (str | None): Search query text (required for search, advanced_search, suggest, save_search).
        library_id (str | None): Optional library ID to search within.
        media_type (str | None): Filter by media type (movie, show, season, episode, artist, album, track, photo).
        limit (int): Maximum number of results (default: 100, range: 1-1000).
        offset (int): Pagination offset (default: 0).
        title (str | None): Filter by title (supports wildcards with *).
        year (int | list[int] | str | None): Filter by specific year or list of years.
        decade (int | None): Filter by decade (e.g., 2020 for 2020s).
        genre (str | list[str] | None): Filter by genre (single or list).
        actor (str | list[str] | None): Filter by actor (single or list).
        director (str | list[str] | None): Filter by director (single or list).
        content_rating (str | list[str] | None): Filter by content rating (e.g., 'PG', 'R', 'TV-MA').
        studio (str | list[str] | None): Filter by studio.
        country (str | list[str] | None): Filter by country.
        language (str | list[str] | None): Filter by language code (e.g., 'en', 'ja').
        collection (str | list[str] | None): Filter by collection.
        min_rating (float | None): Minimum user rating (0-10).
        max_rating (float | None): Maximum user rating (0-10).
        min_year (int | None): Minimum release year.
        max_year (int | None): Maximum release year.
        unwatched (bool | None): Only show unwatched items.
        sort_by (str): Field to sort by (default: 'titleSort').
        sort_dir (str): Sort direction ('asc' or 'desc', default: 'asc').
        search_name (str | None): Name for saved search (required for save_search).
        max_recent (int): Maximum number of recent searches to return (default: 10).
        summary_contains (str | None): Search within plot summaries/descriptions (case-insensitive).

    Returns:
        Operation-specific result with search details and results

    Examples:
        # Basic search
        plex_search("search", query="Star Wars")

        # Search by plot summary (find films by character names, themes, etc.)
        plex_search("search", summary_contains="holly martins")  # Finds The Third Man
        plex_search("search", summary_contains="postwar Vienna")  # Finds films set in Vienna

        # Combined title and summary search
        plex_search("search", query="noir", summary_contains="detective")

        # Advanced search with multiple filters
        plex_search(
            "advanced_search",
            query="action",
            genre=["Action", "Adventure"],
            min_year=2010,
            min_rating=7.5,
            sort_by="rating",
            sort_dir="desc"
        )

        # Get search suggestions
        plex_search("suggest", query="star")

        # Get recent searches
        plex_search("recent_searches", max_recent=20)

        # Save a search
        plex_search(
            "save_search",
            search_name="High-rated Action Movies",
            genre="Action",
            min_rating=8.0,
            min_year=2010
        )

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Configure authentication token
        - "query required": Provide search query for search operations
        - "search_name required": Provide name when saving searches
        - "Library not found": Verify library_id is correct
    """
    try:
        plex = _get_plex_service()

        if operation == "search":
            if not query and not summary_contains:
                return {
                    "success": False,
                    "error": "query or summary_contains is required for search operation",
                    "error_code": "MISSING_PARAMETER",
                    "suggestions": [
                        "Provide a search query string",
                        "Or use summary_contains to search within plot summaries",
                    ],
                }

            # Track recent search
            _recent_searches.insert(
                0,
                {
                    "query": query,
                    "library_id": library_id,
                    "media_type": media_type,
                    "summary_contains": summary_contains,
                    "timestamp": None,
                },
            )
            if len(_recent_searches) > 100:
                _recent_searches.pop()

            # If only summary_contains is provided (no query), search with broader criteria
            if summary_contains and not query:
                search_term = summary_contains.lower()
                all_items = []

                if library_id:
                    # Get all items from specific library
                    result = await plex.get_library_items(library_id=library_id, limit=1000)
                    all_items = result.get("items", [])
                else:
                    # Search across all movie/show libraries
                    libraries = await plex.get_libraries()
                    for lib in libraries:
                        # Only search movie and show libraries for summary
                        if lib.get("type") in ("movie", "show"):
                            try:
                                result = await plex.get_library_items(
                                    library_id=str(lib.get("id")),
                                    limit=500,
                                )
                                all_items.extend(result.get("items", []))
                            except Exception:
                                continue  # Skip libraries that fail

                # Filter by summary - items are dicts from get_library_items
                results = [
                    item
                    for item in all_items
                    if item.get("summary") and search_term in item.get("summary", "").lower()
                ][:limit]
            else:
                results = await plex.search_media(query=query, limit=limit, library_id=library_id)

                # Filter by summary if specified
                if summary_contains and isinstance(results, list):
                    search_term = summary_contains.lower()
                    results = [
                        item
                        for item in results
                        if item.summary and search_term in item.summary.lower()
                    ]

            return {
                "success": True,
                "operation": "search",
                "query": query,
                "summary_filter": summary_contains,
                "results": results,
                "count": len(results) if isinstance(results, list) else 0,
            }

        if operation == "advanced_search":
            if not query and not title and not genre and not actor:
                return {
                    "success": False,
                    "error": "At least one search criterion (query, title, genre, actor, etc.) is required",
                    "error_code": "MISSING_PARAMETER",
                    "suggestions": ["Provide at least one search filter"],
                }

            # Track recent search
            search_params = {
                "query": query,
                "title": title,
                "genre": genre,
                "actor": actor,
                "director": director,
                "year": year,
                "library_id": library_id,
                "media_type": media_type,
                "timestamp": None,
            }
            _recent_searches.insert(0, search_params)
            if len(_recent_searches) > 100:
                _recent_searches.pop()

            results = await plex.search_media(
                query=query,
                limit=limit,
                offset=offset,
                library_id=library_id,
                media_type=media_type,
                title=title,
                year=year,
                decade=decade,
                genre=genre,
                actor=actor,
                director=director,
                content_rating=content_rating,
                studio=studio,
                country=country,
                language=language,
                collection=collection,
                min_rating=min_rating,
                max_rating=max_rating,
                min_year=min_year,
                max_year=max_year,
                unwatched=unwatched,
                sort_by=sort_by,
                sort_dir=sort_dir,
            )
            return {
                "success": True,
                "operation": "advanced_search",
                "results": results,
                "count": results.get("total", 0) if isinstance(results, dict) else 0,
            }

        if operation == "suggest":
            if not query:
                return {
                    "success": False,
                    "error": "query is required for suggest operation",
                    "error_code": "MISSING_PARAMETER",
                    "suggestions": ["Provide a partial search query"],
                }

            # Use search with limit=1 to get suggestions
            suggestions = await plex.search_media(
                query=query, limit=min(limit, 10), library_id=library_id
            )
            return {
                "success": True,
                "operation": "suggest",
                "query": query,
                "suggestions": suggestions[:10] if isinstance(suggestions, list) else [],
                "count": len(suggestions) if isinstance(suggestions, list) else 0,
            }

        if operation == "recent_searches":
            recent = _recent_searches[:max_recent]
            return {
                "success": True,
                "operation": "recent_searches",
                "searches": recent,
                "count": len(recent),
            }

        if operation == "save_search":
            if not search_name:
                return {
                    "success": False,
                    "error": "search_name is required for save_search operation",
                    "error_code": "MISSING_PARAMETER",
                    "suggestions": ["Provide a name for the saved search"],
                }

            if not query and not title and not genre and not actor:
                return {
                    "success": False,
                    "error": "At least one search criterion is required to save a search",
                    "error_code": "MISSING_PARAMETER",
                    "suggestions": ["Provide search parameters to save"],
                }

            saved_search = {
                "name": search_name,
                "query": query,
                "title": title,
                "genre": genre,
                "actor": actor,
                "director": director,
                "year": year,
                "library_id": library_id,
                "media_type": media_type,
                "min_rating": min_rating,
                "max_rating": max_rating,
                "min_year": min_year,
                "max_year": max_year,
                "unwatched": unwatched,
                "sort_by": sort_by,
                "sort_dir": sort_dir,
            }
            _saved_searches[search_name] = saved_search

            return {
                "success": True,
                "operation": "save_search",
                "saved_search": saved_search,
                "message": f"Search '{search_name}' saved successfully",
            }

        return {
            "success": False,
            "error": f"Unknown operation: {operation}",
            "error_code": "INVALID_OPERATION",
            "suggestions": [
                "Use one of: search, advanced_search, suggest, recent_searches, save_search"
            ],
        }

    except Exception as e:
        logger.exception("Error in plex_search operation '{operation}':")
        return {
            "success": False,
            "error": str(e),
            "error_code": "EXECUTION_ERROR",
            "suggestions": [
                "Verify Plex server is accessible",
                "Check PLEX_TOKEN is set correctly",
                "Verify library_id is valid if provided",
            ],
        }
