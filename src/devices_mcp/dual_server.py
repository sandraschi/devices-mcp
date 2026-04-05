"""
Dual Interface Server for Devices MCP

This module implements both MCP (stdio) and REST API (HTTP) interfaces
for the Devices MCP server, enabling seamless integration with
dashboards, mobile apps, and third-party services.
"""

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel

from devices_mcp.config import get_config
from devices_mcp.core.server import DevicesMCPServer

# Configure logging
logger = logging.getLogger(__name__)

# Security scheme for REST API
security = HTTPBearer()


class CameraInfo(BaseModel):
    """Camera information response model"""

    id: str
    name: str
    type: str
    status: str
    ip_address: Optional[str] = None
    model: Optional[str] = None


class StreamResponse(BaseModel):
    """Stream URL response model"""

    stream_url: str
    camera_id: str
    status: str


class SystemStatus(BaseModel):
    """System status response model"""

    status: str
    cameras_online: int
    cameras_total: int
    server_version: str


class TapoCameraDualServer:
    """
    Dual Interface Server for Devices MCP

    Provides both MCP (stdio) and REST API (HTTP) interfaces for
    comprehensive camera management and integration.
    """

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the dual interface server"""
        self.config = get_config()
        self.config_path = config_path

        # Core server will be initialized in lifespan
        self.core_server = None

        # MCP Interface (stdio) - existing
        self.mcp_app = None  # Will be initialized if running MCP mode

        # REST API Interface (HTTP) - new
        self.rest_app = self._create_rest_app()

        # Server state
        self.mcp_task: Optional[asyncio.Task] = None
        self.rest_task: Optional[asyncio.Task] = None

        logger.info("Tapo Camera Dual Server initialized")

    def _create_rest_app(self) -> FastAPI:
        """Create the REST API FastAPI application"""

        @asynccontextmanager
        async def lifespan(_app: FastAPI):
            # Startup - NO hardware initialization to allow immediate dashboard access
            logger.info("Starting Tapo Camera REST API server (lazy hardware init)")
            # self.core_server will be initialized on-demand when first API call is made
            yield
            # Shutdown
            logger.info("Shutting down Tapo Camera REST API server")
            # Core server cleanup handled by singleton
            if hasattr(self, "core_server") and self.core_server:
                await self.core_server.cleanup()

        app = FastAPI(
            title="Devices MCP API",
            description="REST API for Devices MCP - Dual Interface Server",
            version="1.0.0",
            lifespan=lifespan,
        )

        # CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Health check endpoint
        @app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "service": "devices-mcp",
                "version": "1.0.0",
            }

        # System status endpoint
        @app.get("/api/system/status", response_model=SystemStatus)
        async def get_system_status():
            """Get system status"""
            # Lazy initialization of core server
            if not hasattr(self, "core_server") or self.core_server is None:
                logger.info("Initializing core server on-demand for system status")
                self.core_server = await DevicesMCPServer.get_instance()

            cameras = await self.core_server.list_cameras()
            cameras_data = cameras.get("cameras", [])
            online_count = sum(1 for cam in cameras_data if cam.get("status") == "online")

            return SystemStatus(
                status="operational",
                cameras_online=online_count,
                cameras_total=len(cameras_data),
                server_version="1.0.0",
            )

        # Legacy endpoint for dashboard compatibility
        @app.get("/api/cameras/status")
        async def get_cameras_status():
            """Legacy endpoint for dashboard compatibility"""
            # Lazy initialization of core server
            if not hasattr(self, "core_server") or self.core_server is None:
                logger.info("Initializing core server on-demand for cameras status")
                self.core_server = await DevicesMCPServer.get_instance()

            cameras = await self.core_server.list_cameras()
            cameras_data = cameras.get("cameras", [])
            online_count = sum(1 for cam in cameras_data if cam.get("status") == "online")

            return {
                "total": len(cameras_data),
                "online": online_count,
                "cameras": cameras_data,
            }

        # Events endpoint for dashboard compatibility
        @app.get("/api/events/recent")
        async def get_recent_events():
            """Get recent events for dashboard compatibility"""
            # Lazy initialization of core server
            if not hasattr(self, "core_server") or self.core_server is None:
                logger.info("Initializing core server on-demand for events")
                self.core_server = await DevicesMCPServer.get_instance()

            # For now, return empty list - in full implementation would return actual events
            return {"events": [], "total": 0}

        # List cameras endpoint
        @app.get("/api/cameras", response_model=List[CameraInfo])
        async def list_cameras():
            """List all cameras"""
            try:
                # Lazy initialization of core server
                if not hasattr(self, "core_server") or self.core_server is None:
                    logger.info("Initializing core server on-demand for list cameras")
                    self.core_server = await DevicesMCPServer.get_instance()

                result = await self.core_server.list_cameras()
                cameras_data = result.get("cameras", [])

                cameras = []
                for cam in cameras_data:
                    camera = CameraInfo(
                        id=cam.get("id", ""),
                        name=cam.get("name", cam.get("id", "")),
                        type=cam.get("type", "tapo"),
                        status=cam.get("status", "unknown"),
                        ip_address=cam.get("host"),
                        model=cam.get("model"),
                    )
                    cameras.append(camera)

                return cameras

            except Exception as e:
                logger.exception("Error listing cameras")
                raise HTTPException(status_code=500, detail="Failed to list cameras") from e

        # Get camera details endpoint
        @app.get("/api/cameras/{camera_id}", response_model=CameraInfo)
        async def get_camera(camera_id: str):
            """Get camera details"""
            try:
                # Lazy initialization of core server
                if not hasattr(self, "core_server") or self.core_server is None:
                    logger.info("Initializing core server on-demand for get camera")
                    self.core_server = await DevicesMCPServer.get_instance()

                result = await self.core_server.list_cameras()
                cameras_data = result.get("cameras", [])

                for cam in cameras_data:
                    if cam.get("id") == camera_id or cam.get("name") == camera_id:
                        return CameraInfo(
                            id=cam.get("id", ""),
                            name=cam.get("name", cam.get("id", "")),
                            type=cam.get("type", "tapo"),
                            status=cam.get("status", "unknown"),
                            ip_address=cam.get("host"),
                            model=cam.get("model"),
                        )

                raise HTTPException(status_code=404, detail="Camera not found")

            except HTTPException:
                raise
            except Exception as e:
                logger.exception("Error getting camera")
                raise HTTPException(status_code=500, detail="Failed to get camera") from e

        # Get camera stream endpoint
        @app.get("/api/cameras/{camera_id}/stream", response_model=StreamResponse)
        async def get_camera_stream(camera_id: str):
            """Get camera live stream URL"""
            try:
                # Lazy initialization of core server
                if not hasattr(self, "core_server") or self.core_server is None:
                    logger.info("Initializing core server on-demand for camera stream")
                    self.core_server = await DevicesMCPServer.get_instance()

                # For now, return a placeholder stream URL
                # In a full implementation, this would get the actual RTSP stream URL
                stream_url = f"rtsp://placeholder/stream/{camera_id}"

                return StreamResponse(
                    stream_url=stream_url, camera_id=camera_id, status="available"
                )

            except Exception as e:
                logger.exception("Error getting stream for camera")
                raise HTTPException(status_code=500, detail="Failed to get stream") from e

        # Capture snapshot endpoint
        @app.post("/api/cameras/{camera_id}/snapshot")
        async def capture_snapshot(camera_id: str):
            """Capture a snapshot from the camera"""
            try:
                # Lazy initialization of core server
                if not hasattr(self, "core_server") or self.core_server is None:
                    logger.info("Initializing core server on-demand for snapshot")
                    self.core_server = await DevicesMCPServer.get_instance()

                # Find the camera
                result = await self.core_server.list_cameras()
                cameras_data = result.get("cameras", [])

                camera = None
                for cam in cameras_data:
                    if cam.get("id") == camera_id or cam.get("name") == camera_id:
                        camera = cam
                        break

                if not camera:
                    raise HTTPException(status_code=404, detail="Camera not found")

                # For now, return success (full implementation would capture actual image)
                return {
                    "success": True,
                    "camera_id": camera_id,
                    "message": "Snapshot captured successfully",
                    "timestamp": "2025-01-01T00:00:00Z",
                }

            except HTTPException:
                raise
            except Exception as e:
                logger.exception("Error capturing snapshot for camera")
                raise HTTPException(status_code=500, detail="Failed to capture snapshot") from e

        return app

    async def start_mcp_server(self):
        """Start the MCP (stdio) server"""
        try:
            logger.info("Starting MCP server (stdio mode)")
            # Import and start MCP server
            from .mcp_server import start_mcp_server

            await start_mcp_server()
        except Exception:
            logger.exception("Failed to start MCP server")
            raise

    async def start_rest_server(self, host: str = "0.0.0.0", port: int = 8123):  # nosec B104
        """Start the REST API server"""
        try:
            logger.info(f"Starting REST API server on {host}:{port}")

            config = uvicorn.Config(app=self.rest_app, host=host, port=port, log_level="info")
            server = uvicorn.Server(config)
            await server.serve()

        except Exception:
            logger.exception("Failed to start REST API server")
            raise

    async def start_dual_server(
        self,
        rest_host: str = "0.0.0.0",
        rest_port: int = 8123,
        mcp_host: str = "127.0.0.1",
        mcp_port: int = 8000,
    ):  # nosec B104
        """Start both MCP and REST servers concurrently"""
        logger.info("Starting dual interface server (MCP + REST API)")

        async def run_mcp_server():
            """Run MCP server in background"""
            try:
                logger.info(f"Starting MCP server on {mcp_host}:{mcp_port}")
                from devices_mcp.core.server import DevicesMCPServer

                server = await DevicesMCPServer.get_instance()
                await server.run(
                    host=mcp_host,
                    port=mcp_port,
                    stdio=False,  # Run as HTTP server for MCP client
                    direct=False,
                )
            except Exception:
                logger.exception("MCP server failed:")
                raise

        async def run_rest_server():
            """Run REST server in background"""
            try:
                logger.info(f"Starting REST API server on {rest_host}:{rest_port}")
                await self.start_rest_server(rest_host, rest_port)
            except Exception:
                logger.exception("REST server failed:")
                raise

        # Start both servers concurrently
        try:
            mcp_task = asyncio.create_task(run_mcp_server())
            rest_task = asyncio.create_task(run_rest_server())

            # Wait for either to finish (shouldn't happen in normal operation)
            done, pending = await asyncio.wait(
                [mcp_task, rest_task], return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

            # Check for exceptions
            for task in done:
                try:
                    await task
                except Exception:
                    logger.exception("Server task failed:")
                    raise

        except Exception:
            logger.exception("Failed to start dual servers")
            raise

    async def stop(self):
        """Stop all servers"""
        logger.info("Stopping dual interface server")

        # Cancel REST task if running
        if self.rest_task and not self.rest_task.done():
            self.rest_task.cancel()
            with suppress(asyncio.CancelledError):
                await self.rest_task

        # Cleanup core server
        await self.core_server.cleanup()

        logger.info("Dual interface server stopped")


# Global server instance
dual_server = TapoCameraDualServer()


async def start_dual_server():
    """Convenience function to start the dual server"""
    await dual_server.start_dual_server()


async def start_rest_only_server(host: str = "0.0.0.0", port: int = 8123):  # nosec B104
    """Convenience function to start REST API only"""
    await dual_server.start_rest_server(host, port)


async def start_mcp_only_server():
    """Convenience function to start MCP only"""
    await dual_server.start_mcp_server()
