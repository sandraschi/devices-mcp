"""API routes for the Devices MCP server."""

from typing import Any

from fastmcp import FastMCP

from ..camera.manager import CameraManager


class APIRouter:
    """API router for camera operations."""

    def __init__(self, mcp: FastMCP, camera_manager: CameraManager):
        self.mcp = mcp
        self.camera_manager = camera_manager
        self._register_routes()

    def _register_routes(self):
        """Register all API routes."""

        @self.mcp.tool()
        async def list_cameras() -> dict[str, Any]:
            """List all configured cameras with their current status and information.

            Retrieves a comprehensive list of all cameras registered in the system,
            including their connection status, configuration details, and availability.

            Returns:
                Dictionary containing:
                    - status: "success" or "error"
                    - cameras: List of camera dictionaries with details (only present on success)
                        - name: Camera name/identifier
                        - status: Connection status ("connected", "disconnected", "error")
                        - ip: Camera IP address
                        - model: Camera model information
                        - last_seen: Timestamp of last communication
                    - message: Error message string (only present on error)

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
                    result = await list_cameras()
                    if result['status'] == 'success':
                        for camera in result['cameras']:
                            print(f"Camera: {camera['name']} - {camera['status']}")
                    # Returns: {
                    #     'status': 'success',
                    #     'cameras': [
                    #         {'name': 'front_door', 'status': 'connected', 'ip': '192.168.1.100', ...},
                    #         {'name': 'backyard', 'status': 'disconnected', 'ip': '192.168.1.101', ...}
                    #     ]
                    # }

                Error handling:
                    result = await list_cameras()
                    if result['status'] == 'error':
                        print(f"Failed to list cameras: {result['message']}")
                    # Returns: {'status': 'error', 'message': 'Failed to list cameras: Connection timeout'}

            Raises:
                Exception: Propagated from camera manager operations (network issues, authentication failures)

            Notes:
                - Cameras are listed regardless of connection status
                - Status is determined by last known connection state
                - Network connectivity is tested during status checks
                - Results are cached briefly to improve performance

            See Also:
                - add_camera: For adding new cameras to the system
                - remove_camera: For removing cameras from the system
                - get_stream_url: For getting streaming URLs for specific cameras
            """
            try:
                cameras = await self.camera_manager.list_cameras()
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to list cameras: {e!s}",
                }
            else:
                return {"status": "success", "cameras": cameras}

        @self.mcp.tool()
        async def add_camera(
            name: str,
            camera_type: str,
            host: str | None = None,
            username: str | None = None,
            password: str | None = None,
            port: int | None = None,
            stream_type: str | None = None,
            verify_ssl: bool = True,
            timeout: int = 10,
        ) -> dict[str, Any]:
            """Add a new camera to the system with full configuration support.

            Registers and connects to a new camera device using the provided configuration
            parameters. The camera will be added to the system's camera registry and made
            available for streaming, recording, and control operations.

            Parameters:
                name: Camera name/identifier (required)
                    - Must be unique and alphanumeric with underscores only
                    - Used as the primary identifier for camera operations
                camera_type: Camera type string (required, e.g., "tapo", "webcam", "ring")
                    - Determines which camera driver to use
                    - Must match a supported camera type
                host: Camera IP address or hostname (required for most types)
                    - Network address where the camera is located
                    - Optional for local cameras like USB webcams
                username: Camera authentication username (required for authenticated cameras)
                    - Login credential for camera access
                    - May be optional for some camera types
                password: Camera authentication password (required for authenticated cameras)
                    - Password credential for camera access
                    - Stored securely in the configuration
                port: Camera port number (optional, defaults vary by type)
                    - Network port for camera communication
                    - Typically 443 for HTTPS, 554 for RTSP
                stream_type: Stream type ("rtsp", "rtmp", "hls") (optional)
                    - Preferred streaming protocol
                    - Defaults based on camera capabilities
                verify_ssl: SSL certificate verification (optional, default: True)
                    - Whether to verify SSL certificates
                    - Should be False only for self-signed certificates
                timeout: Connection timeout in seconds (optional, default: 10)
                    - Maximum time to wait for camera connection
                    - Increase for slower networks

            Returns:
                Dictionary containing:
                    - status: "success" or "error"
                    - message: Success confirmation or error description

            Usage:
                Use this tool to register new cameras in the system. Ensure all required
                authentication credentials are provided and the camera is accessible on
                the network before adding.

                Common scenarios:
                - Initial system setup with multiple cameras
                - Adding replacement cameras
                - Expanding camera coverage
                - Testing new camera configurations

            Examples:
                Add a Tapo camera:
                    result = await add_camera(
                        name='living_room',
                        camera_type='tapo',
                        host='192.168.1.100',
                        username='admin',
                        password='camera_password',
                        port=443,
                        verify_ssl=True
                    )
                    if result['status'] == 'success':
                        print("Camera added successfully")
                    # Returns: {'status': 'success', 'message': 'Camera living_room added successfully'}

                Add a USB webcam:
                    result = await add_camera(
                        name='webcam1',
                        camera_type='webcam'
                        # host, username, password not needed for local webcam
                    )
                    # Returns: {'status': 'success', 'message': 'Camera webcam1 added successfully'}

                Error handling - missing required field:
                    result = await add_camera(
                        name='',  # Empty name
                        camera_type='tapo',
                        host='192.168.1.100'
                    )
                    # Returns: {'status': 'error', 'message': 'Camera name is required'}

                Error handling - connection failure:
                    result = await add_camera(
                        name='unreachable_cam',
                        camera_type='tapo',
                        host='192.168.1.999',  # Non-existent IP
                        username='admin',
                        password='password'
                    )
                    # Returns: {'status': 'error', 'message': 'Failed to add camera unreachable_cam'}

            Raises:
                Exception: Propagated from camera manager operations (network connectivity, authentication failures)

            Notes:
                - Camera names must be unique within the system
                - Authentication credentials are stored securely
                - Camera connectivity is verified during addition
                - Failed additions don't leave partial configurations
                - Some camera types require additional setup steps

            See Also:
                - list_cameras: To verify camera was added successfully
                - remove_camera: To remove cameras from the system
                - get_stream_url: To get streaming URLs for the added camera
            """
            try:
                if not name:
                    return {"status": "error", "message": "Camera name is required"}

                # Construct camera configuration from parameters
                camera_config = {
                    "name": name,
                    "type": camera_type,
                    "host": host,
                    "username": username,
                    "password": password,
                    "port": port,
                    "stream_type": stream_type,
                    "verify_ssl": verify_ssl,
                    "timeout": timeout,
                }

                # Remove None values to avoid overriding defaults
                camera_config = {k: v for k, v in camera_config.items() if v is not None}

                success = await self.camera_manager.add_camera(camera_config)
            except Exception as e:
                return {"status": "error", "message": f"Failed to add camera: {e!s}"}
            else:
                if success:
                    return {
                        "status": "success",
                        "message": f"Camera {name} added successfully",
                    }
                return {
                    "status": "error",
                    "message": f"Failed to add camera {name}",
                }

        @self.mcp.tool()
        async def remove_camera(name: str) -> dict[str, Any]:
            """Remove a camera from the system and clean up associated resources.

            Disconnects and unregisters a camera from the system, stopping all active
            streams, recordings, and monitoring operations for that camera. All associated
            resources are properly cleaned up and the camera is removed from the registry.

            Parameters:
                name: Camera name/identifier to remove (required)
                    - Must match an existing camera name exactly
                    - Case-sensitive matching

            Returns:
                Dictionary containing:
                    - status: "success" or "error"
                    - message: Success confirmation or error description

            Usage:
                Use this tool to permanently remove cameras from the system. This action
                cannot be undone and will stop all operations for the specified camera.
                Ensure the camera is no longer needed before removal.

                Common scenarios:
                - Removing faulty or replaced cameras
                - System cleanup and reorganization
                - Decommissioning cameras from service
                - Correcting configuration mistakes

            Examples:
                Remove a camera successfully:
                    result = await remove_camera('living_room')
                    if result['status'] == 'success':
                        print("Camera removed successfully")
                    # Returns: {'status': 'success', 'message': 'Camera living_room removed successfully'}

                Error handling - camera not found:
                    result = await remove_camera('nonexistent_camera')
                    if result['status'] == 'error':
                        print(f"Removal failed: {result['message']}")
                    # Returns: {'status': 'error', 'message': 'Failed to remove camera nonexistent_camera'}

                Error handling - empty name parameter:
                    result = await remove_camera('')
                    # Returns: {'status': 'error', 'message': 'Camera name is required'}

                Remove multiple cameras (sequential calls):
                    cameras_to_remove = ['old_cam1', 'old_cam2', 'old_cam3']
                    for cam_name in cameras_to_remove:
                        result = await remove_camera(cam_name)
                        if result['status'] == 'success':
                            print(f"Removed {cam_name}")
                        else:
                            print(f"Failed to remove {cam_name}: {result['message']}")

            Raises:
                Exception: Propagated from camera manager operations (disconnect failures, cleanup errors)

            Notes:
                - Removal is permanent and cannot be undone
                - Active streams and recordings are forcefully stopped
                - Camera resources are properly cleaned up
                - Configuration is updated immediately
                - Related motion detection and alerts are disabled
                - Storage space may be freed up after removal

            See Also:
                - list_cameras: To see available cameras before removal
                - add_camera: To add cameras back to the system
                - get_stream_url: Will no longer work for removed cameras
            """
            try:
                if not name:
                    return {"status": "error", "message": "Camera name is required"}

                success = await self.camera_manager.remove_camera(name)
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to remove camera: {e!s}",
                }
            else:
                if success:
                    return {
                        "status": "success",
                        "message": f"Camera {name} removed successfully",
                    }
                return {
                    "status": "error",
                    "message": f"Failed to remove camera {name}",
                }

        @self.mcp.tool()
        async def capture_still(camera: str, save_path: str | None = None) -> dict[str, Any]:
            """Capture a still image from a specified camera.

            Takes a snapshot from the specified camera and either returns the image data
            directly or saves it to a specified file path. This operation provides immediate
            visual verification of camera functionality and current scene.

            Parameters:
                camera: Camera name/identifier to capture from (required)
                    - Must match an existing camera name exactly
                    - Camera must be connected and operational
                save_path: Optional file path to save the image (optional)
                    - If provided, image is saved to this path and path is returned
                    - If not provided, image data is returned directly
                    - Supports common image formats (.jpg, .png, .bmp)

            Returns:
                Dictionary containing:
                    - status: "success" or "error"
                    - camera: Camera name that was used for capture
                    - image: Image data or file path (only present on success)
                        - PIL Image object if save_path not provided
                        - File path string if save_path was provided
                    - message: Error description (only present on error)

            Usage:
                Use this tool to capture still images for monitoring, verification, or
                archival purposes. Ideal for checking camera positioning, lighting conditions,
                or documenting specific moments/events.

                Common scenarios:
                - Camera setup and positioning verification
                - Security monitoring and incident documentation
                - Automated snapshot scheduling
                - Quality assurance and testing
                - Scene documentation before/after changes

            Examples:
                Capture and return image data:
                    result = await capture_still('front_door')
                    if result['status'] == 'success':
                        image = result['image']  # PIL Image object
                        print(f"Captured image from {result['camera']}")
                    # Returns: {'status': 'success', 'camera': 'front_door', 'image': <PIL.Image>}

                Capture and save to file:
                    result = await capture_still('living_room', '/photos/security/snapshot.jpg')
                    if result['status'] == 'success':
                        print(f"Image saved to {result['image']}")
                    # Returns: {
                    #     'status': 'success',
                    #     'camera': 'living_room',
                    #     'image': '/photos/security/snapshot.jpg'
                    # }

                Error handling - camera not found:
                    result = await capture_still('nonexistent')
                    if result['status'] == 'error':
                        print(f"Capture failed: {result['message']}")
                    # Returns: {'status': 'error', 'camera': 'nonexistent', 'message': 'Camera not found: nonexistent'}

                Error handling - empty camera parameter:
                    result = await capture_still('')
                    # Returns: {'status': 'error', 'message': 'Camera name is required'}

                Error handling - camera connection issues:
                    result = await capture_still('disconnected_cam')
                    # Returns: {
                    #     'status': 'error',
                    #     'camera': 'disconnected_cam',
                    #     'message': 'Connection failed: camera offline'
                    # }

            Raises:
                Exception: Propagated from camera operations (connection failures, hardware issues, file system errors)

            Notes:
                - Camera must be connected and operational
                - Image capture may take several seconds depending on camera type
                - Large images may consume significant memory when not saving to file
                - File paths are resolved relative to the working directory
                - Existing files at save_path will be overwritten
                - Image format is determined by file extension or defaults to JPEG

            See Also:
                - list_cameras: To verify camera availability before capture
                - get_stream_url: For continuous video streaming instead of snapshots
                - add_camera: To ensure cameras are properly configured
            """
            try:
                if not camera:
                    return {"status": "error", "message": "Camera name is required"}

                return await self.camera_manager.capture_still(camera, save_path)

            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to capture image: {e!s}",
                }

        @self.mcp.tool()
        async def get_stream_url(camera: str) -> dict[str, Any]:
            """Get the streaming URL for a specified camera.

            Retrieves the appropriate streaming endpoint URL for the specified camera,
            allowing access to live video feeds. The URL format depends on the camera
            type and configured streaming protocol (RTSP, RTMP, HLS, etc.).

            Parameters:
                camera: Camera name/identifier to get stream URL for (required)
                    - Must match an existing camera name exactly
                    - Camera must be connected and configured for streaming

            Returns:
                Dictionary containing:
                    - status: "success" or "error"
                    - camera: Camera name that was queried
                    - stream_url: Streaming URL string (only present on success)
                        - Complete URL including protocol, host, port, and path
                        - Format depends on camera type and stream configuration
                        - May include authentication parameters if required
                    - message: Error description (only present on error)

            Usage:
                Use this tool to obtain streaming URLs for video playback, monitoring,
                or integration with external systems. Essential for setting up video
                feeds in dashboards, monitoring applications, or automated systems.

                Common scenarios:
                - Setting up video monitoring dashboards
                - Integrating with video management systems
                - Automated recording and analysis pipelines
                - Live streaming to web interfaces
                - Third-party application integration

            Examples:
                Get stream URL successfully:
                    result = await get_stream_url('front_door')
                    if result['status'] == 'success':
                        stream_url = result['stream_url']
                        print(f"Stream URL: {stream_url}")
                    # Returns: {
                    #     'status': 'success',
                    #     'camera': 'front_door',
                    #     'stream_url': 'rtsp://192.168.1.100:554/stream1'
                    # }

                Error handling - camera not found:
                    result = await get_stream_url('nonexistent')
                    if result['status'] == 'error':
                        print(f"Stream URL retrieval failed: {result['message']}")
                    # Returns: {
                    #     'status': 'error',
                    #     'camera': 'nonexistent',
                    #     'message': 'Camera nonexistent not found'
                    # }

                Error handling - empty camera parameter:
                    result = await get_stream_url('')
                    # Returns: {'status': 'error', 'message': 'Camera name is required'}

                Error handling - camera not streaming:
                    result = await get_stream_url('offline_cam')
                    # Returns: {
                    #     'status': 'error',
                    #     'camera': 'offline_cam',
                    #     'message': 'Stream URL not available'
                    # }

                Integration example - use with video player:
                    result = await get_stream_url('security_cam')
                    if result['status'] == 'success':
                        # Use stream_url with video player library
                        player = VideoPlayer(result['stream_url'])
                        player.start()
                        print(f"Started streaming from {result['camera']}")

            Raises:
                Exception: Propagated from camera operations (connection failures, authentication errors, protocol issues)

            Notes:
                - Camera must be connected and operational
                - Stream URLs may include authentication credentials
                - URL format varies by camera type and protocol
                - Some cameras require active connection to generate URLs
                - URLs may have expiration times or session limitations
                - Network connectivity is required for streaming
                - Firewall rules may need to allow streaming ports

            See Also:
                - list_cameras: To verify camera availability before getting stream URL
                - capture_still: For single image capture instead of streaming
                - add_camera: To ensure cameras are properly configured for streaming
            """
            try:
                if not camera:
                    return {"status": "error", "message": "Camera name is required"}

                camera_obj = await self.camera_manager.get_camera(camera)
                if not camera_obj:
                    return {"status": "error", "message": f"Camera {camera} not found"}

                stream_url = await camera_obj.get_stream_url()
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to get stream URL: {e!s}",
                }
            else:
                if not stream_url:
                    return {"status": "error", "message": "Stream URL not available"}

                return {"status": "success", "camera": camera, "stream_url": stream_url}


def setup_api_routes(server) -> APIRouter:
    """Set up API routes for the server."""
    return APIRouter(server.mcp, server.camera_manager)
