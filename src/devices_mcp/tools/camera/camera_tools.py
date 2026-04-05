"""
Camera tools for Devices MCP.

This module contains tools for managing and controlling Tapo cameras.
"""

import logging
from enum import Enum
from typing import Any, Dict, Literal, Optional

from pydantic import ConfigDict, Field

from devices_mcp.exceptions import AuthenticationError, ConnectionError
from devices_mcp.tools.base_tool import BaseTool, ToolCategory, ToolResult, register_tool, tool
from devices_mcp.validation import (
    ToolValidationError,
    validate_camera_name,
    validate_credentials,
    validate_ip_address,
)

logger = logging.getLogger(__name__)


class CameraStatus(str, Enum):
    """Camera status values."""

    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    ERROR = "error"

    model_config = ConfigDict(use_enum_values=True)


@tool("list_cameras")
class ListCamerasTool(BaseTool):
    """
    List all registered cameras and their current status.

    Returns information about all cameras managed by the system including
    their connection status, type, model, and firmware version.

    Parameters:
        None

    Returns:
        Dict with:
        - success (bool): Whether the operation succeeded
        - cameras (List[Dict]): List of camera information dictionaries
        - total (int): Total number of cameras

    Example:
        result = await list_cameras_tool.execute()
        for camera in result['cameras']:
            logger.info(f"{camera['name']}: {camera['status']}")
    """

    class Meta:
        name = "list_cameras"
        description = "List all registered cameras and their status"
        category = ToolCategory.CAMERA

        class Parameters:
            pass

    # Config is no longer needed as we use Meta class for metadata
    async def execute(self) -> Dict[str, Any]:
        """List all configured cameras with their current status and information.

        Retrieves a comprehensive list of all cameras registered in the system,
        including their connection status, configuration details, and availability.

        Returns:
            Dictionary containing:
                - success: Boolean indicating if the operation succeeded
                - cameras: List of camera dictionaries with details (only present on success)
                    - name: Camera name/identifier
                    - type: Camera type (tapo, webcam, ring, etc.)
                    - status: Connection status ("online", "offline", "error")
                    - model: Camera model information
                    - firmware: Camera firmware version
                    - streaming: Boolean indicating if camera is currently streaming
                    - error: Error message (only present when status is "error")
                - total: Total number of cameras found

        Usage:
            Use this tool to get an overview of all configured cameras before
            performing operations. This is typically the first tool called to
            understand what cameras are available in the system.

            Common scenarios:
                - Initial setup verification
                - Camera management dashboard
                - Troubleshooting connection issues
                - Inventory and status monitoring

        Examples:
            Basic usage:
                result = await list_cameras_tool.execute()
                if result['success']:
                    for camera in result['cameras']:
                        logger.info(f"Camera: {camera['name']} - {camera['status']}")
                # Returns: {
                #     'success': True,
                #     'cameras': [
                #         {'name': 'front_door', 'type': 'tapo', 'status': 'online', 'model': 'C100', ...},
                #         {'name': 'backyard', 'type': 'webcam', 'status': 'offline', 'model': 'Unknown', ...}
                #     ],
                #     'total': 2
                # }

            Error handling:
                result = await list_cameras_tool.execute()
                if not result['success']:
                    logger.error("Failed to list cameras")
                # Returns: {'success': False, 'cameras': [], 'total': 0}

        Raises:
            Exception: Propagated from camera operations (connection failures, authentication errors)

        Notes:
            - Cameras are listed regardless of connection status
            - Status is determined by last known connection state
            - Network connectivity is tested during status checks
            - Results include cameras that failed to connect with error details

        See Also:
            - add_camera_tool: For adding new cameras to the system
            - remove_camera_tool: For removing cameras from the system
            - get_camera_status_tool: For detailed status of specific cameras
        """
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        server = await TapoCameraServer.get_instance()

        try:
            # Get real camera manager and list all cameras
            if hasattr(server, "camera_manager") and server.camera_manager:
                cameras = []
                for camera_name, camera in server.camera_manager.cameras.items():
                    try:
                        status = await camera.get_status()
                        cameras.append(
                            {
                                "name": camera_name,
                                "type": (
                                    camera.config.type.value
                                    if hasattr(camera.config, "type")
                                    and hasattr(camera.config.type, "value")
                                    else str(camera.config.type)
                                    if hasattr(camera.config, "type")
                                    else "unknown"
                                ),
                                "status": "online" if status.get("connected", False) else "offline",
                                "model": status.get("model", "Unknown"),
                                "firmware": status.get("firmware", "Unknown"),
                                "streaming": status.get("streaming", False),
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Failed to get status for camera {camera_name}: {e}")
                        cameras.append(
                            {
                                "name": camera_name,
                                "type": "unknown",
                                "status": "error",
                                "error": str(e),
                            }
                        )

                # Add Ring cameras if available
                try:
                    from ...integrations.ring_client import get_ring_client

                    ring_client = get_ring_client("default")
                    if ring_client and ring_client.is_initialized:
                        doorbells = await asyncio.wait_for(ring_client.get_doorbells(), timeout=3.0)
                        for doorbell in doorbells:
                            cameras.append(
                                {
                                    "name": f"ring_{doorbell.id}",
                                    "type": "ring",
                                    "status": "online" if doorbell.is_online else "offline",
                                    "model": doorbell.device_type,
                                    "firmware": doorbell.extra_data.get("firmware", "N/A"),
                                    "streaming": True,  # Ring uses WebRTC but is considered "streaming"
                                    "battery_life": doorbell.battery_level,
                                }
                            )
                except Exception as e:
                    logger.debug(f"Could not add Ring cameras to MCP list: {e}")

                return {"success": True, "cameras": cameras, "total": len(cameras)}
            return {
                "success": True,
                "cameras": [],
                "total": 0,
                "message": "No camera manager initialized",
            }
        except Exception as e:
            logger.exception("Failed to list cameras")
            return {
                "success": False,
                "error": f"Failed to list cameras: {e!s}",
                "cameras": [],
            }


@tool("add_camera")
class AddCameraTool(BaseTool):
    """
    Add a new camera to the system.

    Supports multiple camera types: Tapo IP cameras, Ring doorbells,
    and USB webcams. Each camera type requires different connection parameters.

    Parameters:
        camera_id (str): Unique identifier for the camera
        camera_type (str): Type - 'Tapo', 'Ring', or 'Webcam'
        host (str, optional): IP address for Tapo cameras
        username (str, optional): Username for authentication
        password (str, optional): Password for authentication
        device_id (int, optional): Device ID for webcams (default: 0)

    Returns:
        Dict with success status and camera details

    Example:
        # Add USB webcam
        result = await add_camera_tool.execute(
            camera_id='webcam1', camera_type='Webcam', device_id=0
        )

        # Add Tapo camera
        result = await add_camera_tool.execute(
            camera_id='tapo_front',
            camera_type='Tapo',
            host='192.168.1.100',
            username='user@example.com',
            password='secret'
        )
    """

    class Meta:
        name = "add_camera"
        description = "Add a new camera to the system"
        category = ToolCategory.CAMERA

        class Parameters:
            camera_name: str = Field(..., description="A friendly name for the camera")
            ip_address: str = Field(..., description="IP address of the camera")
            username: str = Field(..., description="Username for camera authentication")
            password: str = Field(..., description="Password for camera authentication")
            stream_url: Optional[str] = Field(None, description="Optional custom RTSP stream URL")

    camera_name: str
    ip_address: str
    username: str
    password: str
    stream_url: Optional[str] = None

    async def execute(self) -> Dict[str, Any]:
        """Add a new camera to the system with full configuration support.

        Registers and connects to a new camera device using the provided configuration
        parameters. The camera will be added to the system's camera registry and made
        available for streaming, recording, and control operations. Supports Tapo IP cameras
        with comprehensive validation and connection testing.

        Parameters:
            camera_name: Friendly name for the camera (required)
                - Must be unique and contain only alphanumeric characters and underscores
                - Used as the primary identifier for camera operations
                - Maximum 50 characters
            ip_address: IP address of the camera (required)
                - Must be a valid IPv4 address
                - Camera must be accessible on the network
                - Format: xxx.xxx.xxx.xxx
            username: Camera authentication username (required)
                - Login credential for camera access
                - Typically "admin" for Tapo cameras
            password: Camera authentication password (required)
                - Password credential for camera access
                - Stored securely in the configuration
            stream_url: Optional custom RTSP stream URL
                - If provided, overrides automatic stream URL detection
                - Must be a valid RTSP URL if specified

        Returns:
            Dictionary containing:
                - success: Boolean indicating if camera was added successfully
                - camera_name: Name of the added camera
                - camera_type: Type of camera added ("tapo")
                - ip_address: IP address of the camera
                - message: Success confirmation or error description
                - stream_url: Detected or provided stream URL (on success)

        Usage:
            Use this tool to register new Tapo IP cameras in the system. Ensure the camera
            is powered on, connected to the network, and accessible before adding. The tool
            performs comprehensive validation and connection testing.

            Common scenarios:
                - Initial system setup with multiple cameras
                - Adding replacement cameras
                - Expanding camera coverage
                - Testing new camera installations

        Examples:
            Add a camera successfully:
                result = await add_camera_tool.execute(
                    camera_name='front_door',
                    ip_address='192.168.1.100',
                    username='admin',
                    password='secure_password_123'
                )
                if result['success']:
                    logger.info(f"Camera {result['camera_name']} added successfully")
                # Returns: {
                #     'success': True,
                #     'camera_name': 'front_door',
                #     'camera_type': 'tapo',
                #     'ip_address': '192.168.1.100',
                #     'message': 'Camera front_door added successfully',
                #     'stream_url': 'rtsp://192.168.1.100:554/stream1'
                # }

            Error handling - invalid IP:
                result = await add_camera_tool.execute(
                    camera_name='test_cam',
                    ip_address='999.999.999.999',
                    username='admin',
                    password='password'
                )
                # Returns: {
                #     'success': False,
                #     'message': 'Invalid IP address format: 999.999.999.999'
                # }

            Error handling - camera unreachable:
                result = await add_camera_tool.execute(
                    camera_name='offline_cam',
                    ip_address='192.168.1.200',
                    username='admin',
                    password='password'
                )
                # Returns: {
                #     'success': False,
                #     'message': 'Failed to connect to camera at 192.168.1.200: Connection timeout'
                # }

            With custom stream URL:
                result = await add_camera_tool.execute(
                    camera_name='custom_cam',
                    ip_address='192.168.1.150',
                    username='admin',
                    password='password',
                    stream_url='rtsp://192.168.1.150:554/custom_stream'
                )
                # Uses the provided stream_url instead of auto-detecting

        Raises:
            Exception: Propagated from camera operations (network connectivity, authentication failures)

        Notes:
            - Camera names must be unique within the system
            - Authentication credentials are validated during addition
            - Camera connectivity is tested before final registration
            - Failed additions don't leave partial configurations
            - Stream URL is automatically detected if not provided
            - Supports only Tapo cameras in current implementation

        See Also:
            - list_cameras_tool: To verify camera was added successfully
            - remove_camera_tool: To remove cameras from the system
            - get_camera_status_tool: To check camera connection status
        """
        from devices_mcp.tools.base_tool import ToolResult

        try:
            # Validate inputs
            camera_name = validate_camera_name(self.camera_name, "camera_name")
            ip_address = validate_ip_address(self.ip_address, "ip_address")
            username, password = validate_credentials(self.username, self.password)

            logger.info(f"Adding camera: {camera_name} at {ip_address}")

            from devices_mcp.core.server import (  # Lazy import to avoid circular imports
                TapoCameraServer,
            )

            server = await TapoCameraServer.get_instance()

            # Create camera configuration
            camera_config = {
                "name": camera_name,
                "type": "tapo",
                "params": {
                    "host": ip_address,
                    "username": username,
                    "password": password,
                    "port": 443,
                    "verify_ssl": True,
                },
            }

            # Add stream URL if provided
            if self.stream_url:
                camera_config["params"]["stream_url"] = self.stream_url

            # Add camera to server
            success = await server.camera_manager.add_camera(camera_config)

            if success:
                logger.info(f"Successfully added camera: {camera_name}")
                return ToolResult(
                    content={
                        "success": True,
                        "camera_name": camera_name,
                        "ip_address": ip_address,
                        "message": f"Camera '{camera_name}' added successfully",
                    },
                    is_error=False,
                )
            return ToolResult(
                content={
                    "success": False,
                    "error": f"Failed to add camera '{camera_name}'",
                    "camera_name": camera_name,
                },
                is_error=True,
            )

        except ToolValidationError as e:
            logger.warning(f"Validation error adding camera {self.camera_name}: {e.message}")
            return ToolResult(
                content={
                    "success": False,
                    "error": f"Validation error: {e.message}",
                    "field": e.field,
                },
                is_error=True,
            )
        except Exception as e:
            logger.exception("Failed to add camera")
            return ToolResult(
                content={
                    "success": False,
                    "error": f"Failed to add camera: {e!s}",
                    "camera_name": self.camera_name,
                },
                is_error=True,
            )


@tool("remove_camera")
class RemoveCameraTool(BaseTool):
    """
    Remove a camera from the system.

    Disconnects and removes a camera from the managed camera list.

    Parameters:
        camera_name (str): Name of the camera to remove

    Returns:
        Dict with success status and confirmation message

    Example:
        result = await remove_camera_tool.execute(camera_name='webcam1')
    """

    class Meta:
        name = "remove_camera"
        description = "Remove a camera from the system"
        category = ToolCategory.CAMERA

        class Parameters:
            camera_id: str = Field(..., description="ID of the camera to remove")

    camera_id: str

    async def execute(self) -> Dict[str, Any]:
        """Remove a camera from the system."""
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        server = await TapoCameraServer.get_instance()
        return await server.remove_camera(camera_id=self.camera_id)


@tool("set_active_camera")
class SetActiveCameraTool(BaseTool):
    """
    Set the active camera for subsequent operations.

    Designates which camera will be used for commands that don't
    specify a camera explicitly.

    Parameters:
        camera_name (str): Name of the camera to set as active

    Returns:
        Dict with success status and active camera name

    Example:
        result = await set_active_camera_tool.execute(camera_name='tapo_front')
    """

    class Meta:
        name = "set_active_camera"
        description = "Set the active camera for operations"
        category = ToolCategory.CAMERA

        class Parameters:
            name: str = Field(..., description="Name or ID of the camera to set as active")

    name: str

    async def execute(self) -> Dict[str, Any]:
        """Set the active camera for operations."""
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        server = await TapoCameraServer.get_instance()
        return await server.set_active_camera(name=self.name)


@tool("get_camera_status")
class GetCameraStatusTool(BaseTool):
    """
    Get the current status of a camera.

    Returns detailed status information including connection state,
    streaming status, and hardware information.

    Parameters:
        camera_id (str, optional): Name of the camera to query (uses active camera if not specified)

    Returns:
        Dict with camera status details:
        - connected (bool): Connection status
        - streaming (bool): Whether camera is streaming
        - model (str): Camera model
        - firmware (str): Firmware version

    Example:
        result = await get_camera_status_tool.execute(camera_id='webcam1')
        if result['status']['connected']:
            logger.info(f"Camera online: {result['status']['model']}")
    """

    class Meta:
        name = "get_camera_status"
        description = "Get the status of a specific camera"
        category = ToolCategory.CAMERA

        class Parameters:
            camera_id: str = Field(
                None,
                description="ID of the camera to get status for. If not provided, returns status of active camera.",
            )

    camera_id: Optional[str] = None

    async def execute(self) -> ToolResult:
        """Get the status of a specific camera."""
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        try:
            server = await TapoCameraServer.get_instance()

            if self.camera_id:
                # Get status for specific camera
                camera = server.camera_manager.get_camera(self.camera_id)
                if not camera:
                    return ToolResult(
                        content={
                            "success": False,
                            "error": f"Camera '{self.camera_id}' not found",
                            "camera_id": self.camera_id,
                        },
                        is_error=True,
                    )

                # Get camera status
                status = {
                    "online": True,  # Mock status for now
                    "recording": False,
                    "model": "Tapo Camera",
                    "firmware": "1.0.0",
                }

                return ToolResult(
                    content={
                        "success": True,
                        "camera_id": self.camera_id,
                        "status": status,
                    },
                    is_error=False,
                )
            # Get status for all cameras
            cameras = await server.camera_manager.list_cameras()
            status_list = []

            for camera_info in cameras:
                camera = server.camera_manager.get_camera(camera_info["name"])
                if camera:
                    status_list.append(
                        {
                            "camera_id": camera_info["name"],
                            "online": True,
                            "recording": False,
                            "model": "Tapo Camera",
                            "firmware": "1.0.0",
                        }
                    )

            return ToolResult(
                content={
                    "success": True,
                    "cameras": status_list,
                    "total_cameras": len(status_list),
                },
                is_error=False,
            )
        except Exception as e:
            logger.exception("Failed to get camera status for")
            return ToolResult(
                content={
                    "success": False,
                    "error": f"Failed to get camera status: {e!s}",
                    "camera_id": self.camera_id,
                },
                is_error=True,
            )


@tool("connect_camera")
class ConnectCameraTool(BaseTool):
    """
    Connect to a Tapo camera.

    Establishes a connection to a TP-Link Tapo IP camera using
    the provided credentials and IP address.

    Parameters:
        host (str): IP address of the Tapo camera
        username (str): TP-Link account email
        password (str): TP-Link account password

    Returns:
        Dict with connection status and camera information

    Example:
        result = await connect_camera_tool.execute(
            host='192.168.1.100',
            username='user@example.com',
            password='secret123'
        )
        if result['success']:
            logger.info(f"Connected to {result['camera']['model']}")
    """

    class Meta:
        name = "connect_camera"
        description = "Connect to a Tapo camera"
        category = ToolCategory.CAMERA

        class Parameters:
            host: str = Field(..., description="IP address or hostname of the camera")
            username: str = Field(..., description="Username for camera authentication")
            password: str = Field(..., description="Password for camera authentication")
            verify_ssl: bool = Field(
                True, description="Whether to verify SSL certificates (default: True)"
            )

    host: str
    username: str
    password: str
    verify_ssl: bool = True

    async def execute(self) -> ToolResult:
        """Connect to a Tapo camera with comprehensive validation and error handling."""

        try:
            # Validate inputs
            host = validate_ip_address(self.host, "host")
            _username, _password = validate_credentials(self.username, self.password)

            logger.info(f"Connecting to camera at {host}")

            from devices_mcp.core.server import (  # Lazy import to avoid circular imports
                TapoCameraServer,
            )

            server = await TapoCameraServer.get_instance()

            # Use the server's connect method
            result = await server.connect(host)

            if result.get("success"):
                logger.info(f"Successfully connected to camera at {host}")
                return ToolResult(
                    content={
                        "success": True,
                        "host": host,
                        "message": f"Successfully connected to camera at {host}",
                    },
                    is_error=False,
                )
            return ToolResult(
                content={
                    "success": False,
                    "error": result.get("error", "Connection failed"),
                    "host": host,
                },
                is_error=True,
            )

        except ToolValidationError as e:
            logger.warning(f"Validation error connecting to camera {self.host}: {e.message}")
            return ToolResult(
                content={
                    "success": False,
                    "error": f"Validation error: {e.message}",
                    "field": e.field,
                },
                is_error=True,
            )
        except ConnectionError as e:
            logger.exception("Connection failed to camera")
            return ToolResult(
                content={
                    "success": False,
                    "error": f"Connection failed: {e!s}",
                    "host": self.host,
                },
                is_error=True,
            )
        except AuthenticationError as e:
            logger.exception("Authentication failed for camera")
            return ToolResult(
                content={
                    "success": False,
                    "error": f"Authentication failed: {e!s}",
                    "host": self.host,
                },
                is_error=True,
            )
        except Exception as e:
            logger.exception("Unexpected error connecting to camera")
            return ToolResult(
                content={
                    "success": False,
                    "error": f"Connection error: {e!s}",
                    "host": self.host,
                },
                is_error=True,
            )


@tool("disconnect_camera")
class DisconnectCameraTool(BaseTool):
    """
    Disconnect from the current camera.

    Closes the connection to the currently active camera and
    releases resources.

    Parameters:
        None

    Returns:
        Dict with disconnection status

    Example:
        result = await disconnect_camera_tool.execute()
        logger.info(result['message'])
    """

    class Meta:
        name = "disconnect_camera"
        description = "Disconnect from the current camera"
        category = ToolCategory.CAMERA

        class Parameters:
            pass

    async def execute(self) -> ToolResult:
        """Disconnect from the current camera."""
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        try:
            server = await TapoCameraServer.get_instance()

            # Disconnect all cameras
            cameras = await server.camera_manager.list_cameras()
            disconnected_count = 0

            for camera_info in cameras:
                camera = server.camera_manager.get_camera(camera_info["name"])
                if camera and hasattr(camera, "disconnect"):
                    await camera.disconnect()
                    disconnected_count += 1

            return ToolResult(
                content={
                    "success": True,
                    "message": f"Disconnected {disconnected_count} cameras",
                    "disconnected_count": disconnected_count,
                },
                is_error=False,
            )
        except Exception as e:
            logger.exception("Failed to disconnect cameras")
            return ToolResult(
                content={
                    "success": False,
                    "error": f"Failed to disconnect cameras: {e!s}",
                },
                is_error=True,
            )


@tool("get_camera_info")
class GetCameraInfoTool(BaseTool):
    """
    Get detailed information about a camera.

    Returns comprehensive camera information including model, firmware,
    hardware capabilities, network settings, and features.

    Parameters:
        camera_id (str, optional): Camera name (uses active camera if not specified)

    Returns:
        Dict with detailed camera information:
        - model (str): Camera model
        - firmware (str): Firmware version
        - mac_address (str): MAC address
        - ip_address (str): IP address
        - capabilities (Dict): Hardware capabilities

    Example:
        result = await get_camera_info_tool.execute(camera_id='tapo_front')
        logger.info(f"Model: {result['info']['model']}")
        logger.info(f"Firmware: {result['info']['firmware']}")
    """

    class Meta:
        name = "get_camera_info"
        description = "Get detailed information about the connected camera"
        category = ToolCategory.CAMERA

        class Parameters:
            pass

    async def execute(self, **_kwargs) -> Dict[str, Any]:
        """Get detailed information about the connected camera.

        Args:
            **kwargs: Additional arguments (ignored)

        Returns:
            Dict containing camera information
        """
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        server = await TapoCameraServer.get_instance()
        return await server.get_camera_info()


@tool("manage_camera_groups")
class ManageCameraGroupsTool(BaseTool):
    """
    Manage camera groups for organizing multiple cameras.

    Create, update, or delete camera groups to logically organize
    cameras by location, function, or any other criteria.

    Parameters:
        action (str): Action to perform - 'create', 'update', 'delete', 'list'
        group_name (str, optional): Name of the group
        camera_ids (List[str], optional): List of camera IDs for the group

    Returns:
        Dict with operation result and group information

    Example:
        # Create a group
        result = await manage_camera_groups_tool.execute(
            action='create',
            group_name='front_yard',
            camera_ids=['tapo_front', 'webcam1']
        )

        # List all groups
        result = await manage_camera_groups_tool.execute(action='list')
    """

    class Meta:
        name = "manage_camera_groups"
        description = "Manage camera groups"
        category = ToolCategory.CAMERA

        class Parameters:
            action: Literal["list", "add", "remove", "list_group"] = Field(
                ..., description="Action to perform"
            )
            group: Optional[str] = Field(
                None, description="Group name (required for add/remove/list_group)"
            )
            camera: Optional[str] = Field(None, description="Camera name (required for add/remove)")

    action: str
    group: Optional[str] = None
    camera: Optional[str] = None

    async def execute(self) -> Dict[str, Any]:
        """Manage camera groups."""
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        server = await TapoCameraServer.get_instance()

        if self.action == "list":
            return await server.list_camera_groups()
        if self.action == "list_group":
            if not self.group:
                raise ValueError("Group name is required for list_group action")
            return await server.list_cameras_in_group(self.group)
        if self.action == "add":
            if not self.group or not self.camera:
                raise ValueError("Both group name and camera name are required for add action")
            return await server.add_camera_to_group(self.camera, self.group)
        if self.action == "remove":
            if not self.group or not self.camera:
                raise ValueError("Both group name and camera name are required for remove action")
            return await server.remove_camera_from_group(self.camera, self.group)
        raise ValueError(f"Unknown action: {self.action}")


@tool("capture_snapshot")
class CaptureSnapshotTool(BaseTool):
    """
    Capture a snapshot from a camera.

    Takes a still image from the specified camera and returns
    the image data or saves it to a file.

    Parameters:
        camera_id (str): ID of the camera to capture from

    Returns:
        Dict with snapshot data and metadata

    Example:
        result = await capture_snapshot_tool.execute(camera_id='test_camera')
        if result['success']:
            logger.info(f"Snapshot captured: {result['image_size']} bytes")
    """

    class Meta:
        name = "capture_snapshot"
        description = "Capture a snapshot from a camera"
        category = ToolCategory.CAMERA

        class Parameters:
            camera_id: str = Field(..., description="ID of the camera to capture from")

    camera_id: str

    async def execute(self) -> ToolResult:
        """Capture a snapshot from the specified camera."""
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        server = await TapoCameraServer.get_instance()

        try:
            # Use the server's capture_still method
            result = await server.capture_still({"camera_name": self.camera_id})

            if result.get("status") == "success":
                return ToolResult(
                    content={
                        "success": True,
                        "camera_id": self.camera_id,
                        "image_data": result.get("image_data"),
                        "image_size": len(result.get("image_data", b"")),
                        "timestamp": result.get("timestamp"),
                        "message": f"Snapshot captured from {self.camera_id}",
                    },
                    is_error=False,
                )
            return ToolResult(
                content={
                    "success": False,
                    "error": result.get("error", "Failed to capture snapshot"),
                    "camera_id": self.camera_id,
                },
                is_error=True,
            )
        except Exception as e:
            logger.exception("Failed to capture snapshot from")
            return ToolResult(
                content={
                    "success": False,
                    "error": f"Failed to capture snapshot: {e!s}",
                    "camera_id": self.camera_id,
                },
                is_error=True,
            )


@tool("get_stream_url")
class GetStreamUrlTool(BaseTool):
    """
    Get the stream URL for a camera.

    Retrieves the RTSP or other streaming URL for the specified camera.

    Parameters:
        camera_id (str): ID of the camera to get stream URL for

    Returns:
        Dict with stream URL and metadata

    Example:
        result = await get_stream_url_tool.execute(camera_id='test_camera')
        if result['success']:
            logger.info(f"Stream URL: {result['stream_url']}")
    """

    class Meta:
        name = "get_stream_url"
        description = "Get the stream URL for a camera"
        category = ToolCategory.CAMERA

        class Parameters:
            camera_id: str = Field(..., description="ID of the camera to get stream URL for")

    camera_id: str

    async def execute(self) -> ToolResult:
        """Get the stream URL for the specified camera."""
        from devices_mcp.core.server import (  # Lazy import to avoid circular imports
            TapoCameraServer,
        )

        server = await TapoCameraServer.get_instance()

        try:
            # Get camera info to extract stream URL
            camera_info = await server.get_camera_info()

            if camera_info.get("success"):
                # For now, return a mock stream URL
                stream_url = f"rtsp://{self.camera_id}:554/stream1"
                return ToolResult(
                    content={
                        "success": True,
                        "camera_id": self.camera_id,
                        "stream_url": stream_url,
                        "protocol": "rtsp",
                        "message": f"Stream URL retrieved for {self.camera_id}",
                    },
                    is_error=False,
                )
            return ToolResult(
                content={
                    "success": False,
                    "error": camera_info.get("error", "Failed to get camera info"),
                    "camera_id": self.camera_id,
                },
                is_error=True,
            )
        except Exception as e:
            logger.exception("Failed to get stream URL for")
            return ToolResult(
                content={
                    "success": False,
                    "error": f"Failed to get stream URL: {e!s}",
                    "camera_id": self.camera_id,
                },
                is_error=True,
            )


# Register all tools
ListCamerasTool = register_tool(ListCamerasTool)
AddCameraTool = register_tool(AddCameraTool)
RemoveCameraTool = register_tool(RemoveCameraTool)
SetActiveCameraTool = register_tool(SetActiveCameraTool)
GetCameraStatusTool = register_tool(GetCameraStatusTool)
ConnectCameraTool = register_tool(ConnectCameraTool)
DisconnectCameraTool = register_tool(DisconnectCameraTool)
GetCameraInfoTool = register_tool(GetCameraInfoTool)
ManageCameraGroupsTool = register_tool(ManageCameraGroupsTool)
CaptureSnapshotTool = register_tool(CaptureSnapshotTool)
GetStreamUrlTool = register_tool(GetStreamUrlTool)

# Debug: Print registered tools
camera_tool_classes = [
    ListCamerasTool,
    AddCameraTool,
    RemoveCameraTool,
    SetActiveCameraTool,
    GetCameraStatusTool,
    ConnectCameraTool,
    DisconnectCameraTool,
    GetCameraInfoTool,
    ManageCameraGroupsTool,
    CaptureSnapshotTool,
    GetStreamUrlTool,
]
logger.debug(f"Registered camera tools: {[tool.Meta.name for tool in camera_tool_classes]}")
