"""
Playback-related API endpoints for PlexMCP.

This module contains API endpoints for managing Plex playback, sessions, and clients.
"""

# Import the shared FastMCP instance from the package level
# Import models
from ..models import (
    CastRequest,
    PlaybackControlResult,
    PlexClient,
    PlexSession,
    RemotePlaybackRequest,
)


async def get_clients() -> list[PlexClient]:
    """
    Get all available Plex client devices.

    Returns information about connected Plex clients that can
    be used for remote playback control.

    Returns:
        List of available Plex client devices

    Raises:
        RuntimeError: If there's an error fetching client information
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        clients = await plex.get_clients()

        return [
            PlexClient(
                name=client.get("name", "Unknown Client"),
                host=client.get("host", ""),
                machine_identifier=client.get("machineIdentifier", ""),
                product=client.get("product", ""),
                platform=client.get("platform", ""),
                platform_version=client.get("platformVersion", ""),
                device=client.get("device", ""),
            )
            for client in clients
        ]

    except Exception as e:
        raise RuntimeError(f"Error fetching clients: {e!s}") from e


async def get_sessions() -> list[PlexSession]:
    """
    Get active playback sessions on the Plex server.

    Shows who is currently watching what content,
    including playback progress and player information.

    Returns:
        List of active playback sessions

    Raises:
        RuntimeError: If there's an error fetching active sessions
    """
    from ..services.plex_service import PlexService

    try:
        plex = PlexService()
        sessions = await plex.get_sessions()

        return [
            PlexSession(
                session_key=str(session.get("session_key", "")),
                user=session.get("user", "Unknown User"),
                player=session.get("player", "Unknown Player"),
                state=session.get("state", "unknown"),
                title=session.get("title", "Unknown Title"),
                progress=int(session.get("view_offset", 0) / 1000),  # Convert ms to seconds
                duration=int(session.get("duration", 0) / 1000),  # Convert ms to seconds
            )
            for session in sessions
        ]

    except Exception as e:
        raise RuntimeError(f"Error fetching active sessions: {e!s}") from e


async def control_playback(request: RemotePlaybackRequest) -> PlaybackControlResult:
    """
    Control playback on a remote Plex client.

    Args:
        request: Remote playback control request

    Returns:
        Result of the playback control operation
    """
    # TODO: Implement actual Plex service call
    # Removed print statements - use logger instead for MCP stdio compatibility

    return PlaybackControlResult(
        status="success",
        client_id=request.client_id,
        action=request.action,
        current_state="playing",
        position=1800000,  # 30 minutes in milliseconds
        duration=7200000,  # 2 hours in milliseconds
        volume=75,
        message=f"Successfully executed {request.action} on {request.client_id}",
    )


async def cast_media(request: CastRequest) -> PlaybackControlResult:
    """
    Cast media to a Plex client.

    Args:
        request: Cast request with media and client information

    Returns:
        Result of the cast operation
    """
    # TODO: Implement actual Plex service call
    # Removed print statements - use logger instead for MCP stdio compatibility

    return PlaybackControlResult(
        status="success",
        client_id=request.client_id,
        action="play_media",
        current_state="playing",
        position=0,
        duration=7200000,  # 2 hours in milliseconds
        volume=50,
        message=f"Successfully cast media to {request.client_id}",
    )


# No need to export app - tools are registered with the shared mcp instance
