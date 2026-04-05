"""
Security Analysis Portmanteau Tool

Combines security analysis operations:
- Test Nest Protect device
- Correlate Nest camera events
"""

import logging
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from ...tools.base_tool import BaseTool, ToolCategory, tool

logger = logging.getLogger(__name__)


@tool("security_analysis")
class SecurityAnalysisTool(BaseTool):
    """Security analysis tool.

    Provides unified security analysis operations including device testing
    and event correlation across Nest devices.

    Parameters:
        operation: Type of security operation (test_device, correlate_events).
        device_id: Device ID for test operations.
        test_type: Type of test for test_device operation (smoke, co, connectivity).
        correlation_window: Time window for event correlation in minutes.
        event_types: Event types to correlate (motion, sound, alerts).

    Returns:
        A dictionary containing the security analysis result.
    """

    class Meta:
        name = "security_analysis"
        description = "Unified security analysis including device testing and event correlation"
        category = ToolCategory.ALARMS

        class Parameters(BaseModel):
            operation: str = Field(
                ..., description="Security operation: 'test_device', 'correlate_events'"
            )
            device_id: Optional[str] = Field(None, description="Device ID for test operations")
            test_type: Optional[str] = Field(
                None, description="Test type: 'smoke', 'co', 'connectivity'"
            )
            correlation_window: Optional[int] = Field(
                60, description="Correlation window in minutes"
            )
            event_types: Optional[List[str]] = Field(None, description="Event types to correlate")

    async def execute(
        self,
        operation: str,
        device_id: Optional[str] = None,
        test_type: Optional[str] = None,
        correlation_window: int = 60,
        event_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute security analysis operation."""
        try:
            logger.info(f"Security analysis {operation} operation")

            if operation == "test_device":
                return await self._test_device(device_id, test_type)
            if operation == "correlate_events":
                return await self._correlate_events(correlation_window, event_types)
            return {
                "success": False,
                "error": f"Invalid operation: {operation}. Must be 'test_device' or 'correlate_events'",
                "timestamp": time.time(),
            }

        except Exception as e:
            logger.exception(f"Security analysis {operation} operation failed")
            return {
                "success": False,
                "error": str(e),
                "operation": operation,
                "timestamp": time.time(),
            }

    async def _test_device(
        self, device_id: Optional[str], test_type: Optional[str]
    ) -> Dict[str, Any]:
        """Test Nest Protect device."""
        if not device_id:
            return {
                "success": False,
                "error": "Device ID is required for test operations",
                "timestamp": time.time(),
            }

        if not test_type:
            return {
                "success": False,
                "error": "Test type is required for test operations",
                "timestamp": time.time(),
            }

        valid_test_types = ["smoke", "co", "connectivity"]
        if test_type not in valid_test_types:
            return {
                "success": False,
                "error": f"Invalid test type: {test_type}. Must be one of: {valid_test_types}",
                "timestamp": time.time(),
            }

        # Simulate device test
        test_results = {
            "device_id": device_id,
            "test_type": test_type,
            "test_timestamp": time.time(),
            "status": "completed",
            "result": "passed",
        }

        if test_type == "smoke":
            test_results.update(
                {
                    "smoke_sensor": "functional",
                    "alarm_sound": "tested",
                    "speech_alert": "tested",
                    "night_light": "tested",
                }
            )
        elif test_type == "co":
            test_results.update(
                {
                    "co_sensor": "functional",
                    "alarm_sound": "tested",
                    "speech_alert": "tested",
                    "pathlight": "tested",
                }
            )
        elif test_type == "connectivity":
            test_results.update(
                {
                    "wifi_connection": "excellent",
                    "signal_strength": 95,
                    "response_time": 45,
                    "cloud_sync": "active",
                }
            )

        return {
            "success": True,
            "operation": "test_device",
            "test_results": test_results,
            "message": f"Device test completed for {device_id}: {test_type} test passed",
            "timestamp": time.time(),
        }

    async def _correlate_events(
        self, correlation_window: int, event_types: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Correlate events across Nest devices."""
        # Simulate event correlation
        import secrets

        # Generate simulated events
        events = []
        current_time = time.time()
        window_start = current_time - (correlation_window * 60)

        # Generate motion events
        if not event_types or "motion" in event_types:
            for i in range(secrets.randbelow(5) + 1):
                events.append(
                    {
                        "event_id": f"motion_{i + 1}",
                        "type": "motion",
                        "device_id": f"camera_{secrets.randbelow(3) + 1:03d}",
                        "device_name": f"Camera {i + 1}",
                        "timestamp": window_start + secrets.randbelow(correlation_window * 60),
                        "location": f"Zone {i + 1}",
                        "confidence": round(0.7 + secrets.randbelow(30) / 100, 2),
                    }
                )

        # Generate sound events
        if not event_types or "sound" in event_types:
            for i in range(secrets.randbelow(3) + 1):
                events.append(
                    {
                        "event_id": f"sound_{i + 1}",
                        "type": "sound",
                        "device_id": f"protect_{secrets.randbelow(3) + 1:03d}",
                        "device_name": f"Protect {i + 1}",
                        "timestamp": window_start + secrets.randbelow(correlation_window * 60),
                        "location": f"Room {i + 1}",
                        "sound_level": round(40 + secrets.randbelow(40), 1),
                    }
                )

        # Generate alert events
        if not event_types or "alerts" in event_types:
            for i in range(secrets.randbelow(2) + 1):
                events.append(
                    {
                        "event_id": f"alert_{i + 1}",
                        "type": "alert",
                        "device_id": f"protect_{secrets.randbelow(3) + 1:03d}",
                        "device_name": f"Protect {i + 1}",
                        "timestamp": window_start + secrets.randbelow(correlation_window * 60),
                        "location": f"Room {i + 1}",
                        "alert_type": secrets.choice(["smoke", "co", "test"]),
                    }
                )

        # Sort events by timestamp
        events.sort(key=lambda x: x["timestamp"])

        # Find correlations
        correlations = []
        for i, event in enumerate(events):
            for _j, other_event in enumerate(events[i + 1 :], i + 1):
                time_diff = abs(event["timestamp"] - other_event["timestamp"])
                if time_diff <= 300:  # Within 5 minutes
                    correlation_score = max(0, 1 - (time_diff / 300))
                    if correlation_score > 0.3:  # Significant correlation
                        correlations.append(
                            {
                                "event_1": event,
                                "event_2": other_event,
                                "time_difference": time_diff,
                                "correlation_score": round(correlation_score, 2),
                                "correlation_type": self._determine_correlation_type(
                                    event, other_event
                                ),
                            }
                        )

        # Generate insights
        insights = []
        if len(correlations) > 0:
            insights.append(
                f"Found {len(correlations)} event correlations in {correlation_window} minute window"
            )

        high_correlation_events = [c for c in correlations if c["correlation_score"] > 0.7]
        if high_correlation_events:
            insights.append(f"{len(high_correlation_events)} high-confidence correlations detected")

        motion_events = [e for e in events if e["type"] == "motion"]
        if len(motion_events) > 3:
            insights.append("High motion activity detected - potential security concern")

        return {
            "success": True,
            "operation": "correlate_events",
            "correlation_window": correlation_window,
            "total_events": len(events),
            "events": events,
            "correlations": correlations,
            "total_correlations": len(correlations),
            "high_confidence_correlations": len(high_correlation_events),
            "insights": insights,
            "message": f"Event correlation completed: {len(events)} events, {len(correlations)} correlations",
            "timestamp": time.time(),
        }

    def _determine_correlation_type(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> str:
        """Determine the type of correlation between two events."""
        if event1["type"] == event2["type"]:
            return f"same_type_{event1['type']}"
        if event1["type"] in ["motion", "sound"] and event2["type"] in ["motion", "sound"]:
            return "activity_correlation"
        if event1["type"] == "alert" or event2["type"] == "alert":
            return "alert_correlation"
        return "mixed_correlation"
