"""Robotics API for controlling and monitoring home robots."""

import asyncio
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, WebSocket
from pydantic import BaseModel, Field

from devices_mcp.integrations.dreame_client import DreameClient
from devices_mcp.integrations.go2_client import UnitreeGo2Client
from devices_mcp.integrations.moorebot_client import MoorebotScoutClient
from devices_mcp.integrations.vbot_client import VbotClient
from devices_mcp.integrations.yahboom_client import YahboomClient

# Global vbot client instance
_vbot_client: Optional[VbotClient] = None

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/robots", tags=["robots"])


class RobotType(str, Enum):
    """Supported robot types."""

    SCOUT = "scout"  # Moorebot Scout (physical)
    SCOUT_E = "scout_e"  # Moorebot Scout E (physical)
    GO2 = "go2"  # Unitree Go2 (physical)
    G1 = "g1"  # Unitree G1 (physical)
    ROOMBOT = "roombot"  # Roomba/iRobot (physical)
    PETBOT = "petbot"  # Petbot Loona (physical)
    VSCOUT = "vscout"  # Virtual Moorebot Scout
    VSCOUT_E = "vscout_e"  # Virtual Moorebot Scout E
    VGO2 = "vgo2"  # Virtual Unitree Go2
    VG1 = "vg1"  # Virtual Unitree G1
    VROBBIE = "vrobbie"  # Virtual Robbie
    DREAMBOT = "dreame"  # Dreame D20 Pro (Home Assistant)
    YAHBOOM = "yahboom"  # Yahboom ROS 2 Robot Car


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
    battery_capacity: Optional[int] = None  # mAh
    max_runtime: Optional[int] = None  # minutes


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
    battery_voltage: Optional[float] = None
    temperature: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    wifi_signal: Optional[int] = None  # dBm
    last_update: datetime


class Robot(BaseModel):
    """Complete robot information."""

    id: str
    name: str
    type: RobotType
    status: RobotStatus
    capabilities: RobotCapabilities
    position: RobotPosition
    telemetry: Optional[RobotTelemetry] = None
    last_seen: datetime
    firmware_version: Optional[str] = None
    ip_address: Optional[str] = None
    connected_since: Optional[datetime] = None
    is_virtual: bool = False  # True for virtual robots (vbots)
    platform: Optional[str] = None  # "unity" or "vrchat" for vbots


class RobotCommand(str, Enum):
    """Available robot commands."""

    START_PATROL = "start_patrol"
    STOP_PATROL = "stop_patrol"
    START_CLEANING = "start_cleaning"
    STOP_CLEANING = "stop_cleaning"
    RETURN_HOME = "return_home"
    DOCK = "dock"
    UNDOCK = "undock"
    PAUSE = "pause"
    RESUME = "resume"
    REBOOT = "reboot"
    UPDATE_FIRMWARE = "update_firmware"
    DELETE_VBOT = "delete_vbot"
    STOP = "stop"


class RobotCommandRequest(BaseModel):
    """Request to execute a robot command."""

    command: RobotCommand
    parameters: Optional[Dict[str, Any]] = None


# In-memory robot registry (would be database in production)
_robots: Dict[str, Robot] = {}
_active_connections: Dict[str, WebSocket] = {}


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
        RobotType.PETBOT: RobotCapabilities(
            has_camera=True, has_voice=True, supports_autonomous=False
        ),
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
                status=RobotStatus.ONLINE
                if robot_type == RobotType.YAHBOOM
                else RobotStatus.OFFLINE,
                capabilities=get_default_capabilities(robot_type),
                position=RobotPosition(x=0, y=0, z=0, heading=0, floor="ground"),
                last_seen=now,
                ip_address=device_data.get("host"),
            )
            _robots[robot.id] = robot
            logger.info(f"Loaded robot from config: {robot.id} ({robot.type.value})")

    except Exception as e:
        logger.error(f"Error loading robots from config: {e}")

    # Add default samples if not present
    if "scout_01" not in _robots:
        scout = Robot(
            id="scout_01",
            name="Living Room Scout",
            type=RobotType.SCOUT,
            status=RobotStatus.OFFLINE,
            capabilities=get_default_capabilities(RobotType.SCOUT),
            position=RobotPosition(x=0, y=0, z=0, heading=0, floor="ground"),
            last_seen=now,
            firmware_version="1.4.2",
            ip_address="192.168.1.150",
        )
        _robots[scout.id] = scout

    if "go2_01" not in _robots:
        go2 = Robot(
            id="go2_01",
            name="Patrol Go2",
            type=RobotType.GO2,
            status=RobotStatus.OFFLINE,
            capabilities=get_default_capabilities(RobotType.GO2),
            position=RobotPosition(x=0, y=0, z=0, heading=0, floor="ground"),
            last_seen=now,
            firmware_version=None,
            ip_address="192.168.1.120",
        )
        _robots[go2.id] = go2


# Initialize sample data
initialize_sample_robots()


# Initialize vbot client and load virtual robots
async def initialize_vbot_integration():
    """Initialize virtual robot integration with robotics-mcp server."""
    global _vbot_client

    try:
        # Get config for robotics MCP integration
        from devices_mcp.config import get_config

        config = get_config()
        robotics_config = config.get("robotics_mcp", {})

        if not robotics_config.get("enabled", False):
            logger.info("Robotics MCP integration disabled")
            return

        server_url = robotics_config.get("server_url", "http://localhost:8080")
        timeout = robotics_config.get("timeout", 30)
        auto_discover = robotics_config.get("auto_discover_robots", True)

        if not auto_discover:
            logger.info("Auto-discovery of robots disabled")
            return

        # Initialize vbot client
        _vbot_client = VbotClient(server_url, timeout)

        # Connect to robotics-mcp server
        connection_result = await _vbot_client.connect()
        if not connection_result.get("success"):
            logger.error(f"Failed to connect to robotics-mcp server: {connection_result}")
            return

        logger.info("Connected to robotics-mcp server for virtual robot integration")

        # Load virtual robots from robotics-mcp server
        if auto_discover:
            await load_virtual_robots_from_server()

    except Exception as e:
        logger.exception(f"Error initializing vbot integration: {e}")


async def load_virtual_robots_from_server():
    """Load virtual robots from the robotics-mcp server."""
    global _vbot_client

    if not _vbot_client:
        return

    try:
        # Get list of virtual robots from robotics-mcp
        vbot_list = await _vbot_client.list_vbots()
        if not vbot_list.get("success"):
            logger.error(f"Failed to list vbots: {vbot_list}")
            return

        virtual_robots = vbot_list.get("robots", [])
        logger.info(f"Found {len(virtual_robots)} virtual robots on robotics-mcp server")

        # Add virtual robots to our registry
        for vbot_data in virtual_robots:
            robot_id = vbot_data.get("robot_id")
            if not robot_id:
                continue

            # Skip if we already have this robot
            if robot_id in _robots:
                continue

            # Map vbot types to our robot types
            vbot_type = vbot_data.get("robot_type", "scout")
            robot_type_map = {
                "scout": RobotType.VSCOUT,
                "scout_e": RobotType.VSCOUT_E,
                "go2": RobotType.VGO2,
                "g1": RobotType.VG1,
                "robbie": RobotType.VROBBIE,
            }
            robot_type = robot_type_map.get(vbot_type, RobotType.VSCOUT)

            # Create robot entry
            robot = Robot(
                id=robot_id,
                name=f"Virtual {vbot_type.title()} ({robot_id})",
                type=robot_type,
                status=RobotStatus.IDLE,  # Assume idle initially
                capabilities=get_default_capabilities(robot_type),
                position=RobotPosition(
                    x=vbot_data.get("position", {}).get("x", 0.0),
                    y=vbot_data.get("position", {}).get("y", 0.0),
                    z=vbot_data.get("position", {}).get("z", 0.0),
                    heading=0.0,
                    floor="virtual",
                ),
                last_seen=datetime.now(),
                firmware_version=f"vbot-{vbot_type}",
                ip_address=None,  # Virtual robots don't have IPs
                connected_since=datetime.now(),
                is_virtual=True,
                platform=vbot_data.get("platform", "unity"),
            )

            _robots[robot_id] = robot
            logger.info(f"Added virtual robot: {robot_id} ({robot_type.value})")

    except Exception as e:
        logger.exception(f"Error loading virtual robots from server: {e}")


async def execute_vbot_command(robot: Robot, command_request: RobotCommandRequest):
    """Execute command on a virtual robot."""
    global _vbot_client

    if not _vbot_client:
        raise HTTPException(status_code=500, detail="Virtual robot client not available")

    try:
        if command_request.command == RobotCommand.START_PATROL:
            result = await _vbot_client.start_vbot_patrol(robot.id)
        elif command_request.command == RobotCommand.STOP_PATROL:
            result = await _vbot_client.stop_vbot(robot.id)
        elif command_request.command == RobotCommand.RETURN_HOME:
            # For virtual robots, return to origin
            result = await _vbot_client.update_vbot(
                robot.id, position={"x": 0.0, "y": 0.0, "z": 0.0}
            )
        elif command_request.command == RobotCommand.STOP:
            result = await _vbot_client.stop_vbot(robot.id)
        elif command_request.command == RobotCommand.REBOOT:
            # Simulate reboot for virtual robot
            robot.status = RobotStatus.OFFLINE
            await asyncio.sleep(2)
            robot.status = RobotStatus.IDLE
            result = {"success": True, "message": "Virtual robot rebooted"}
        elif command_request.command == RobotCommand.DELETE_VBOT:
            # Delete virtual robot
            result = await _vbot_client.delete_vbot(robot.id)
            if result.get("success"):
                # Remove from our registry
                if robot.id in _robots:
                    del _robots[robot.id]
        else:
            result = {
                "success": True,
                "message": f"Command {command_request.command} not implemented for virtual robots",
            }

        if not result.get("success"):
            logger.error(f"Virtual robot command failed: {result}")
            raise HTTPException(status_code=500, detail=result.get("error", "Command failed"))

    except Exception as e:
        logger.exception(f"Error executing virtual robot command: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Vbot integration will be initialized when the server starts up


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
            robot_dict["battery_percentage"] = (
                robot.telemetry.battery_level if robot.telemetry else None
            )
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
        robot_dict["battery_percentage"] = (
            robot.telemetry.battery_level if robot.telemetry else None
        )

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
            if robot.status == RobotStatus.OFFLINE and not robot.is_virtual:
                raise HTTPException(status_code=400, detail=f"Robot {robot_id} is offline")

        logger.info(f"Executing command {command_request.command} on robot {robot_id}")

        # Execute command based on robot type
        if robot.is_virtual:
            # Handle virtual robot commands
            await execute_vbot_command(robot, command_request)
            result = {
                "success": True,
                "message": f"Virtual robot command {command_request.command} executed",
            }

        elif robot.type == RobotType.SCOUT:
            # Use Moorebot client
            scout_client = MoorebotScoutClient(
                robot.ip_address or "192.168.1.150",
                mock_mode=_robot_hardware_mock_mode(robot),
            )

            if command_request.command == RobotCommand.START_PATROL:
                result = await scout_client.start_patrol()
                if result.get("success"):
                    robot.status = RobotStatus.PATROLLING
            elif command_request.command == RobotCommand.STOP_PATROL:
                result = await scout_client.stop_patrol()
                if result.get("success"):
                    robot.status = RobotStatus.ONLINE
            elif command_request.command == RobotCommand.RETURN_HOME:
                result = await scout_client.return_to_dock()
                if result.get("success"):
                    robot.status = (
                        RobotStatus.CHARGING
                        if result.get("docking_status") == "success"
                        else RobotStatus.DOCKED
                    )
            elif command_request.command == RobotCommand.STOP:
                result = await scout_client.stop()
                if result.get("success"):
                    robot.status = RobotStatus.IDLE
            elif command_request.command == RobotCommand.REBOOT:
                # Simulate reboot
                robot.status = RobotStatus.OFFLINE
                await asyncio.sleep(2)
                robot.status = RobotStatus.ONLINE
                result = {"success": True, "message": "Reboot completed"}

            # For unsupported commands, simulate success
            if "result" not in locals():
                result = {
                    "success": True,
                    "message": f"Command {command_request.command} simulated",
                }

        elif robot.type == RobotType.GO2:
            # Use Go2 client
            go2_client = UnitreeGo2Client(
                robot.ip_address or "192.168.1.120",
                mock_mode=_robot_hardware_mock_mode(robot),
            )

            if command_request.command == RobotCommand.START_PATROL:
                result = await go2_client.start_patrol()
                if result.get("success"):
                    robot.status = RobotStatus.PATROLLING
            elif command_request.command == RobotCommand.STOP_PATROL:
                result = await go2_client.stop_patrol()
                if result.get("success"):
                    robot.status = RobotStatus.IDLE
            elif command_request.command == RobotCommand.RETURN_HOME:
                result = await go2_client.return_to_dock()
                if result.get("success"):
                    robot.status = (
                        RobotStatus.CHARGING
                        if result.get("docking_status") == "success"
                        else RobotStatus.DOCKED
                    )
            elif command_request.command == RobotCommand.STOP:
                result = await go2_client.stop()
                if result.get("success"):
                    robot.status = RobotStatus.IDLE
            elif command_request.command == RobotCommand.REBOOT:
                # Simulate reboot
                robot.status = RobotStatus.OFFLINE
                await asyncio.sleep(3)  # Go2 takes longer to reboot
                robot.status = RobotStatus.IDLE
                result = {"success": True, "message": "Go2 reboot completed"}

            # For unsupported commands, simulate success
            if "result" not in locals():
                result = {
                    "success": True,
                    "message": f"Go2 command {command_request.command} simulated",
                }

        elif robot.type == RobotType.DREAMBOT:
            # Use Dreame client via Home Assistant (devices-mcp integration).
            # NOTE: This uses HA entity_ids like "vacuum.dreame_*", not the robot_id in this UI.
            from devices_mcp.config import get_config
            import os

            cfg = get_config()
            ha_cfg = cfg.get("homeassistant", {}) or cfg.get("security", {}).get("integrations", {}).get("homeassistant", {}) or {}
            ha_url = ha_cfg.get("url") or ha_cfg.get("server_url") or "http://localhost:8123"
            ha_token = ha_cfg.get("access_token") or ha_cfg.get("token")
            dreame_mcp_url = os.getenv("DREAME_MCP_URL")
            dreame_client = DreameClient(
                str(ha_url),
                token=str(ha_token) if ha_token else None,
                dreame_mcp_url=dreame_mcp_url,
            )
            await dreame_client.connect()
            entity_id = None
            if getattr(dreame_client, "entities", None):
                entity_id = (dreame_client.entities[0] or {}).get("entity_id")
            if not entity_id and getattr(dreame_client, "_mode", "") == "ha":
                raise HTTPException(status_code=503, detail="No Dreame vacuum entity found in Home Assistant")

            if command_request.command == RobotCommand.START_CLEANING:
                result = await dreame_client.start_cleaning(str(entity_id or ""))
                if result.get("success"):
                    robot.status = RobotStatus.CLEANING
            elif command_request.command == RobotCommand.STOP_CLEANING:
                result = await dreame_client.stop_cleaning(str(entity_id or ""))
                if result.get("success"):
                    robot.status = RobotStatus.ONLINE
            elif command_request.command == RobotCommand.RETURN_HOME:
                result = await dreame_client.return_to_dock(str(entity_id or ""))
                if result.get("success"):
                    robot.status = RobotStatus.DOCKED
            elif command_request.command == RobotCommand.PAUSE:
                result = await dreame_client.pause_cleaning(str(entity_id or ""))
                if result.get("success"):
                    robot.status = RobotStatus.ONLINE
            else:
                result = {
                    "success": True,
                    "message": f"Dreame command {command_request.command} simulated",
                }

        elif robot.type == RobotType.YAHBOOM:
            # Use Yahboom client
            yahboom_client = YahboomClient(robot.ip_address or "192.168.1.60")
            await yahboom_client.connect()

            if command_request.command == RobotCommand.START_PATROL:
                result = await yahboom_client.start_patrol()
                if result.get("success"):
                    robot.status = RobotStatus.PATROLLING
            elif command_request.command == RobotCommand.STOP_PATROL:
                result = await yahboom_client.stop()
                if result.get("success"):
                    robot.status = RobotStatus.IDLE
            elif command_request.command == RobotCommand.RETURN_HOME:
                result = await yahboom_client.return_to_dock()
                if result.get("success"):
                    robot.status = RobotStatus.DOCKED
            elif command_request.command == RobotCommand.STOP:
                result = await yahboom_client.stop()
                if result.get("success"):
                    robot.status = RobotStatus.IDLE
            else:
                result = {
                    "success": True,
                    "message": f"Yahboom command {command_request.command} simulated",
                }

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
            "message": result.get(
                "message", f"Command {command_request.command} executed on {robot_id}"
            ),
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
        if robot.is_virtual:
            # Get virtual robot telemetry
            global _vbot_client
            if _vbot_client:
                status_result = await _vbot_client.get_vbot_status(robot.id)
                if status_result.get("success"):
                    telemetry = RobotTelemetry(
                        battery_level=100.0,  # Virtual robots don't drain battery
                        battery_voltage=0.0,
                        temperature=25.0,  # Room temperature
                        cpu_usage=10.0,  # Low usage for virtual
                        memory_usage=25.0,  # Memory usage in Unity/VRChat
                        wifi_signal=-30,  # Virtual connection
                        last_update=datetime.now(),
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

        elif robot.type == RobotType.SCOUT:
            # Use Moorebot client
            scout_client = MoorebotScoutClient(
                robot.ip_address or "192.168.1.150",
                mock_mode=_robot_hardware_mock_mode(robot),
            )
            status_data = await scout_client.get_status()
            sensor_data = await scout_client.get_sensor_data()

            telemetry = RobotTelemetry(
                battery_level=status_data.get("battery_level", 85.0),
                battery_voltage=12.6,  # Typical LiPo voltage
                temperature=35.0,  # Estimated CPU temperature
                cpu_usage=45.0,  # Estimated
                memory_usage=60.0,  # Estimated
                wifi_signal=status_data.get("wifi_signal", -45),
                last_update=datetime.now(),
            )

            # Update position from sensor data
            robot.position.x = status_data.get("position", {}).get("x", robot.position.x)
            robot.position.y = status_data.get("position", {}).get("y", robot.position.y)
            robot.position.heading = status_data.get("position", {}).get(
                "heading", robot.position.heading
            )

        elif robot.type == RobotType.GO2:
            # Use Go2 client
            go2_client = UnitreeGo2Client(
                robot.ip_address or "192.168.1.120",
                mock_mode=_robot_hardware_mock_mode(robot),
            )
            status_data = await go2_client.get_status()

            telemetry = RobotTelemetry(
                battery_level=status_data.get("battery_level", 85.0),
                battery_voltage=24.0,  # Go2 uses higher voltage battery
                temperature=status_data.get("temperature", 45.0),  # CPU temperature
                cpu_usage=55.0,  # Estimated for Go2
                memory_usage=65.0,  # Estimated for Go2
                wifi_signal=status_data.get("wifi_signal", -50),
                last_update=datetime.now(),
            )

            # Update position from status data
            pos_data = status_data.get("position", {})
            robot.position.x = pos_data.get("x", robot.position.x)
            robot.position.y = pos_data.get("y", robot.position.y)
            robot.position.heading = pos_data.get("yaw", robot.position.heading)

        elif robot.type == RobotType.DREAMBOT:
            from devices_mcp.config import get_config
            import os

            cfg = get_config()
            ha_cfg = cfg.get("homeassistant", {}) or cfg.get("security", {}).get("integrations", {}).get("homeassistant", {}) or {}
            ha_url = ha_cfg.get("url") or ha_cfg.get("server_url") or "http://localhost:8123"
            ha_token = ha_cfg.get("access_token") or ha_cfg.get("token")
            dreame_mcp_url = os.getenv("DREAME_MCP_URL")
            dreame_client = DreameClient(
                str(ha_url),
                token=str(ha_token) if ha_token else None,
                dreame_mcp_url=dreame_mcp_url,
            )
            await dreame_client.connect()
            status_obj = await dreame_client.get_status()
            status_data = status_obj.__dict__ if status_obj else {}

            telemetry = RobotTelemetry(
                battery_level=status_data.get("battery_level", 85.0),
                battery_voltage=14.4,  # Typical vacuum voltage
                temperature=30.0,
                cpu_usage=20.0,
                memory_usage=40.0,
                wifi_signal=-55,
                last_update=datetime.now(),
            )

        elif robot.type == RobotType.YAHBOOM:
            # Use Yahboom client
            yahboom_client = YahboomClient(robot.ip_address or "192.168.1.60")
            await yahboom_client.connect()
            status_data = await yahboom_client.get_status()

            telemetry = RobotTelemetry(
                battery_level=status_data.get("battery_level", 95.0),
                battery_voltage=12.0,
                temperature=status_data.get("temperature", 38.0),
                cpu_usage=15.0,
                memory_usage=30.0,
                wifi_signal=-40,
                last_update=datetime.now(),
            )

            # Update position
            pos = status_data.get("position", {})
            robot.position.x = pos.get("x", robot.position.x)
            robot.position.y = pos.get("y", robot.position.y)
            robot.position.heading = pos.get("yaw", robot.position.heading)

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


@router.post("/discover")
async def discover_robots():
    """Discover robots on the network."""
    try:
        # This would implement actual network discovery
        # For now, return current registered robots
        discovered = []
        for robot in _robots.values():
            discovered.append(
                {
                    "id": robot.id,
                    "name": robot.name,
                    "type": robot.type,
                    "ip_address": robot.ip_address,
                    "discovered_at": datetime.now().isoformat(),
                }
            )

        return {
            "success": True,
            "discovered_robots": discovered,
            "message": f"Discovered {len(discovered)} robots",
        }
    except Exception as e:
        logger.exception("Failed to discover robots")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/create_vbot")
async def create_virtual_robot(request: Dict[str, Any]):
    """Create a new virtual robot."""
    try:
        global _vbot_client

        if not _vbot_client:
            raise HTTPException(status_code=500, detail="Virtual robot client not available")

        robot_type = request.get("robot_type", "scout")
        platform = request.get("platform", "unity")

        # Create virtual robot via robotics-mcp server
        result = await _vbot_client.create_vbot(robot_type, platform=platform)

        if result.get("success"):
            robot_id = result.get("robot_id")
            if robot_id:
                # Add to our local registry
                await load_virtual_robots_from_server()
                return {
                    "success": True,
                    "message": f"Virtual robot {robot_id} created successfully",
                    "robot_id": robot_id,
                }

        return {
            "success": False,
            "message": result.get("message", "Failed to create virtual robot"),
        }

    except Exception as e:
        logger.exception("Error creating virtual robot")
        raise HTTPException(status_code=500, detail=str(e))


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
