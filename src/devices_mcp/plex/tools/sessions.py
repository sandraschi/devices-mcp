"""Plex session management tools for FastMCP 2.10.1."""

import os

from pydantic import BaseModel, Field

from ..app import mcp
from ..models.session import Session


def _get_plex_service():
    from ..services.plex_service import PlexService

    base_url = os.getenv("PLEX_URL") or os.getenv("PLEX_SERVER_URL", "http://localhost:32400")
    token = os.getenv("PLEX_TOKEN")
    if not token:
        raise RuntimeError("PLEX_TOKEN environment variable is required")
    return PlexService(base_url=base_url, token=token)


@mcp.tool()
async def list_sessions() -> list[Session]:
    """Get a list of all active Plex sessions.

    Returns:
        List of active sessions with client and playback information
    """
    plex = _get_plex_service()
    return await plex.get_sessions()


class ClientInfo(BaseModel):
    """Information about a Plex client."""

    id: str = Field(..., description="Client identifier")
    name: str = Field(..., description="Client name")
    product: str = Field(..., description="Client product name")
    platform: str = Field(..., description="Client platform")
    local: bool = Field(..., description="Whether the client is on the local network")


@mcp.tool()
async def list_clients() -> list[ClientInfo]:
    """Get a list of all available Plex clients.

    Returns:
        List of available Plex clients
    """
    plex = _get_plex_service()
    clients = await plex.get_clients()
    return [
        ClientInfo(
            id=client["machine_identifier"],
            name=client["name"],
            product=client["product"],
            platform=client["platform"],
            local=client["local"],
        )
        for client in clients
    ]


class PlaybackControlRequest(BaseModel):
    """Request model for controlling playback."""

    client_id: str = Field(..., description="ID of the client to control")
    action: str = Field(
        ...,
        description="Action to perform (play, pause, stop, skip_next, skip_previous, step_forward, step_back, seek_to)",
    )
    media_key: str | None = Field(None, description="Media key to play (required for play action)")
    seek_to: int | None = Field(None, description="Position in milliseconds to seek to (for seek_to action)")
    offset: int | None = Field(30, description="Time offset in seconds (for step_forward/step_back actions)")


@mcp.tool()
async def control_playback(request: PlaybackControlRequest) -> bool:
    """Control playback on a Plex client.

    Args:
        request: Playback control request

    Returns:
        bool: True if the operation was successful
    """
    plex = _get_plex_service()
    return await plex.control_playback(
        client_identifier=request.client_id,
        action=request.action,
        media_key=request.media_key,
        seek_to=request.seek_to,
        offset=request.offset,
    )
