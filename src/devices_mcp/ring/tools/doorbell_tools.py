"""
Ring Doorbell Management Tools - FastMCP 3.1

Comprehensive doorbell operations including video streaming, audio communication,
visitor management, and motion detection. Handles both wired and battery doorbells.

This module uses FastMCP 3.1 patterns with multiline decorators and proper
tool registration for Claude Desktop stdio communication.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from fastmcp import FastMCP

from ..core.exceptions import StreamingError
from ..core.ring_client import RingClient

logger = logging.getLogger(__name__)


def register_tools(app: FastMCP) -> None:
    """Register doorbell management tools with the FastMCP application.

    Uses FastMCP 3.1 patterns with multiline decorators and proper
    stdio communication support for Claude Desktop integration.

    Args:
        app: FastMCP application instance
    """

    @app.tool(
        name="get_doorbell_status",
        description="Get comprehensive status of all Ring doorbells in the system",
    )
    async def get_doorbell_status() -> Dict[str, Any]:
        """Get comprehensive status of all Ring doorbells in the system.

        Provides detailed information about doorbell health, connectivity, settings,
        and current operational status. Essential for monitoring doorbell functionality
        and diagnosing issues before they affect security coverage.

        Returns:
            Dict containing:
            - doorbells: List of all doorbells with detailed status
            - summary: Overall doorbell system health
            - recommendations: Maintenance or configuration suggestions
        """
        try:
            client = RingClient()
            doorbells = client.get_devices_by_type("doorbell")

            doorbell_status = []
            offline_count = 0

            for doorbell in doorbells:
                device_info = client.get_device_details(doorbell.id)

                if not device_info.get("online", False):
                    offline_count += 1

                doorbell_info = {
                    "device_id": doorbell.id,
                    "name": device_info.get("name", "Ring Doorbell"),
                    "model": device_info.get("model", "Unknown"),
                    "online": device_info.get("online", False),
                    "battery_level": device_info.get("battery_level"),
                    "signal_strength": device_info.get("signal_strength"),
                    "motion_detection_enabled": device_info.get("motion_detection_enabled", False),
                }
                doorbell_status.append(doorbell_info)

            return {
                "success": True,
                "doorbells": doorbell_status,
                "summary": {
                    "total_doorbells": len(doorbell_status),
                    "online_doorbells": len(doorbell_status) - offline_count,
                    "offline_doorbells": offline_count,
                },
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.exception("Error getting doorbell status:")
            return {"success": False, "error": str(e)}

    @app.tool(
        name="get_doorbell_live_stream", description="Get live video stream from Ring doorbell"
    )
    def get_doorbell_live_stream(
        doorbell_id: Optional[str] = None,
        quality: Literal["low", "medium", "high"] = "high",
        duration_seconds: int = 30,
    ) -> Dict[str, Any]:
        """Start live video stream from Ring doorbell with configurable quality.

        Initiates a live video stream from the specified doorbell for real-time monitoring.
        Supports multiple quality levels to balance bandwidth usage with video clarity.

        Args:
            doorbell_id: Specific doorbell ID (uses primary if not specified)
            quality: Video quality level ('low', 'medium', 'high')
            duration_seconds: Maximum stream duration (default: 30 seconds)

        Returns:
            Dict containing:
            - stream_url: Video stream URL for playback
            - stream_id: Unique identifier for this stream session
            - quality_settings: Applied video quality parameters
            - stream_expires_at: When the stream will automatically end
        """
        try:
            client = RingClient()

            # Get target doorbell
            if doorbell_id:
                doorbell = client.get_device(doorbell_id)
                if not doorbell:
                    return {"success": False, "error": f"Doorbell with ID {doorbell_id} not found"}
            else:
                doorbells = client.get_devices_by_type("doorbell")
                if not doorbells:
                    return {"success": False, "error": "No doorbells found in system"}
                doorbell = doorbells[0]

            # Quality settings
            quality_config = {
                "low": {"resolution": "480p", "bitrate": 500},
                "medium": {"resolution": "720p", "bitrate": 1000},
                "high": {"resolution": "1080p", "bitrate": 2000},
            }

            stream_settings = quality_config.get(quality, quality_config["high"])

            # Start live stream
            stream_result = client.start_live_stream(
                device_id=doorbell.id,
                quality_settings=stream_settings,
                max_duration=duration_seconds,
            )

            # Calculate expiration time
            expires_at = (datetime.now() + timedelta(seconds=duration_seconds)).isoformat()

            return {
                "success": True,
                "doorbell_id": doorbell.id,
                "doorbell_name": doorbell.name,
                "stream_url": stream_result.get("stream_url"),
                "stream_id": stream_result.get("stream_id"),
                "quality_settings": stream_settings,
                "duration_seconds": duration_seconds,
                "stream_expires_at": expires_at,
                "stream_started_at": datetime.now().isoformat(),
            }

        except StreamingError as e:
            logger.exception("Streaming error:")
            return {
                "success": False,
                "error": f"Failed to start stream: {e!s}",
                "error_type": "streaming",
            }
        except Exception as e:
            logger.exception("Error starting live stream:")
            return {"success": False, "error": str(e)}

    @app.tool(
        name="answer_doorbell_call",
        description="Answer an active doorbell call with two-way audio communication",
    )
    def answer_doorbell_call(
        doorbell_id: Optional[str] = None,
        enable_two_way_audio: bool = True,
        auto_record: bool = True,
    ) -> Dict[str, Any]:
        """Answer an active doorbell call with two-way audio communication.

        Responds to an active doorbell press by establishing two-way audio communication
        with the visitor. Allows you to speak with visitors remotely and optionally
        record the conversation for security purposes.

        This is essential for package deliveries, visitor screening, and emergency
        situations when you cannot physically answer the door.

        Args:
            doorbell_id: Specific doorbell ID (uses primary if not specified)
            enable_two_way_audio: Enable bidirectional audio communication
            auto_record: Automatically record the conversation

        Returns:
            Dict containing:
            - call_session_id: Unique identifier for this call session
            - audio_stream_url: Audio stream for communication
            - visitor_snapshot: Image of visitor (if available)
            - call_started_at: Timestamp when call was answered
            - recording_enabled: Whether conversation is being recorded
        """
        try:
            client = RingClient()

            # Get target doorbell
            if doorbell_id:
                doorbell = client.get_device(doorbell_id)
            else:
                doorbells = client.get_devices_by_type("doorbell")
                if not doorbells:
                    return {"success": False, "error": "No doorbells found in system"}
                doorbell = doorbells[0]

            # Check for active doorbell call
            active_calls = client.get_active_calls(doorbell.id)
            if not active_calls:
                return {
                    "success": False,
                    "error": "No active doorbell call to answer",
                    "suggestion": "Use get_doorbell_events() to check recent doorbell activity",
                }

            active_call = active_calls[0]

            # Answer the call
            call_result = client.answer_call(
                call_id=active_call["call_id"],
                enable_two_way_audio=enable_two_way_audio,
                record_conversation=auto_record,
            )

            # Get visitor snapshot if available
            visitor_snapshot = None
            if active_call.get("snapshot_url"):
                visitor_snapshot = {
                    "url": active_call["snapshot_url"],
                    "timestamp": active_call.get("timestamp"),
                }

            return {
                "success": True,
                "doorbell_id": doorbell.id,
                "call_session_id": call_result.get("session_id"),
                "audio_stream_url": call_result.get("audio_stream_url"),
                "two_way_audio_enabled": enable_two_way_audio,
                "recording_enabled": auto_record,
                "visitor_snapshot": visitor_snapshot,
                "call_started_at": datetime.now().isoformat(),
                "call_duration_limit": call_result.get("max_duration_seconds", 300),
                "instructions": "Use the audio stream URL to establish communication with visitor",
            }

        except Exception as e:
            logger.exception("Error answering doorbell call:")
            return {"success": False, "error": str(e)}

    @app.tool(
        name="get_visitor_history",
        description="Get comprehensive visitor history with snapshots and event details",
    )
    def get_visitor_history(
        hours: int = 24, include_snapshots: bool = True, motion_only: bool = False
    ) -> Dict[str, Any]:
        """Get comprehensive visitor history with snapshots and event details.

        Retrieves detailed history of doorbell activity including visitor events,
        motion detection, and doorbell presses. Essential for security monitoring,
        identifying frequent visitors, and reviewing missed visitors.

        Includes timestamps, event types, visitor snapshots, and interaction details.
        Use this to track delivery patterns, identify suspicious activity, or
        review security incidents at your front door.

        Args:
            hours: Number of hours of history to retrieve (default: 24)
            include_snapshots: Whether to include visitor snapshot images
            motion_only: Filter to show only motion events (exclude doorbell presses)

        Returns:
            Dict containing:
            - visitor_events: Chronological list of visitor activity
            - summary: Statistics and patterns for the time period
            - frequent_visitors: Analysis of repeat visitors (if identifiable)
            - peak_activity_times: When most visitor activity occurs
        """
        try:
            client = RingClient()

            # Get all doorbells
            doorbells = client.get_devices_by_type("doorbell")
            if not doorbells:
                return {"success": False, "error": "No doorbells found in system"}

            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours)

            all_events = []

            # Get events from each doorbell
            for doorbell in doorbells:
                doorbell_events = client.get_doorbell_events(
                    device_id=doorbell.id,
                    start_time=start_time,
                    end_time=end_time,
                    motion_only=motion_only,
                )

                # Add doorbell info to each event
                for event in doorbell_events:
                    event["doorbell_id"] = doorbell.id
                    event["doorbell_name"] = doorbell.name

                    # Add snapshot if requested and available
                    if include_snapshots and event.get("snapshot_id"):
                        snapshot_url = client.get_snapshot_url(event["snapshot_id"])
                        event["visitor_snapshot"] = {
                            "url": snapshot_url,
                            "thumbnail_url": client.get_thumbnail_url(event["snapshot_id"]),
                        }

                all_events.extend(doorbell_events)

            # Sort events chronologically (newest first)
            all_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            # Analyze patterns
            event_types = {}
            hourly_activity = [0] * 24  # 24-hour activity pattern

            for event in all_events:
                event_type = event.get("event_type", "unknown")
                event_types[event_type] = event_types.get(event_type, 0) + 1

                # Extract hour for activity pattern
                try:
                    event_datetime = datetime.fromisoformat(event.get("timestamp", ""))
                    hour = event_datetime.hour
                    hourly_activity[hour] += 1
                except:
                    pass

            # Find peak activity hours
            peak_hours = []
            max_activity = max(hourly_activity) if hourly_activity else 0
            for hour, activity in enumerate(hourly_activity):
                if activity == max_activity and max_activity > 0:
                    peak_hours.append(f"{hour:02d}:00")

            # Identify frequent visitors (basic analysis based on timing patterns)
            frequent_visitors = []
            if len(all_events) > 5:
                # Group events by similar time patterns (very basic implementation)
                time_clusters = {}
                for event in all_events:
                    try:
                        event_time = datetime.fromisoformat(event.get("timestamp", ""))
                        hour_minute = f"{event_time.hour:02d}:{event_time.minute // 15 * 15:02d}"
                        time_clusters[hour_minute] = time_clusters.get(hour_minute, 0) + 1
                    except:
                        pass

                # Find time slots with multiple visits (potential regular visitors)
                for time_slot, count in time_clusters.items():
                    if count >= 3:
                        frequent_visitors.append(
                            {
                                "time_pattern": f"Around {time_slot}",
                                "visit_count": count,
                                "pattern_type": "regular_timing",
                            }
                        )

            summary = {
                "total_events": len(all_events),
                "event_types": event_types,
                "time_period_hours": hours,
                "active_doorbells": len(doorbells),
                "peak_activity_hours": peak_hours,
                "busiest_hour": f"{hourly_activity.index(max_activity):02d}:00"
                if max_activity > 0
                else None,
                "average_events_per_hour": round(len(all_events) / hours, 1) if hours > 0 else 0,
            }

            return {
                "success": True,
                "time_range": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "hours": hours,
                },
                "visitor_events": all_events,
                "summary": summary,
                "frequent_visitors": frequent_visitors,
                "hourly_activity_pattern": hourly_activity,
                "filters_applied": {
                    "motion_only": motion_only,
                    "include_snapshots": include_snapshots,
                },
            }

        except Exception as e:
            logger.exception("Error getting visitor history:")
            return {"success": False, "error": str(e)}

    @app.tool(
        name="configure_motion_detection",
        description="Configure motion detection settings for Ring doorbell with advanced options",
    )
    def configure_motion_detection(
        doorbell_id: Optional[str] = None,
        sensitivity: Literal["low", "medium", "high"] = "medium",
        motion_zones: Optional[List[Dict[str, Any]]] = None,
        smart_alerts: bool = True,
        schedule_enabled: bool = False,
    ) -> Dict[str, Any]:
        """Configure motion detection settings for Ring doorbell with advanced options.

        Customizes motion detection behavior to optimize security coverage while
        minimizing false alerts. Supports sensitivity adjustment, custom motion zones,
        smart alerts, and scheduling for different detection behavior throughout the day.

        Proper motion configuration is crucial for effective security monitoring.
        Higher sensitivity catches more movement but may trigger on cars, animals, or
        weather. Custom zones focus detection on important areas like walkways.

        Args:
            doorbell_id: Specific doorbell ID (uses primary if not specified)
            sensitivity: Motion detection sensitivity level
            motion_zones: Custom detection zones with coordinates and names
            smart_alerts: Enable AI-powered person/package detection
            schedule_enabled: Whether to use time-based detection schedules

        Returns:
            Dict containing:
            - configuration_applied: Settings that were successfully applied
            - previous_settings: Previous configuration for comparison
            - optimization_suggestions: Recommendations for better detection
            - test_recommendations: How to test the new configuration
        """
        try:
            client = RingClient()

            # Get target doorbell
            if doorbell_id:
                doorbell = client.get_device(doorbell_id)
            else:
                doorbells = client.get_devices_by_type("doorbell")
                if not doorbells:
                    return {"success": False, "error": "No doorbells found in system"}
                doorbell = doorbells[0]

            # Get current settings for comparison
            current_settings = client.get_motion_settings(doorbell.id)

            # Prepare new configuration
            new_config = {
                "sensitivity": sensitivity,
                "smart_alerts_enabled": smart_alerts,
                "schedule_enabled": schedule_enabled,
            }

            # Handle motion zones if provided
            if motion_zones:
                # Validate motion zone format
                valid_zones = []
                for zone in motion_zones:
                    if all(key in zone for key in ["name", "coordinates"]):
                        valid_zones.append(
                            {
                                "name": zone.get("name", "Custom Zone"),
                                "coordinates": zone["coordinates"],
                                "enabled": zone.get("enabled", True),
                            }
                        )

                new_config["motion_zones"] = valid_zones

            # Apply configuration
            config_result = client.update_motion_settings(
                device_id=doorbell.id, settings=new_config
            )

            # Generate optimization suggestions
            suggestions = []

            if sensitivity == "high":
                suggestions.append(
                    {
                        "type": "sensitivity",
                        "message": "High sensitivity may cause false alerts from cars/weather",
                        "recommendation": "Monitor for false positives and adjust if needed",
                    }
                )

            if not smart_alerts:
                suggestions.append(
                    {
                        "type": "smart_alerts",
                        "message": "Smart alerts help reduce false positives",
                        "recommendation": "Consider enabling for better person/package detection",
                    }
                )

            if not motion_zones:
                suggestions.append(
                    {
                        "type": "motion_zones",
                        "message": "Custom motion zones can improve detection accuracy",
                        "recommendation": "Set up zones to focus on walkways and entry points",
                    }
                )

            return {
                "success": True,
                "doorbell_id": doorbell.id,
                "doorbell_name": doorbell.name,
                "configuration_applied": new_config,
                "previous_settings": current_settings,
                "changes_made": {
                    "sensitivity_changed": current_settings.get("sensitivity") != sensitivity,
                    "smart_alerts_changed": current_settings.get("smart_alerts_enabled")
                    != smart_alerts,
                    "zones_updated": motion_zones is not None,
                    "schedule_changed": current_settings.get("schedule_enabled")
                    != schedule_enabled,
                },
                "optimization_suggestions": suggestions,
                "test_recommendations": [
                    "Walk through different areas to test motion detection",
                    "Check detection during different times of day",
                    "Monitor for false alerts over the next few days",
                    "Adjust sensitivity if too many/few alerts received",
                ],
                "configuration_timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.exception("Error configuring motion detection:")
            return {"success": False, "error": str(e)}
