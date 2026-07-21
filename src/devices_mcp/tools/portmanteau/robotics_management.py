"""
Robotics Management Portmanteau Tool

Consolidates all robotics-related operations into a single tool with action-based interface.
Currently supports Moorebot Scout robot with ROS 1.4 compatibility.
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

_READ_ONLY: dict[str, bool] = {"readonly": True}
_MUTATING: dict[str, bool] = {}
_DESTRUCTIVE: dict[str, bool] = {"destructive": True}

from ...tools.robotics.moorebot_tools import (
    get_moorebot_client,
    initialize_moorebot_client,
    moorebot_get_camera_stream,
    moorebot_get_sensors,
    moorebot_get_status,
    moorebot_move,
    moorebot_patrol,
    moorebot_return_to_dock,
    moorebot_stop_patrol,
)
from ...utils.response_builders import (
    build_error_response,
    build_hardware_error_response,
)

logger = logging.getLogger(__name__)

ROBOTICS_ACTIONS = {
    "get_status": "Get robot status (battery, position, sensors)",
    "move": "Move robot with specified velocities",
    "patrol": "Start autonomous patrol route",
    "stop_patrol": "Stop current patrol",
    "return_to_dock": "Return robot to charging dock",
    "get_sensors": "Get current sensor readings (ToF, IMU, light)",
    "get_camera_stream": "Get camera stream URLs (RTSP)",
    "initialize": "Initialize robot client connection",
}


def register_robotics_management_tool(mcp: FastMCP) -> None:
    """Register the robotics management portmanteau tool."""

    @mcp.tool(annotations=_MUTATING)
    async def robotics_management(
        action: Literal[
            "get_status",
            "move",
            "patrol",
            "stop_patrol",
            "return_to_dock",
            "get_sensors",
            "get_camera_stream",
            "initialize",
        ],
        route: str | None = None,
        linear_velocity: float = 0.0,
        angular_velocity: float = 0.0,
        duration: float = 0.0,
        ip_address: str | None = None,
        mock_mode: bool = True,
    ) -> dict[str, Any]:
        """
        Comprehensive robotics management portmanteau tool for Moorebot Scout.

        PORTMANTEAU PATTERN RATIONALE:
        Consolidates robotics operations into a single interface to reduce tool explosion
        while maintaining full functionality. Supports Moorebot Scout with ROS 1.4 compatibility,
        including autonomous patrol, sensor integration, and camera streaming.

        Args:
            action (Literal, required): The operation to perform. Must be one of:
                - "get_status": Get robot status (battery, position, sensors)
                - "move": Move robot with specified velocities (requires: linear_velocity, angular_velocity, optional: duration)
                - "patrol": Start autonomous patrol route (optional: route name, default: "default")
                - "stop_patrol": Stop current patrol
                - "return_to_dock": Return robot to charging dock
                - "get_sensors": Get current sensor readings (ToF, IMU, light)
                - "get_camera_stream": Get camera stream URLs (RTSP)
                - "initialize": Initialize robot client connection (requires: ip_address, optional: mock_mode)

            route (str | None): Patrol route name for patrol action
                - "default": Living room -> Bedroom -> Kitchen -> Home
                - "perimeter": Full apartment perimeter
                - "rooms": Quick check of all rooms

            linear_velocity (float): Linear velocity in m/s for move action (range: -0.3 to 0.3)
                - Positive: forward, Negative: backward

            angular_velocity (float): Angular velocity in rad/s for move action (range: -2.0 to 2.0)
                - Positive: counter-clockwise, Negative: clockwise

            duration (float): Movement duration in seconds for move action (0 = continuous)

            ip_address (str | None): Robot IP address for initialize action

            mock_mode (bool): Use mock mode for testing (default: True)

        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data (status, sensors, streams, etc.)
                - error (str | None): Error message if success is False

        Examples:
            # Initialize robot client
            result = await robotics_management(action="initialize", ip_address="192.168.1.100", mock_mode=False)

            # Get robot status
            result = await robotics_management(action="get_status")

            # Move forward for 3 seconds
            result = await robotics_management(action="move", linear_velocity=0.2, duration=3.0)

            # Start default patrol
            result = await robotics_management(action="patrol", route="default")

            # Stop patrol
            result = await robotics_management(action="stop_patrol")

            # Return to dock
            result = await robotics_management(action="return_to_dock")

            # Get sensor readings
            result = await robotics_management(action="get_sensors")

            # Get camera streams
            result = await robotics_management(action="get_camera_stream")
        """
        try:
            if action not in ROBOTICS_ACTIONS:
                return {
                    "success": False,
                    "message": f"Invalid action '{action}'. Available: {list(ROBOTICS_ACTIONS.keys())}",
                }

            logger.info(f"Executing robotics management action: {action}")

            if action == "initialize":
                if not ip_address:
                    return {
                        "success": False,
                        "message": "ip_address is required for initialize action",
                        "error": "ip_address is required for initialize action",
                    }
                initialize_moorebot_client(ip_address, mock_mode)
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "ip_address": ip_address,
                        "mock_mode": mock_mode,
                        "message": f"Moorebot client initialized at {ip_address} (mock: {mock_mode})",
                    },
                }

            # All other actions require a client
            try:
                get_moorebot_client()  # Check if initialized
            except RuntimeError:
                return {
                    "success": False,
                    "message": "Robot client not initialized. Use initialize action first.",
                    "error": "Robot client not initialized. Use initialize action first.",
                }

            if action == "get_status":
                result = await moorebot_get_status()
                return {"success": True, "action": action, "data": result}

            if action == "move":
                result = await moorebot_move(linear_velocity, angular_velocity, duration)
                return {"success": True, "action": action, "data": result}

            if action == "patrol":
                patrol_route = route or "default"
                result = await moorebot_patrol(patrol_route)
                return {"success": True, "action": action, "data": result}

            if action == "stop_patrol":
                result = await moorebot_stop_patrol()
                return {"success": True, "action": action, "data": result}

            if action == "return_to_dock":
                result = await moorebot_return_to_dock()
                return {"success": True, "action": action, "data": result}

            if action == "get_sensors":
                result = await moorebot_get_sensors()
                return {"success": True, "action": action, "data": result}

            if action == "get_camera_stream":
                result = await moorebot_get_camera_stream()
                return {"success": True, "action": action, "data": result}

            return build_error_response(
                error=f"Robotics action '{action}' not implemented",
                error_code="ACTION_NOT_IMPLEMENTED",
                message=f"The requested robotics action '{action}' is not yet available",
                suggestions=[
                    "Use available actions: get_status, move, patrol, stop_patrol, etc.",
                    "Check for MCP server updates that may add this functionality",
                    "Verify robot supports the requested operation",
                ],
            )

        except Exception as e:
            logger.exception("Error in robotics management action '{action}':")

            # Intelligent error analysis for robotics issues
            error_str = str(e).lower()
            recovery_options = []

            if "ros" in error_str or "master" in error_str:
                recovery_options = [
                    "Check ROS master is running: 'roscore'",
                    "Verify ROS_MASTER_URI environment variable",
                    "Ensure robot and MCP server are on same ROS network",
                    "Check ROS node registration and topics",
                ]
            elif "connection" in error_str or "network" in error_str or "unreachable" in error_str:
                recovery_options = [
                    "Check robot is powered on and connected to network",
                    "Verify robot IP address and network configuration",
                    "Check firewall allows communication with robot",
                    "Try power cycling the robot (unplug for 30 seconds)",
                ]
            elif "moorebot" in error_str or "scout" in error_str:
                recovery_options = [
                    "Check Moorebot Scout is powered on and in range",
                    "Verify Scout is connected to same WiFi network as MCP server",
                    "Ensure Scout firmware is up to date via Moorebot app",
                    "Check battery level - charge if below 20%",
                    "Verify Scout is not in use by another application",
                ]
            elif "battery" in error_str or "power" in error_str:
                recovery_options = [
                    "Check robot battery level - charge if low",
                    "Ensure robot is not in power-saving mode",
                    "Verify charging dock connection if returning to dock",
                    "Check battery contacts and charging system",
                ]
            elif "camera" in error_str or "stream" in error_str:
                recovery_options = [
                    "Check robot camera is not obstructed or covered",
                    "Verify RTSP stream settings in robot configuration",
                    "Ensure camera permissions and network access",
                    "Try restarting camera service on robot",
                ]
            else:
                recovery_options = [
                    "Check robot status and connectivity",
                    "Verify robot is powered on and not in error state",
                    "Try restarting the MCP server",
                    "Check robot firmware and software updates",
                ]

            return build_hardware_error_response(
                error=f"Robotics operation failed during {action}",
                device_type="Robot",
                device_id="scout_robot",
                recovery_options=recovery_options,
                suggestions=[
                    f"Try running robotics action '{action}' again after applying recovery steps",
                    "Check robot status with 'get_status' action first",
                    "Verify robot network connectivity and power status",
                ],
            )
