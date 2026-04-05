"""
Vienna/Austrian context service for PlexMCP.

Provides functionality for content recommendations with Austrian cultural context.
"""

from datetime import datetime
from typing import List, Optional

from ..models.vienna import AnimeSeasonInfo, EuropeanContent, WienerRecommendation


class ViennaService:
    """Service for Vienna/Austrian context functionality."""

    def __init__(self, plex_manager):
        """Initialize with a PlexManager instance."""
        self.plex_manager = plex_manager

    async def get_wiener_recommendations(
        self, mood: str, time_context: Optional[str] = None, max_recommendations: int = 5
    ) -> List[WienerRecommendation]:
        """
        Get Vienna-context content recommendations with Austrian gemütlichkeit.

        Args:
            mood: The desired mood (e.g., 'cozy', 'festive', 'cultural')
            time_context: Time of day context ('morning', 'afternoon', 'evening')
            max_recommendations: Maximum number of recommendations to return

        Returns:
            List of WienerRecommendation objects
        """
        # Default to current time of day if not specified
        if not time_context:
            current_hour = datetime.now().hour
            if 5 <= current_hour < 12:
                time_context = "morning"
            elif 12 <= current_hour < 17:
                time_context = "afternoon"
            else:
                time_context = "evening"

        # Vienna mood mapping with Austrian efficiency
        vienna_moods = {
            "cozy": ["drama", "comedy", "romance", "family"],
            "festive": ["comedy", "music", "family", "holiday"],
            "cultural": ["documentary", "history", "biography", "art"],
            "scenic": ["travel", "documentary", "nature"],
            "classic": ["classic", "drama", "romance"],
            "modern": ["drama", "comedy", "thriller"],
        }

        # Get mood-specific genres
        target_genres = vienna_moods.get(mood.lower(), ["drama", "comedy"])

        # Get all movies and shows from the library
        all_media = await self.plex_manager.get_all_media()

        # Score and rank the media based on Vienna context
        vienna_recommendations = []
        current_month = datetime.now().month

        for item in all_media:
            title = item.get("title", "").lower()
            genre = item.get("genre", "").lower()
            rating = float(item.get("rating", 0))
            duration = int(item.get("duration", 0) / 60000)  # Convert ms to minutes

            # Initial score based on genre match
            genre_score = 1.0 if any(g in genre for g in target_genres) else 0.0

            # Base score starts with genre match
            vienna_score = genre_score * 2.0

            # Rating bonus (Austrians appreciate quality)
            if rating >= 8.0:
                vienna_score += 1.0
            elif rating >= 7.0:
                vienna_score += 0.5

            # Seasonal context (Austrian cultural awareness)
            seasonal_bonus = 0
            if current_month in [12, 1, 2] and "christmas" in title:
                seasonal_bonus = 1.0
            elif current_month in [3, 4, 5] and "spring" in title:
                seasonal_bonus = 0.5

            vienna_score += seasonal_bonus

            # Austrian/European content bonus
            austrian_context = None
            if any(word in title for word in ["vienna", "austria", "salzburg", "mozart"]):
                vienna_score += 2.0
                austrian_context = "Direct Austrian reference"
            elif any(word in title for word in ["german", "deutschland", "berlin"]):
                vienna_score += 1.0
                austrian_context = "German-speaking region"
            elif any(word in title for word in ["european", "eu", "europe"]):
                vienna_score += 0.5
                austrian_context = "European context"

            # Time context adjustment
            time_bonus = 0
            if (time_context == "morning" and duration <= 60) or (
                time_context == "evening" and duration > 60
            ):
                time_bonus = 0.5

            vienna_score += time_bonus

            # Create recommendation if score is above threshold
            if vienna_score >= 1.5:  # Minimum threshold for recommendations
                recommendation = WienerRecommendation(
                    media_key=item.get("key", ""),
                    title=item.get("title", "Unknown"),
                    type=item.get("type", "movie"),
                    year=item.get("year"),
                    duration=duration,
                    rating=rating,
                    vienna_score=round(vienna_score, 2),
                    mood_match=mood,
                    austrian_context=austrian_context,
                    recommendation_reason=self._get_recommendation_reason(
                        vienna_score, genre_score, seasonal_bonus, time_bonus, austrian_context
                    ),
                    best_time=time_context,
                )
                vienna_recommendations.append(recommendation)

        # Sort by score and return top recommendations
        vienna_recommendations.sort(key=lambda x: x.vienna_score, reverse=True)
        return vienna_recommendations[:max_recommendations]

    def _get_recommendation_reason(
        self,
        score: float,
        genre_score: float,
        seasonal_bonus: float,
        time_bonus: float,
        austrian_context: Optional[str],
    ) -> str:
        """Generate a human-readable reason for the recommendation."""
        reasons = []

        if genre_score > 0:
            reasons.append("matches your selected mood")

        if seasonal_bonus > 0:
            reasons.append("perfect for the current season")

        if time_bonus > 0:
            reasons.append("ideal for this time of day")

        if austrian_context:
            reasons.append(f"features {austrian_context.lower()}")

        if not reasons:
            reasons.append("a solid choice")

        return f"This is {' and '.join(reasons)}."

    async def find_european_content(
        self,
        country: Optional[str] = None,
        genre: Optional[str] = None,
        language: str = "any",
        max_results: int = 15,
    ) -> List[EuropeanContent]:
        """
        Discover European cinema and content with Austrian cultural perspective.

        Args:
            country: Filter by country of origin (e.g., 'Austria', 'Germany')
            genre: Filter by genre
            language: Filter by language
            max_results: Maximum number of results to return

        Returns:
            List of EuropeanContent objects
        """
        # Implementation will be added in the next step

    async def get_anime_season_info(self) -> List[AnimeSeasonInfo]:
        """
        Get information about current anime seasons with Austrian efficiency.

        Returns:
            List of AnimeSeasonInfo objects
        """
        # Implementation will be added in the next step
