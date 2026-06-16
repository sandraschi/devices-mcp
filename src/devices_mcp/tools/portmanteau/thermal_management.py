"""
Thermal Cameras Management Portmanteau Tool
Consolidates thermal camera operations into a single tool for MLX90640,
AMG8833, and other thermal sensors used for hot spot detection and
temperature monitoring.
"""

import logging
from typing import Any

from fastmcp import FastMCP

logger = logging.getLogger(__name__)
THERMAL_ACTIONS = {
    "list_sensors": "List all thermal camera sensors",
    "get_sensor_status": "Get status of a specific thermal sensor",
    "get_temperature_data": "Get thermal temperature data and hotspots",
    "detect_hotspots": "Detect temperature hotspots above threshold",
    "set_thresholds": "Set temperature alert thresholds",
    "get_thermal_image": "Capture thermal image data",
    "calibrate_sensor": "Calibrate thermal sensor",
    "get_temperature_history": "Get historical temperature data",
}


def register_thermal_management_tool(mcp: FastMCP) -> None:
    """Register the thermal cameras management portmanteau tool."""

    @mcp.tool()
    async def thermal_management(
        action: str,
        sensor_id: str | None = None,
        threshold_celsius: float | None = None,
        hotspot_threshold: float | None = None,
        duration_minutes: int = 60,
        resolution: str = "high",
    ) -> dict[str, Any]:
        """
        Comprehensive thermal cameras management portmanteau tool.
        PORTMANTEAU PATTERN RATIONALE:
        Thermal cameras (MLX90640, AMG8833) share common operational patterns
        for temperature monitoring, hotspot detection, and thermal imaging.
        This tool consolidates them to reduce complexity.
        Args:
            action (str, required): The operation to perform. Must be one of:
                - "list_sensors": List all thermal sensors
                - "get_sensor_status": Get sensor status (requires: sensor_id)
                - "get_temperature_data": Get thermal data (requires: sensor_id)
                - "detect_hotspots": Detect hotspots (requires: sensor_id, optional: hotspot_threshold)
                - "set_thresholds": Set thresholds (requires: sensor_id, threshold_celsius)
                - "get_thermal_image": Get thermal image (requires: sensor_id)
                - "calibrate_sensor": Calibrate sensor (requires: sensor_id)
                - "get_temperature_history": Get history (requires: sensor_id, optional: duration_minutes)
            sensor_id (str | None): Thermal sensor identifier
            threshold_celsius (float | None): Temperature threshold in Celsius
            hotspot_threshold (float | None): Hotspot detection threshold
            duration_minutes (int): History duration in minutes (default: 60)
            resolution (str): Data resolution ("low", "medium", "high")
        Returns:
            dict[str, Any]: Operation result with thermal data and status
        """
        try:
            if action not in THERMAL_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(THERMAL_ACTIONS.keys())}",
                }
            logger.info(f"Executing thermal management action: {action}")
            # Mock implementations for thermal cameras
            # In a real implementation, these would connect to actual thermal sensors
            if action == "list_sensors":
                sensors = [
                    {
                        "id": "mlx90640_kitchen",
                        "name": "Kitchen Thermal Camera",
                        "model": "MLX90640",
                        "type": "thermal_array",
                        "ip": "192.168.0.210",
                        "status": "online",
                        "location": "Kitchen",
                        "resolution": "32x24",
                        "temperature_range": "-40°C to 300°C",
                        "frame_rate_hz": 8,
                        "current_max_temp": 45.2,
                        "current_min_temp": 22.1,
                        "alert_threshold": 150.0,
                    },
                    {
                        "id": "mlx90640_server",
                        "name": "Server Rack Thermal",
                        "model": "MLX90640",
                        "type": "thermal_array",
                        "ip": "192.168.0.211",
                        "status": "online",
                        "location": "Server Room",
                        "resolution": "32x24",
                        "temperature_range": "-40°C to 300°C",
                        "frame_rate_hz": 8,
                        "current_max_temp": 38.7,
                        "current_min_temp": 21.8,
                        "alert_threshold": 50.0,
                    },
                    {
                        "id": "amg8833_office",
                        "name": "Office Motion Sensor",
                        "model": "AMG8833",
                        "type": "thermal_grid",
                        "ip": "192.168.0.212",
                        "status": "online",
                        "location": "Office",
                        "resolution": "8x8",
                        "temperature_range": "0°C to 80°C",
                        "frame_rate_hz": 10,
                        "current_max_temp": 24.5,
                        "current_min_temp": 20.2,
                        "alert_threshold": 35.0,
                    },
                ]
                return {
                    "success": True,
                    "action": action,
                    "sensors": sensors,
                    "count": len(sensors),
                }
            if action == "get_sensor_status":
                if not sensor_id:
                    return {
                        "success": False,
                        "message": "sensor_id is required for get_sensor_status",
                        "error": "sensor_id is required for get_sensor_status",
                    }
                # Mock sensor status
                sensor_status = {
                    "id": sensor_id,
                    "status": "online",
                    "last_reading": "2025-12-27T04:00:00Z",
                    "uptime_hours": 168,
                    "firmware_version": "2.1.0",
                    "calibration_status": "valid",
                    "connection_quality": "excellent",
                    "temperature_accuracy": "±1.5°C",
                    "power_consumption_mw": 45,
                    "operating_temperature": 28.5,
                }
                return {
                    "success": True,
                    "action": action,
                    "sensor": sensor_status,
                }
            if action == "get_temperature_data":
                if not sensor_id:
                    return {
                        "success": False,
                        "message": "sensor_id is required for get_temperature_data",
                        "error": "sensor_id is required for get_temperature_data",
                    }
                # Mock thermal data
                thermal_data = {
                    "sensor_id": sensor_id,
                    "timestamp": "2025-12-27T04:00:00Z",
                    "resolution": resolution,
                    "temperature_stats": {
                        "max_celsius": 45.2,
                        "min_celsius": 22.1,
                        "avg_celsius": 28.7,
                        "median_celsius": 26.8,
                        "std_dev_celsius": 3.2,
                    },
                    "hotspots": [
                        {
                            "x": 15,
                            "y": 8,
                            "temperature_celsius": 45.2,
                            "confidence": 0.95,
                            "description": "Oven heating element",
                        },
                        {
                            "x": 22,
                            "y": 12,
                            "temperature_celsius": 38.7,
                            "confidence": 0.87,
                            "description": "Server CPU",
                        },
                    ],
                    "thermal_image_available": True,
                    "frame_rate_hz": 8,
                }
                return {
                    "success": True,
                    "action": action,
                    "thermal_data": thermal_data,
                }
            if action == "detect_hotspots":
                if not sensor_id:
                    return {
                        "success": False,
                        "message": "sensor_id is required for detect_hotspots",
                        "error": "sensor_id is required for detect_hotspots",
                    }
                threshold = hotspot_threshold or 40.0  # Default 40°C
                # Mock hotspot detection
                hotspots_detected = [
                    {
                        "id": "hotspot_001",
                        "sensor_id": sensor_id,
                        "coordinates": {"x": 15, "y": 8},
                        "temperature_celsius": 45.2,
                        "threshold_celsius": threshold,
                        "severity": "high",
                        "confidence": 0.95,
                        "description": "Potential fire hazard - oven overheating",
                        "timestamp": "2025-12-27T04:00:00Z",
                        "actions_taken": ["alert_generated", "notification_sent"],
                    },
                    {
                        "id": "hotspot_002",
                        "sensor_id": sensor_id,
                        "coordinates": {"x": 22, "y": 12},
                        "temperature_celsius": 38.7,
                        "threshold_celsius": threshold,
                        "severity": "medium",
                        "confidence": 0.87,
                        "description": "Server temperature elevated",
                        "timestamp": "2025-12-27T04:00:00Z",
                        "actions_taken": ["logged"],
                    },
                ]
                detection_result = {
                    "sensor_id": sensor_id,
                    "threshold_celsius": threshold,
                    "hotspots_found": len(hotspots_detected),
                    "scan_duration_ms": 250,
                    "hotspots": hotspots_detected,
                    "timestamp": "2025-12-27T04:00:00Z",
                }
                return {
                    "success": True,
                    "action": action,
                    "detection": detection_result,
                }
            if action == "set_thresholds":
                if not sensor_id or threshold_celsius is None:
                    return {
                        "success": False,
                        "message": "sensor_id and threshold_celsius are required for set_thresholds",
                        "error": "sensor_id and threshold_celsius are required for set_thresholds",
                    }
                # Mock threshold setting
                threshold_config = {
                    "sensor_id": sensor_id,
                    "alert_threshold_celsius": threshold_celsius,
                    "warning_threshold_celsius": threshold_celsius * 0.8,
                    "critical_threshold_celsius": threshold_celsius,
                    "hysteresis_celsius": 2.0,
                    "alert_cooldown_minutes": 5,
                    "notifications_enabled": True,
                    "timestamp": "2025-12-27T04:00:00Z",
                }
                return {
                    "success": True,
                    "action": action,
                    "thresholds": threshold_config,
                }
            if action == "get_thermal_image":
                if not sensor_id:
                    return {
                        "success": False,
                        "message": "sensor_id is required for get_thermal_image",
                        "error": "sensor_id is required for get_thermal_image",
                    }
                # Mock thermal image capture
                thermal_image = {
                    "sensor_id": sensor_id,
                    "timestamp": "2025-12-27T04:00:00Z",
                    "resolution": resolution,
                    "image_format": "thermal_array",
                    "dimensions": {"width": 32, "height": 24} if resolution == "high" else {"width": 16, "height": 12},
                    "temperature_range": {"min_celsius": 22.1, "max_celsius": 45.2},
                    "data_points": 768,  # 32x24
                    "file_size_kb": 15,
                    "processing_time_ms": 45,
                    "quality_score": 0.92,
                }
                return {
                    "success": True,
                    "action": action,
                    "thermal_image": thermal_image,
                }
            if action == "calibrate_sensor":
                if not sensor_id:
                    return {
                        "success": False,
                        "message": "sensor_id is required for calibrate_sensor",
                        "error": "sensor_id is required for calibrate_sensor",
                    }
                # Mock calibration
                calibration_result = {
                    "sensor_id": sensor_id,
                    "calibration_type": "thermal_offset",
                    "duration_seconds": 60,
                    "status": "completed",
                    "accuracy_improvement_percent": 15.2,
                    "drift_compensation_applied": True,
                    "next_calibration_due": "2026-03-27T04:00:00Z",
                    "timestamp": "2025-12-27T04:00:00Z",
                }
                return {
                    "success": True,
                    "action": action,
                    "calibration": calibration_result,
                }
            if action == "get_temperature_history":
                if not sensor_id:
                    return {
                        "success": False,
                        "message": "sensor_id is required for get_temperature_history",
                        "error": "sensor_id is required for get_temperature_history",
                    }
                # Mock historical data
                history_data = {
                    "sensor_id": sensor_id,
                    "duration_minutes": duration_minutes,
                    "data_points": duration_minutes * 8,  # 8 readings per minute
                    "temperature_range": {
                        "max_celsius": 48.5,
                        "min_celsius": 20.8,
                        "avg_celsius": 28.2,
                    },
                    "hotspot_events": 3,
                    "alert_events": 1,
                    "data_compression": "adaptive",
                    "timestamp": "2025-12-27T04:00:00Z",
                    "samples": [
                        {"timestamp": "2025-12-27T03:00:00Z", "max_temp": 42.1, "avg_temp": 26.8},
                        {"timestamp": "2025-12-27T03:30:00Z", "max_temp": 45.2, "avg_temp": 28.1},
                        {"timestamp": "2025-12-27T04:00:00Z", "max_temp": 38.7, "avg_temp": 27.5},
                    ],
                }
                return {
                    "success": True,
                    "action": action,
                    "history": history_data,
                }
            return {
                "success": False,
                "message": f"Action '{action}' not implemented",
                "error": f"Action '{action}' not implemented",
            }
        except Exception as e:
            logger.exception("Error in thermal management action '{action}':")
            return {
                "success": False,
                "message": f"Failed to execute action '{action}': {e!s}",
                "error": f"Failed to execute action '{action}': {e!s}",
            }
