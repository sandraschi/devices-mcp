"""Robotics API for controlling and monitoring home robots."""

import asyncio
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel, Field

# MCP server URLs (from registry: yahboom-mcp=10892, dreame-mcp=10894)
YAHBOOM_MCP_URL = os.environ.get("YAHBOOM_MCP_URL", "http://127.0.0.1:10892")
DREAME_MCP_URL = os.environ.get("DREAME_MCP_URL", "http://127.0.0.1:10894")

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/robots", tags=["robots"])


async def _call_mcp(url: str, method: str = "GET") -> dict[str, Any]:
    """Call an MCP server endpoint and return JSON, or error dict on failure."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            if method == "GET":
                r = await client.get(url)
            else:
                r = await client.post(url)
            r.raise_for_status()
            return r.json()
    except httpx.RequestError as e:
        return {"success": False, "error": f"MCP server unreachable: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


class RobotType(str, Enum):
    """Supported robot types."""

    DREAMBOT = "dreame"  # Dreame D20 Pro (via dreame-mcp)
    YAHBOOM = "yahboom"  # Yahboom ROS 2 Robot Car (via yahboom-mcp)


class RobotStatus(str, Enum):
    """Robot operational status."""

    ONLINE = "online"
    OFFLINE = "offline"
    CHARGING = "charging"
    PATROLLING = "patrolling"
    DOCKED = "docked"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class RobotCapabilities(BaseModel):
    """Robot capabilities and features."""

    has_camera: bool = False
    has_lidar: bool = False
    can_patrol: bool = False
    can_navigate: bool = False
    has_voice: bool = False
    supports_autonomous: bool = False
    battery_capacity: int | None = None  # mAh
    max_runtime: int | None = None  # minutes


class RobotPosition(BaseModel):
    """Robot position and orientation."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    heading: float = 0.0  # degrees
    floor: str = "ground"


class RobotTelemetry(BaseModel):
    """Real-time robot telemetry data."""

    battery_level: float = Field(..., ge=0, le=100)  # percentage
    battery_voltage: float | None = None
    temperature: float | None = None
    cpu_usage: float | None = None
    memory_usage: float | None = None
    wifi_signal: int | None = None  # dBm
    last_update: datetime


class Robot(BaseModel):
    """Complete robot information."""

    id: str
    name: str
    type: RobotType
    status: RobotStatus
    capabilities: RobotCapabilities
    position: RobotPosition
    telemetry: RobotTelemetry | None = None
    last_seen: datetime
    firmware_version: str | None = None
    ip_address: str | None = None
    connected_since: datetime | None = None
    is_virtual: bool = False  # True for virtual robots (vbots)
    platform: str | None = None  # "unity" or "vrchat" for vbots


class RobotCommand(str, Enum):
    """Available robot commands."""

    START_PATROL = "start_patrol"
    STOP_PATROL = "stop_patrol"
    START_CLEANING = "start_cleaning"
    STOP_CLEANING = "stop_cleaning"
    RETURN_HOME = "return_home"
    DOCK = "dock"
    PAUSE = "pause"
    STOP = "stop"
    FIND_ROBOT = "find_robot"
    FLASH_LIGHTS = "flash_lights"


class RobotCommandRequest(BaseModel):
    """Request to execute a robot command."""

    command: RobotCommand
    parameters: dict[str, Any] | None = None


# In-memory robot registry (would be database in production)
_robots: dict[str, Robot] = {}
_active_connections: dict[str, WebSocket] = {}


def get_default_capabilities(robot_type: RobotType) -> RobotCapabilities:
    """Get default capabilities for a robot type."""
    defaults = {
        # Physical robots
        RobotType.SCOUT: RobotCapabilities(
            has_camera=True,
            has_lidar=True,
            can_patrol=True,
            can_navigate=True,
            supports_autonomous=True,
            battery_capacity=5000,
            max_runtime=120,
        ),
        RobotType.SCOUT_E: RobotCapabilities(
            has_camera=True,
            has_lidar=True,
            can_patrol=True,
            can_navigate=True,
            supports_autonomous=True,
            battery_capacity=15000,
            max_runtime=240,
        ),
        RobotType.GO2: RobotCapabilities(
            has_camera=True,
            has_lidar=True,
            can_patrol=True,
            can_navigate=True,
            supports_autonomous=True,
            battery_capacity=15000,
            max_runtime=120,
        ),
        RobotType.G1: RobotCapabilities(
            has_camera=True,
            has_lidar=True,
            can_patrol=True,
            can_navigate=True,
            has_voice=True,
            supports_autonomous=True,
            battery_capacity=15000,
            max_runtime=180,
        ),
        RobotType.ROOMBOT: RobotCapabilities(
            can_patrol=True,
            can_navigate=True,
            supports_autonomous=True,
            battery_capacity=3000,
            max_runtime=90,
        ),
        RobotType.PETBOT: RobotCapabilities(has_camera=True, has_voice=True, supports_autonomous=False),
        # Virtual robots (vbots) - same capabilities but unlimited battery
        RobotType.VSCOUT: RobotCapabilities(
            has_camera=True,
            has_lidar=True,
            can_patrol=True,
            can_navigate=True,
            supports_autonomous=True,
            battery_capacity=None,  # Unlimited for virtual
            max_runtime=None,  # Unlimited for virtual
        ),
        RobotType.VSCOUT_E: RobotCapabilities(
            has_camera=True,
            has_lidar=True,
            can_patrol=True,
            can_navigate=True,
            supports_autonomous=True,
            battery_capacity=None,
            max_runtime=None,
        ),
        RobotType.VGO2: RobotCapabilities(
            has_camera=True,
            has_lidar=True,
            can_patrol=True,
            can_navigate=True,
            supports_autonomous=True,
            battery_capacity=None,
            max_runtime=None,
        ),
        RobotType.VG1: RobotCapabilities(
            has_camera=True,
            has_lidar=True,
            can_patrol=True,
            can_navigate=True,
            has_voice=True,
            supports_autonomous=True,
            battery_capacity=None,
            max_runtime=None,
        ),
        RobotType.VROBBIE: RobotCapabilities(
            has_camera=True,
            has_voice=True,
            can_patrol=True,
            can_navigate=True,
            supports_autonomous=True,
            battery_capacity=None,
            max_runtime=None,
        ),
        RobotType.DREAMBOT: RobotCapabilities(
            has_camera=True,
            has_lidar=True,
            can_patrol=True,
            can_navigate=True,
            supports_autonomous=True,
            battery_capacity=5200,
            max_runtime=180,
        ),
        RobotType.YAHBOOM: RobotCapabilities(
            has_camera=True,
            has_lidar=True,
            can_patrol=True,
            can_navigate=True,
            has_voice=False,
            supports_autonomous=True,
            battery_capacity=10000,
            max_runtime=120,
        ),
    }
    return defaults.get(robot_type, RobotCapabilities())


def initialize_sample_robots():
    """Initialize robots from configuration and add samples."""
    now = datetime.now()

    # Get config for robotics
    try:
        from devices_mcp.config import get_config

        config = get_config()
        robotics_config = config.get("robotics_mcp", {})
        devices_config = robotics_config.get("devices", {})

        # Load configured robots
        for device_id, device_data in devices_config.items():
            robot_type_str = device_data.get("type")
            try:
                # Map string to RobotType enum
                if robot_type_str == "dreame":
                    robot_type = RobotType.DREAMBOT
                elif robot_type_str == "yahboom":
                    robot_type = RobotType.YAHBOOM
                else:
                    robot_type = RobotType(robot_type_str)
            except ValueError:
                logger.warning(f"Unknown robot type: {robot_type_str}, skipping {device_id}")
                continue

            robot = Robot(
                id=device_id,
                name=device_data.get("name", device_id),
                type=robot_type,
                status=RobotStatus.ONLINE if robot_type == RobotType.YAHBOOM else RobotStatus.OFFLINE,
                capabilities=get_default_capabilities(robot_type),
                position=RobotPosition(x=0, y=0, z=0, heading=0, floor="ground"),
                last_seen=now,
                ip_address=device_data.get("host"),
            )
            _robots[robot.id] = robot
            logger.info(f"Loaded robot from config: {robot.id} ({robot.type.value})")

    except Exception as e:
        logger.error(f"Error loading robots from config: {e}")


# Initialize robot status from config only (no hardcoded samples)
initialize_sample_robots()


@router.get("/")
async def get_robots():
    """Get all registered robots."""
    try:
        robots_data = []
        for robot in _robots.values():
            robot_dict = robot.dict()
            # Add computed fields
            robot_dict["is_online"] = robot.status in [
                RobotStatus.ONLINE,
                RobotStatus.PATROLLING,
                RobotStatus.CHARGING,
            ]
            robot_dict["battery_percentage"] = robot.telemetry.battery_level if robot.telemetry else None
            robots_data.append(robot_dict)

        return {
            "success": True,
            "robots": robots_data,
            "total": len(robots_data),
            "online": sum(1 for r in robots_data if r["is_online"]),
        }
    except Exception as e:
        logger.exception("Failed to get robots")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{robot_id}")
async def get_robot(robot_id: str):
    """Get specific robot details."""
    try:
        if robot_id not in _robots:
            raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")

        robot = _robots[robot_id]
        robot_dict = robot.dict()
        robot_dict["is_online"] = robot.status in [
            RobotStatus.ONLINE,
            RobotStatus.PATROLLING,
            RobotStatus.CHARGING,
        ]
        robot_dict["battery_percentage"] = robot.telemetry.battery_level if robot.telemetry else None

        return {"success": True, "robot": robot_dict}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get robot {robot_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{robot_id}/command")
async def execute_robot_command(robot_id: str, command_request: RobotCommandRequest):
    """Execute a command on a robot."""
    try:
        if robot_id not in _robots:
            raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")

        robot = _robots[robot_id]

        # Check if robot is online for commands that require it
        if command_request.command in [
            RobotCommand.START_PATROL,
            RobotCommand.STOP_PATROL,
            RobotCommand.RETURN_HOME,
            RobotCommand.DOCK,
        ]:
            if robot.status == RobotStatus.OFFLINE:
                raise HTTPException(status_code=400, detail=f"Robot {robot_id} is offline")

        logger.info(f"Executing command {command_request.command} on robot {robot_id}")

        # Execute command based on robot type
        if robot.type == RobotType.DREAMBOT:
            if command_request.command == RobotCommand.START_CLEANING:
                result = await _call_mcp(f"{DREAME_MCP_URL}/api/v1/control/start_clean", method="POST")
                if result.get("success"):
                    robot.status = RobotStatus.CLEANING
            elif command_request.command == RobotCommand.STOP_CLEANING:
                result = await _call_mcp(f"{DREAME_MCP_URL}/api/v1/control/stop", method="POST")
                if result.get("success"):
                    robot.status = RobotStatus.ONLINE
            elif command_request.command == RobotCommand.RETURN_HOME:
                result = await _call_mcp(f"{DREAME_MCP_URL}/api/v1/control/go_home", method="POST")
                if result.get("success"):
                    robot.status = RobotStatus.DOCKED
            elif command_request.command == RobotCommand.PAUSE:
                result = await _call_mcp(f"{DREAME_MCP_URL}/api/v1/control/pause", method="POST")
                if result.get("success"):
                    robot.status = RobotStatus.ONLINE
            elif command_request.command == RobotCommand.FIND_ROBOT:
                result = await _call_mcp(f"{DREAME_MCP_URL}/api/v1/control/find_robot", method="POST")
                if result.get("success"):
                    robot.status = RobotStatus.ONLINE
            else:
                result = {"success": False, "error": f"Unknown dreame command: {command_request.command}"}

        elif robot.type == RobotType.YAHBOOM:
            cmd = command_request.command
            params = command_request.parameters or {}
            if cmd == RobotCommand.START_PATROL:
                linear = params.get("linear", 0.15)
                angular = params.get("angular", 0)
                result = await _call_mcp(
                    f"{YAHBOOM_MCP_URL}/api/v1/control/move?linear={linear}&angular={angular}",
                    method="POST",
                )
                if result.get("success"):
                    robot.status = RobotStatus.PATROLLING
            elif cmd == RobotCommand.STOP_PATROL:
                result = await _call_mcp(f"{YAHBOOM_MCP_URL}/api/v1/missions/stop", method="POST")
                if result.get("success"):
                    robot.status = RobotStatus.IDLE
            elif cmd == RobotCommand.RETURN_HOME:
                linear = params.get("linear", -0.15)
                result = await _call_mcp(
                    f"{YAHBOOM_MCP_URL}/api/v1/control/move?linear={linear}&angular=0",
                    method="POST",
                )
                if result.get("success"):
                    robot.status = RobotStatus.DOCKED
            elif cmd == RobotCommand.STOP:
                result = await _call_mcp(f"{YAHBOOM_MCP_URL}/api/v1/stop_all", method="POST")
                if result.get("success"):
                    robot.status = RobotStatus.IDLE
            elif cmd == RobotCommand.FLASH_LIGHTS:
                r = params.get("r", 255)
                g = params.get("g", 255)
                b = params.get("b", 255)
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.post(
                            f"{YAHBOOM_MCP_URL}/api/v1/control/lightstrip",
                            json={"operation": "set", "r": r, "g": g, "b": b},
                        )
                        result = resp.json() if resp.status_code == 200 else {"success": False}
                except httpx.RequestError as e:
                    result = {"success": False, "error": str(e)}
            elif cmd in ("start_cleaning", "stop_cleaning"):
                result = {"success": False, "error": "Yahboom robot car has no cleaning function"}
            else:
                result = {"success": False, "error": f"Unknown yahboom command: {cmd}"}

        else:
            # Simulate commands for other robot types
            if command_request.command == RobotCommand.START_PATROL:
                robot.status = RobotStatus.PATROLLING
            elif command_request.command == RobotCommand.STOP_PATROL:
                robot.status = RobotStatus.ONLINE
            elif command_request.command == RobotCommand.RETURN_HOME:
                robot.status = RobotStatus.DOCKED
            elif command_request.command == RobotCommand.DOCK:
                robot.status = RobotStatus.CHARGING
            elif command_request.command == RobotCommand.REBOOT:
                robot.status = RobotStatus.OFFLINE
                await asyncio.sleep(2)
                robot.status = RobotStatus.ONLINE

            result = {"success": True, "message": f"Command {command_request.command} simulated"}

        robot.last_seen = datetime.now()

        return {
            "success": result.get("success", True),
            "message": result.get("message", f"Command {command_request.command} executed on {robot_id}"),
            "robot_id": robot_id,
            "command": command_request.command,
            "timestamp": robot.last_seen.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to execute command on robot {robot_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{robot_id}/telemetry")
async def get_robot_telemetry(robot_id: str):
    """Get current telemetry for a robot."""
    try:
        if robot_id not in _robots:
            raise HTTPException(status_code=404, detail=f"Robot {robot_id} not found")

        robot = _robots[robot_id]

        # Get telemetry based on robot type
        if robot.type == RobotType.DREAMBOT:
            telemetry_data = await _call_mcp(f"{DREAME_MCP_URL}/api/v1/status")
            if telemetry_data.get("success"):
                telemetry = RobotTelemetry(
                    battery_level=telemetry_data.get("battery", 85.0),
                    battery_voltage=14.4,
                    temperature=30.0,
                    cpu_usage=20.0,
                    memory_usage=40.0,
                    wifi_signal=-55,
                    last_update=datetime.now(),
                )
                robot.status = (
                    RobotStatus.CHARGING
                    if telemetry_data.get("is_charging")
                    else RobotStatus.CLEANING
                    if telemetry_data.get("is_cleaning")
                    else RobotStatus.DOCKED
                    if telemetry_data.get("state") in ("idle", "charging_completed")
                    else RobotStatus.ONLINE
                )
            else:
                telemetry = RobotTelemetry(
                    battery_level=0.0,
                    battery_voltage=0.0,
                    temperature=0.0,
                    cpu_usage=0.0,
                    memory_usage=0.0,
                    wifi_signal=0,
                    last_update=datetime.now(),
                )

        elif robot.type == RobotType.YAHBOOM:
            telem_data = await _call_mcp(f"{YAHBOOM_MCP_URL}/api/v1/telemetry")
            if telem_data.get("status") in ("live",):
                telemetry = RobotTelemetry(
                    battery_level=telem_data.get("battery", 95.0),
                    battery_voltage=telem_data.get("voltage", 12.0),
                    temperature=38.0,
                    cpu_usage=15.0,
                    memory_usage=30.0,
                    wifi_signal=-40,
                    last_update=datetime.now(),
                )
                robot.position.x = telem_data.get("position", {}).get("x", robot.position.x)
                robot.position.y = telem_data.get("position", {}).get("y", robot.position.y)
                robot.position.heading = telem_data.get("imu", {}).get("heading", robot.position.heading)
            else:
                telemetry = RobotTelemetry(
                    battery_level=0.0,
                    battery_voltage=0.0,
                    temperature=0.0,
                    cpu_usage=0.0,
                    memory_usage=0.0,
                    wifi_signal=0,
                    last_update=datetime.now(),
                )

        else:
            # Generate mock telemetry for other robots
            telemetry = RobotTelemetry(
                battery_level=85.0 if robot.status != RobotStatus.CHARGING else 95.0,
                battery_voltage=12.6,
                temperature=35.0,
                cpu_usage=45.0,
                memory_usage=60.0,
                wifi_signal=-45,
                last_update=datetime.now(),
            )

        # Update robot's telemetry
        robot.telemetry = telemetry
        robot.last_seen = datetime.now()

        return {"success": True, "telemetry": telemetry.dict(), "robot_id": robot_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get telemetry for robot {robot_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/{robot_id}/ws")
async def robot_websocket(websocket: WebSocket, robot_id: str):
    """WebSocket endpoint for real-time robot updates."""
    await websocket.accept()

    if robot_id not in _robots:
        await websocket.send_json({"error": f"Robot {robot_id} not found"})
        await websocket.close()
        return

    _active_connections[robot_id] = websocket

    try:
        # Send initial robot data
        robot = _robots[robot_id]
        await websocket.send_json(
            {"type": "robot_update", "robot": robot.dict(), "timestamp": datetime.now().isoformat()}
        )

        # Keep connection alive and send periodic updates
        while True:
            await asyncio.sleep(5)  # Update every 5 seconds

            if robot_id not in _robots:
                break

            # Send telemetry update
            telemetry_data = await get_robot_telemetry(robot_id)
            await websocket.send_json(
                {
                    "type": "telemetry_update",
                    "data": telemetry_data,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    except Exception as e:
        logger.exception(f"WebSocket error for robot {robot_id}: {e}")
    finally:
        _active_connections.pop(robot_id, None)


@router.get("/types/capabilities")
async def get_robot_capabilities():
    """Get capabilities for all robot types."""
    try:
        capabilities = {}
        for robot_type in RobotType:
            capabilities[robot_type.value] = get_default_capabilities(robot_type).dict()

        return {"success": True, "capabilities": capabilities}
    except Exception as e:
        logger.exception("Failed to get robot capabilities")
        raise HTTPException(status_code=500, detail=str(e))
