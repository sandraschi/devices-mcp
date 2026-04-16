"""
Vienna-specific models for PlexMCP.

This module contains models related to the Austrian/Vienna-specific functionality
that was referenced in the project's models/__init__.py file.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class WienerRecommendation(BaseModel):
    """Model for Viennese cultural recommendations."""

    title: str = Field(..., description="Title of the recommended content")
    description: str = Field(..., description="Description of the recommendation")
    category: str = Field(..., description="Category of the recommendation")
    location: str = Field(..., description="Location in Vienna")
    start_date: datetime | None = Field(None, description="Start date and time")
    end_date: datetime | None = Field(None, description="End date and time")


class EuropeanContent(BaseModel):
    """Model for European cultural content."""

    title: str = Field(..., description="Title of the content")
    country: str = Field(..., description="Country of origin")
    language: str = Field(..., description="Original language")
    year: int = Field(..., description="Release year")
    is_eu_funded: bool = Field(False, description="Whether the content received EU funding")


class AnimeSeasonInfo(BaseModel):
    """Model for anime season information."""

    title: str = Field(..., description="Anime title")
    season_number: int = Field(..., description="Season number")
    episode_count: int = Field(..., description="Number of episodes")
    year: int = Field(..., description="Release year")
    studio: str = Field(..., description="Production studio")
    is_viennese_dub: bool = Field(False, description="Has Viennese German dub")


# Add any additional Vienna-specific models below
