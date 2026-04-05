"""
PlexMCP Streaming/Playback Control Portmanteau Tool

Consolidates all playback control and session management operations into a single comprehensive interface.
FastMCP 2.13+ compliant with comprehensive docstrings and AI-friendly error messages.
"""

import os
from typing import Any, Dict, Literal, Optional

from ...app import mcp
from ...utils import get_logger

logger = get_logger(__name__)


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
async def plex_streaming(
    operation: Literal[
        "list_sessions",
        "list_clients",
        "play",
        "pause",
        "stop",
        "seek",
        "skip_next",
        "skip_previous",
        "set_quality",
        "set_volume",
        "control",
    ],
    client_id: Optional[str] = None,
    media_key: Optional[str] = None,
    seek_to: Optional[int] = None,
    offset: Optional[int] = 30,
    action: Optional[str] = None,
    volume: Optional[int] = None,
    quality: Optional[str] = None,
) -> Dict[str, Any]:
    """Comprehensive playback control and session management operations for Plex Media Server.

    PORTMANTEAU PATTERN RATIONALE:
    Instead of creating 10+ separate tools (one per operation), this tool consolidates related
    playback control and session management operations into a single interface. This design:
    - Prevents tool explosion (10+ tools → 1 tool) while maintaining full functionality
    - Improves discoverability by grouping related operations together
    - Reduces cognitive load when working with playback control tasks
    - Enables consistent playback interface across all operations
    - Follows FastMCP 2.13+ best practices for feature-rich MCP servers

    SUPPORTED OPERATIONS:
    - list_sessions: List all active Plex sessions
    - list_clients: List all available Plex clients
    - play: Play media on a client
    - pause: Pause playback on a client
    - stop: Stop playback on a client
    - seek: Seek to a specific position in the current media
    - skip_next: Skip to the next item in the play queue
    - skip_previous: Skip to the previous item in the play queue
    - set_quality: Set streaming quality settings (placeholder for future implementation)
    - set_volume: Set the volume of a Plex client (0-100)
    - control: Generic playback control with action parameter

    OPERATIONS DETAIL:

    list_sessions: List all active Plex sessions
    - Parameters: None required
    - Returns: List of active sessions with client and playback information
    - Example: plex_streaming(operation="list_sessions")
    - Use when: You want to see what's currently playing

    list_clients: List all available Plex clients
    - Parameters: None required
    - Returns: List of available Plex clients
    - Example: plex_streaming(operation="list_clients")
    - Use when: You want to see available clients to control

    play: Play media on a client
    - Parameters: client_id (required), media_key (required)
    - Returns: Success confirmation
    - Example: plex_streaming(operation="play", client_id="abc123", media_key="12345")
    - Use when: Starting playback on a specific client

    pause: Pause playback on a client
    - Parameters: client_id (required)
    - Returns: Success confirmation
    - Example: plex_streaming(operation="pause", client_id="abc123")
    - Use when: Pausing current playback

    stop: Stop playback on a client
    - Parameters: client_id (required)
    - Returns: Success confirmation
    - Example: plex_streaming(operation="stop", client_id="abc123")
    - Use when: Stopping current playback

    seek: Seek to a specific position in the current media
    - Parameters: client_id (required), seek_to (required, milliseconds)
    - Returns: Success confirmation
    - Example: plex_streaming(operation="seek", client_id="abc123", seek_to=60000)
    - Use when: Jumping to a specific time in the media

    skip_next: Skip to the next item in the play queue
    - Parameters: client_id (required)
    - Returns: Success confirmation
    - Example: plex_streaming(operation="skip_next", client_id="abc123")
    - Use when: Moving to the next item in queue

    skip_previous: Skip to the previous item in the play queue
    - Parameters: client_id (required)
    - Returns: Success confirmation
    - Example: plex_streaming(operation="skip_previous", client_id="abc123")
    - Use when: Moving to the previous item in queue

    set_quality: Set streaming quality settings
    - Parameters: client_id (required), quality (required)
    - Returns: Success confirmation
    - Example: plex_streaming(operation="set_quality", client_id="abc123", quality="1080p")
    - Use when: Changing streaming quality (NOTE: May not be fully supported by Plex API)

    control: Generic playback control with action parameter
    - Parameters: client_id (required), action (required), media_key (optional), seek_to (optional), offset (optional)
    - Returns: Success confirmation
    - Example: plex_streaming(operation="control", client_id="abc123", action="play", media_key="12345")
    - Use when: Using a custom action or when other operations don't fit

    Prerequisites:
        - Plex Media Server running and accessible
        - Valid PLEX_TOKEN environment variable set
        - At least one active client for playback operations

    Args:
        operation (str): The streaming operation to perform. Required. Must be one of: "list_sessions", "list_clients", "play", "pause", "stop", "seek", "skip_next", "skip_previous", "set_quality", "control"
        client_id (str | None): Client identifier. Required for: play, pause, stop, seek, skip_next, skip_previous, set_quality, control. Use list_clients to find IDs.
        media_key (str | None): Media item key/ID. Required for: play. Optional for: control ("play" action). Obtained from plex_media results.
        seek_to (int | None): Position in milliseconds to seek to. Required for: seek. Optional for: control ("seek_to" action).
        offset (int | None): Time offset in seconds. Optional for: control ("step_forward" or "step_back" action). Default: 30.
        action (str | None): Action to perform. Required for: control. Valid: play, pause, stop, skip_next, skip_previous, step_forward, step_back, seek_to.
        quality (str | None): Quality setting. Required for: set_quality. Examples: "1080p", "720p", "480p".

    Returns:
        Dictionary containing:
            - success: Boolean indicating operation success
            - operation: The operation that was performed
            - data: Operation-specific result data
            - count: Number of sessions/clients returned (for list operations)
            - error: Error message if success is False
            - error_code: Specific error code for programmatic handling
            - suggestions: List of suggested fixes (on error)

    Examples:
        # List active sessions
        result = await plex_streaming(operation="list_sessions")
        # Returns: {'success': True, 'operation': 'list_sessions', 'data': [...], 'count': 2}

        # List available clients
        result = await plex_streaming(operation="list_clients")
        # Returns: {'success': True, 'operation': 'list_clients', 'data': [...], 'count': 5}

        # Play media on a client
        result = await plex_streaming(operation="play", client_id="abc123", media_key="12345")
        # Returns: {'success': True, 'operation': 'play'}

        # Pause playback
        result = await plex_streaming(operation="pause", client_id="abc123")
        # Returns: {'success': True, 'operation': 'pause'}

        # Seek to position
        result = await plex_streaming(operation="seek", client_id="abc123", seek_to=60000)
        # Returns: {'success': True, 'operation': 'seek'}

        # Generic control
        result = await plex_streaming(operation="control", client_id="abc123", action="skip_next")
        # Returns: {'success': True, 'operation': 'control'}

    Errors:
        Common errors and solutions:
        - "PLEX_TOKEN not set": Set PLEX_TOKEN environment variable with your auth token
        - "client_id required": Provide valid client ID for operations that require it
        - "Client not found": Use plex_streaming(operation="list_clients") to find valid client IDs
        - "Media key required": Provide media_key for play operation
        - "Invalid action": Use valid action values for control operation

    See Also:
        - plex_media: For browsing and searching media to play
        - plex_library: For library management operations
    """
    try:
        plex = _get_plex_service()

        # Operation: list_sessions
        if operation == "list_sessions":
            sessions = await plex.get_sessions()
            return {
                "success": True,
                "operation": "list_sessions",
                "data": sessions,
                "count": len(sessions) if isinstance(sessions, list) else 0,
            }

        # Operation: list_clients
        if operation == "list_clients":
            clients = await plex.get_clients()
            return {
                "success": True,
                "operation": "list_clients",
                "data": clients,
                "count": len(clients) if isinstance(clients, list) else 0,
            }

        # Operation: play (can auto-select client, so check before requiring client_id)
        if operation == "play":
            if not media_key:
                return {
                    "success": False,
                    "error": "media_key is required for play operation",
                    "error_code": "MISSING_MEDIA_KEY",
                    "suggestions": [
                        "Get media_key from plex_media(operation='browse') or plex_media(operation='search')",
                        "Provide media_key parameter",
                    ],
                }

            # Auto-select client if not provided
            if not client_id:
                # Get media type to select appropriate client
                media_type = await plex._run_in_executor(plex._get_media_type, media_key)
                if not media_type:
                    return {
                        "success": False,
                        "error": "Could not determine media type. Please provide client_id explicitly.",
                        "error_code": "MEDIA_TYPE_UNKNOWN",
                        "suggestions": [
                            "Provide client_id parameter explicitly",
                            "Use plex_streaming(operation='list_clients') to see available clients",
                        ],
                    }

                # Get all clients
                all_clients = await plex.get_clients()
                if not all_clients:
                    return {
                        "success": False,
                        "error": "No clients available",
                        "error_code": "NO_CLIENTS",
                        "suggestions": [
                            "Ensure at least one Plex client is open and connected",
                            "Try plex_streaming(operation='list_clients') to check available clients",
                        ],
                    }

                # Select best client for this media type
                selected_client = await plex._run_in_executor(
                    plex._select_client_for_media, media_type, all_clients
                )
                if not selected_client:
                    return {
                        "success": False,
                        "error": "Could not select appropriate client",
                        "error_code": "CLIENT_SELECTION_FAILED",
                        "suggestions": [
                            "Provide client_id parameter explicitly",
                            f"Available clients: {[c.get('name') for c in all_clients]}",
                        ],
                    }

                client_id = selected_client.get("machineIdentifier") or selected_client.get("id")
                logger.info(
                    f"Auto-selected client '{selected_client.get('name')}' ({selected_client.get('product')}) for {media_type} media"
                )

            result = await plex.control_playback(
                client_identifier=client_id,
                action="play",
                media_key=media_key,
            )
            return {
                "success": result,
                "operation": "play",
                "client_id": client_id,
                "media_key": media_key,
                "data": {"played": result},
            }

        # All other operations require client_id
        if not client_id:
            return {
                "success": False,
                "error": f"client_id is required for {operation} operation",
                "error_code": "MISSING_CLIENT_ID",
                "suggestions": [
                    "Use plex_streaming(operation='list_clients') to find available client IDs",
                    f"Provide client_id parameter: plex_streaming(operation='{operation}', client_id='...')",
                ],
            }

        # Operation: pause
        if operation == "pause":
            result = await plex.control_playback(
                client_identifier=client_id,
                action="pause",
            )
            return {
                "success": result,
                "operation": "pause",
                "client_id": client_id,
                "data": {"paused": result},
            }

        # Operation: stop
        if operation == "stop":
            result = await plex.control_playback(
                client_identifier=client_id,
                action="stop",
            )
            return {
                "success": result,
                "operation": "stop",
                "client_id": client_id,
                "data": {"stopped": result},
            }

        # Operation: seek
        if operation == "seek":
            if seek_to is None:
                return {
                    "success": False,
                    "error": "seek_to is required for seek operation",
                    "error_code": "MISSING_SEEK_TO",
                    "suggestions": ["Provide seek_to parameter (position in milliseconds)"],
                }

            result = await plex.control_playback(
                client_identifier=client_id,
                action="seek_to",
                seek_to=seek_to,
            )
            return {
                "success": result,
                "operation": "seek",
                "client_id": client_id,
                "seek_to": seek_to,
                "data": {"seeked": result},
            }

        # Operation: skip_next
        if operation == "skip_next":
            result = await plex.control_playback(
                client_identifier=client_id,
                action="skip_next",
            )
            return {
                "success": result,
                "operation": "skip_next",
                "client_id": client_id,
                "data": {"skipped": result},
            }

        # Operation: skip_previous
        if operation == "skip_previous":
            result = await plex.control_playback(
                client_identifier=client_id,
                action="skip_previous",
            )
            return {
                "success": result,
                "operation": "skip_previous",
                "client_id": client_id,
                "data": {"skipped": result},
            }

        # Operation: set_quality
        if operation == "set_quality":
            if not quality:
                return {
                    "success": False,
                    "error": "quality is required for set_quality operation",
                    "error_code": "MISSING_QUALITY",
                    "suggestions": ["Provide quality parameter (e.g., '1080p', '720p', '480p')"],
                }

            # Note: Plex API may have limited support for quality settings
            # This is a placeholder implementation
            return {
                "success": False,
                "error": "set_quality operation is not yet fully implemented",
                "error_code": "NOT_IMPLEMENTED",
                "suggestions": [
                    "Use plex_performance tool for quality profile management",
                    "Quality settings may need to be configured via Plex Web App",
                ],
            }

        # Operation: set_volume
        if operation == "set_volume":
            if not client_id:
                return {
                    "success": False,
                    "error": "client_id is required for set_volume operation",
                    "error_code": "MISSING_CLIENT_ID",
                }
            if volume is None:
                return {
                    "success": False,
                    "error": "volume is required for set_volume operation",
                    "error_code": "MISSING_VOLUME",
                }

            result = await plex.control_playback(
                client_identifier=client_id, action="set_volume", volume=volume
            )
            return {
                "success": result,
                "operation": "set_volume",
                "client_id": client_id,
                "volume": volume,
            }

        # Operation: control
        if operation == "control":
            if not action:
                return {
                    "success": False,
                    "error": "action is required for control operation",
                    "error_code": "MISSING_ACTION",
                    "suggestions": [
                        "Provide action parameter: play, pause, stop, skip_next, skip_previous, step_forward, step_back, seek_to, set_volume",
                    ],
                }

            valid_actions = [
                "play",
                "pause",
                "stop",
                "skip_next",
                "skip_previous",
                "step_forward",
                "step_back",
                "seek_to",
                "set_volume",
            ]
            if action not in valid_actions:
                return {
                    "success": False,
                    "error": f"Invalid action: '{action}'",
                    "error_code": "INVALID_ACTION",
                    "suggestions": [
                        f"Valid actions: {', '.join(valid_actions)}",
                        f"You provided: '{action}'",
                    ],
                }

            # Build kwargs for control_playback
            kwargs = {}
            if media_key:
                kwargs["media_key"] = media_key
            if seek_to is not None:
                kwargs["seek_to"] = seek_to
            if offset is not None:
                kwargs["offset"] = offset
            if volume is not None:
                kwargs["volume"] = volume

            result = await plex.control_playback(
                client_identifier=client_id,
                action=action,
                **kwargs,
            )
            return {
                "success": result,
                "operation": "control",
                "client_id": client_id,
                "action": action,
                "data": {"controlled": result},
            }

        return {
            "success": False,
            "error": f"Invalid operation: '{operation}'",
            "error_code": "INVALID_OPERATION",
            "suggestions": [
                "Valid operations: list_sessions, list_clients, play, pause, stop, seek, skip_next, skip_previous, set_quality, control",
                f"You provided: '{operation}'",
            ],
        }

    except RuntimeError as e:
        error_msg = str(e)
        suggestions = []

        if "PLEX_TOKEN" in error_msg:
            suggestions = [
                "Set PLEX_TOKEN environment variable",
                "Get token from: Plex Web App → Settings → Account → Authorized Devices",
                "Or visit: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/",
            ]
        elif "not found" in error_msg.lower():
            suggestions = [
                "Verify the client_id is correct",
                "Use plex_streaming(operation='list_clients') to find valid client IDs",
            ]

        return {
            "success": False,
            "error": error_msg,
            "error_code": "RUNTIME_ERROR",
            "operation": operation,
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.error(
            f"Unexpected error in plex_streaming operation '{operation}': {e}",
            exc_info=True,
        )
        return {
            "success": False,
            "error": f"Unexpected error during {operation}: {e!s}",
            "error_code": "UNEXPECTED_ERROR",
            "operation": operation,
            "suggestions": [
                "Check server logs for detailed error information",
                "Verify all required parameters are provided",
                "Try the operation again with valid parameters",
            ],
        }
