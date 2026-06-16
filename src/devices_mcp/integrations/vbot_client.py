"""
Virtual Robot (Vbot) Client Integration
Provides Python interface to virtual robots managed by robotics-mcp server.
Communicates with FastMCP server via HTTP API calls.
**Timestamp**: 2025-12-29
**Status**: Integration for virtual robots in robotics webapp
"""

import logging
from enum import StrEnum
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class VbotStatus(StrEnum):
    """Virtual robot status states"""

    IDLE = "idle"
    SPAWNED = "spawned"
    ACTIVE = "active"
    MOVING = "moving"
    PATROLLING = "patrolling"
    ERROR = "error"
    OFFLINE = "offline"


class VbotType(StrEnum):
    """Supported virtual robot types"""

    SCOUT = "scout"  # Moorebot Scout
    SCOUT_E = "scout_e"  # Moorebot Scout E
    GO2 = "go2"  # Unitree Go2
    G1 = "g1"  # Unitree G1
    ROBBIE = "robbie"  # Robbie from Forbidden Planet
    CUSTOM = "custom"  # Custom robot type


class VbotClient:
    """
    Client for virtual robots managed by robotics-mcp server.
    FEATURES:
    - CRUD operations (create, read, update, delete, list)
    - Virtual robot operations (spawn, status, lidar, navigation)
    - Environment loading and management
    - Real-time synchronization with physical robots
    REQUIREMENTS:
    - Robotics-mcp server running and accessible
    - HTTP API endpoint for MCP tool calls
    - Virtual robot assets in Unity/VRChat
    Args:
        mcp_server_url: URL of the robotics-mcp server (e.g., "http://localhost:8001")
        timeout: Request timeout in seconds (default: 30)
    Returns:
        Initialized client ready for virtual robot control
    Examples:
        # Connect to robotics-mcp server
        client = VbotClient("http://localhost:8001")
        # List all vbots
        vbots = await client.list_vbots()
        # Create a new Scout vbot
        result = await client.create_vbot("scout", position={"x": 0, "y": 0, "z": 0})
        # Control vbot
        await client.move_vbot("vbot_scout_01", linear=0.5, angular=0.0)
    """

    def __init__(self, mcp_server_url: str, timeout: int = 30):
        self.mcp_server_url = mcp_server_url.rstrip("/")
        self.timeout = timeout
        self.session: aiohttp.ClientSession | None = None
        logger.info(f"VbotClient initialized: {mcp_server_url}")

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()

    async def connect(self) -> dict:
        """
        Connect to the robotics-mcp server.
        Returns:
            Connection status
        """
        try:
            if self.session and not self.session.closed:
                await self.session.close()
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
            # Test connection by calling a simple tool
            test_result = await self._call_mcp_tool("robotics_system", {"operation": "status"})
            if test_result.get("success"):
                logger.info("Connected to robotics-mcp server")
                return {"success": True, "server_status": test_result}
            logger.error(f"Failed to connect to robotics-mcp server: {test_result}")
            return {"success": False, "message": "Server connection failed", "error": "Server connection failed"}
        except Exception as e:
            logger.exception("Error connecting to robotics-mcp server:")
            return {"success": False, "message": str(e), "error": str(e)}

    async def disconnect(self):
        """Disconnect from the server"""
        if self.session and not self.session.closed:
            await self.session.close()
        logger.info("Disconnected from robotics-mcp server")

    async def _call_mcp_tool(self, tool_name: str, arguments: dict) -> dict:
        """
        Call an MCP tool via HTTP API.
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments
        Returns:
            Tool result
        """
        if not self.session:
            return {"success": False, "message": "Not connected", "error": "Not connected"}
        try:
            url = f"{self.mcp_server_url}/api/v1/tools/{tool_name}"
            payload = arguments
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("result", result)
                error_text = await response.text()
                logger.error(f"MCP tool call failed: {response.status} - {error_text}")
                return {
                    "success": False,
                    "message": f"HTTP {response.status}: {error_text}",
                    "error": f"HTTP {response.status}: {error_text}",
                }
        except TimeoutError:
            logger.exception("MCP tool call timed out:")
            return {"success": False, "message": "Request timeout", "error": "Request timeout"}
        except Exception as e:
            logger.exception("Error calling MCP tool {tool_name}:")
            return {"success": False, "message": str(e), "error": str(e)}

    # CRUD Operations
    async def create_vbot(
        self,
        robot_type: str,
        platform: str = "unity",
        position: dict[str, float] | None = None,
        scale: float | None = None,
        metadata: dict[str, Any] | None = None,
        model_path: str | None = None,
    ) -> dict:
        """
        Create a new virtual robot.
        Args:
            robot_type: Type of robot ("scout", "go2", "g1", "robbie", "custom")
            platform: Target platform ("unity" or "vrchat")
            position: Initial position {"x": float, "y": float, "z": float}
            scale: Size multiplier
            metadata: Additional metadata
            model_path: Path to custom model (for "custom" type)
        Returns:
            Creation result with vbot details
        """
        args = {"operation": "create", "robot_type": robot_type, "platform": platform}
        if position:
            args["position"] = position
        if scale is not None:
            args["scale"] = scale
        if metadata:
            args["metadata"] = metadata
        if model_path:
            args["model_path"] = model_path
        result = await self._call_mcp_tool("robot_virtual", args)
        if result.get("success"):
            logger.info(f"Created vbot: {robot_type} - {result.get('robot_id', 'unknown')}")
        else:
            logger.error(f"Failed to create vbot: {result}")
        return result

    async def read_vbot(self, robot_id: str) -> dict:
        """
        Get details of a virtual robot.
        Args:
            robot_id: Virtual robot ID
        Returns:
            Vbot details
        """
        args = {"operation": "read", "robot_id": robot_id}
        result = await self._call_mcp_tool("robot_virtual", args)
        return result

    async def update_vbot(
        self,
        robot_id: str,
        position: dict[str, float] | None = None,
        scale: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """
        Update virtual robot properties.
        Args:
            robot_id: Virtual robot ID
            position: New position
            scale: New scale
            metadata: New metadata
        Returns:
            Update result
        """
        args = {"operation": "update", "robot_id": robot_id}
        if position:
            args["position"] = position
        if scale is not None:
            args["scale"] = scale
        if metadata:
            args["metadata"] = metadata
        result = await self._call_mcp_tool("robot_virtual", args)
        if result.get("success"):
            logger.info(f"Updated vbot: {robot_id}")
        else:
            logger.error(f"Failed to update vbot {robot_id}: {result}")
        return result

    async def delete_vbot(self, robot_id: str) -> dict:
        """
        Delete a virtual robot.
        Args:
            robot_id: Virtual robot ID
        Returns:
            Deletion result
        """
        args = {"operation": "delete", "robot_id": robot_id}
        result = await self._call_mcp_tool("robot_virtual", args)
        if result.get("success"):
            logger.info(f"Deleted vbot: {robot_id}")
        else:
            logger.error(f"Failed to delete vbot {robot_id}: {result}")
        return result

    async def list_physical_robots(self) -> dict:
        """
        List all available physical robots from the robotics MCP.
        Returns:
            List of physical robots available
        """
        args = {"operation": "list_physical"}
        result = await self._call_mcp_tool("robot_physical", args)
        return result

    async def list_vbots(self, robot_type: str | None = None) -> dict:
        """
        List all virtual robots.
        Args:
            robot_type: Filter by robot type
        Returns:
            List of vbots
        """
        args = {"operation": "list"}
        if robot_type:
            args["robot_type"] = robot_type
        result = await self._call_mcp_tool("robot_virtual", args)
        return result

    # Virtual Robot Operations
    async def spawn_vbot(
        self,
        robot_type: str,
        platform: str = "unity",
        position: dict[str, float] | None = None,
        scale: float | None = None,
    ) -> dict:
        """
        Spawn a virtual robot (alias for create).
        Args:
            robot_type: Type of robot
            platform: Target platform
            position: Initial position
            scale: Size multiplier
        Returns:
            Spawn result
        """
        return await self.create_vbot(robot_type, platform, position, scale)

    async def get_vbot_status(self, robot_id: str) -> dict:
        """
        Get virtual robot status.
        Args:
            robot_id: Virtual robot ID
        Returns:
            Status information
        """
        args = {"operation": "get_status", "robot_id": robot_id}
        result = await self._call_mcp_tool("robot_virtual", args)
        return result

    async def get_vbot_lidar(self, robot_id: str) -> dict:
        """
        Get virtual LiDAR scan data.
        Args:
            robot_id: Virtual robot ID
        Returns:
            LiDAR scan data
        """
        args = {"operation": "get_lidar", "robot_id": robot_id}
        result = await self._call_mcp_tool("robot_virtual", args)
        return result

    async def set_vbot_scale(self, robot_id: str, scale: float) -> dict:
        """
        Set virtual robot scale.
        Args:
            robot_id: Virtual robot ID
            scale: Size multiplier
        Returns:
            Scale result
        """
        args = {"operation": "set_scale", "robot_id": robot_id, "scale": scale}
        result = await self._call_mcp_tool("robot_virtual", args)
        if result.get("success"):
            logger.info(f"Set vbot scale: {robot_id} = {scale}")
        else:
            logger.error(f"Failed to set vbot scale {robot_id}: {result}")
        return result

    async def test_vbot_navigation(self, robot_id: str) -> dict:
        """
        Test pathfinding for virtual robot.
        Args:
            robot_id: Virtual robot ID
        Returns:
            Navigation test result
        """
        args = {"operation": "test_navigation", "robot_id": robot_id}
        result = await self._call_mcp_tool("robot_virtual", args)
        return result

    async def sync_vbot_with_physical(self, robot_id: str) -> dict:
        """
        Sync virtual robot state with physical robot.
        Args:
            robot_id: Virtual robot ID
        Returns:
            Sync result
        """
        args = {"operation": "sync_with_physical", "robot_id": robot_id}
        result = await self._call_mcp_tool("robot_virtual", args)
        if result.get("success"):
            logger.info(f"Synced vbot with physical: {robot_id}")
        else:
            logger.error(f"Failed to sync vbot {robot_id}: {result}")
        return result

    async def load_environment(
        self, environment: str, environment_path: str | None = None, platform: str = "unity"
    ) -> dict:
        """
        Load environment into virtual scene.
        Args:
            environment: Environment name
            environment_path: Path to environment file
            platform: Target platform
        Returns:
            Environment load result
        """
        args = {"operation": "load_environment", "environment": environment, "platform": platform}
        if environment_path:
            args["environment_path"] = environment_path
        result = await self._call_mcp_tool("robot_virtual", args)
        if result.get("success"):
            logger.info(f"Loaded environment: {environment}")
        else:
            logger.error(f"Failed to load environment {environment}: {result}")
        return result

    # Control Operations (via robot_behavior tool)
    async def move_vbot(self, robot_id: str, linear: float = 0.0, angular: float = 0.0, duration: float = 0.0) -> dict:
        """
        Move virtual robot.
        Args:
            robot_id: Virtual robot ID
            linear: Linear velocity (m/s)
            angular: Angular velocity (rad/s)
            duration: Movement duration (seconds)
        Returns:
            Movement result
        """
        args = {
            "robot_id": robot_id,
            "category": "animation",
            "action": "animate_movement",
            "wheel_speeds": {
                "front_left": linear + angular,
                "front_right": linear - angular,
                "rear_left": linear + angular,
                "rear_right": linear - angular,
            },
        }
        if duration > 0:
            args["duration"] = duration
        result = await self._call_mcp_tool("robot_behavior", args)
        if result.get("success"):
            logger.info(f"Moved vbot: {robot_id} linear={linear}, angular={angular}")
        else:
            logger.error(f"Failed to move vbot {robot_id}: {result}")
        return result

    async def start_vbot_patrol(self, robot_id: str, route: str = "default") -> dict:
        """
        Start virtual robot patrol.
        Args:
            robot_id: Virtual robot ID
            route: Patrol route name
        Returns:
            Patrol result
        """
        args = {
            "robot_id": robot_id,
            "category": "navigation",
            "action": "follow_path",
            "path_id": route,
        }
        result = await self._call_mcp_tool("robot_behavior", args)
        if result.get("success"):
            logger.info(f"Started vbot patrol: {robot_id} route={route}")
        else:
            logger.error(f"Failed to start vbot patrol {robot_id}: {result}")
        return result

    async def stop_vbot(self, robot_id: str) -> dict:
        """
        Stop virtual robot movement.
        Args:
            robot_id: Virtual robot ID
        Returns:
            Stop result
        """
        args = {"robot_id": robot_id, "category": "animation", "action": "stop_animation"}
        result = await self._call_mcp_tool("robot_behavior", args)
        if result.get("success"):
            logger.info(f"Stopped vbot: {robot_id}")
        else:
            logger.error(f"Failed to stop vbot {robot_id}: {result}")
        return result

    async def get_vbot_camera_feed(self, robot_id: str) -> dict:
        """
        Get virtual robot camera feed.
        Args:
            robot_id: Virtual robot ID
        Returns:
            Camera feed info
        """
        args = {"robot_id": robot_id, "category": "camera", "action": "get_virtual_camera"}
        result = await self._call_mcp_tool("robot_behavior", args)
        return result
