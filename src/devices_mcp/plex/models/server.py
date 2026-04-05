"""Pydantic models for Plex server status and information."""

from pydantic import BaseModel, Field


class PlexServerStatus(BaseModel):
    """Model representing Plex server status and information."""

    name: str = Field(..., description="Friendly name of the Plex server")
    version: str = Field(..., description="Plex server version")
    platform: str = Field(..., description="Platform the server is running on")
    updated_at: int = Field(..., description="Timestamp of last server update")
    size: int = Field(0, description="Size of the Plex database in bytes")
    my_plex_username: str = Field("", description="Plex account username")
    my_plex_mapping_state: str = Field("", description="Plex account mapping state")
    connected: bool = Field(False, description="Connection status to Plex services")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "My Plex Server",
                "version": "1.40.0",
                "platform": "Linux",
                "updated_at": 1699027200,
                "size": 2147483648,
                "my_plex_username": "user@example.com",
                "my_plex_mapping_state": "mapped",
                "connected": True,
            }
        }
