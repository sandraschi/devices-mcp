"""
HTTP Server for Ring MCP - Web API Access

This module provides an HTTP REST API server for the Ring MCP functionality,
allowing web applications and other HTTP clients to access Ring device controls.

The server runs alongside the stdio MCP server, providing dual transport support.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any

import structlog
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ring_mcp.core.exceptions import AuthenticationError, DeviceNotFoundError
from ring_mcp.core.ring_client_modern import RingClient

# Configure structured logging
logger = structlog.get_logger(__name__)

# Global Ring client instance (lazy initialization)
ring_client: RingClient | None = None
auth_credentials: dict[str, str] | None = None


def get_ring_client() -> RingClient:
    """Get or create the global Ring client instance."""
    global ring_client
    if ring_client is None:
        logger.info("Initializing Ring client for HTTP server")
        if auth_credentials:
            ring_client = RingClient(
                username=auth_credentials.get("username"), password=auth_credentials.get("password")
            )
            logger.info("Ring client initialized with provided credentials")
        else:
            ring_client = RingClient()
            logger.info("Ring client initialized without credentials")
    return ring_client


# Create FastAPI application
app = FastAPI(
    title="Ring MCP HTTP API",
    description="REST API for Ring MCP - Smart home security controls",
    version="1.0.3",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Add CORS middleware for web app access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:11110",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:11110",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Error handler for API exceptions
@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    return JSONResponse(
        status_code=401,
        content={
            "error": True,
            "message": "Authentication failed - please check your Ring credentials",
            "code": "AUTHENTICATION_ERROR",
        },
    )


@app.exception_handler(DeviceNotFoundError)
async def device_not_found_handler(request: Request, exc: DeviceNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": True,
            "message": f"Device not found: {exc!s}",
            "code": "DEVICE_NOT_FOUND",
        },
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    logger.exception("API Error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": True, "message": "Internal server error", "code": "INTERNAL_ERROR"},
    )


# API Routes
@app.post("/api/v1/auth/configure")
async def configure_auth(credentials: dict[str, str]):
    """Configure authentication credentials for Ring API."""
    global ring_client, auth_credentials

    username = credentials.get("username")
    password = credentials.get("password")

    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    try:
        # Store credentials
        auth_credentials = {"username": username, "password": password}

        # Reset client so it gets recreated with new credentials
        ring_client = None

        # Test the connection by creating a new client
        test_client = RingClient(username=username, password=password)

        # Try to authenticate (this will raise an exception if credentials are invalid)
        await test_client.get_devices(force_refresh=True)

        logger.info(f"Authentication configured successfully for user: {username}")

        return {
            "success": True,
            "message": "Authentication configured successfully",
            "user": username,
        }

    except AuthenticationError as e:
        # Clear stored credentials on auth failure
        auth_credentials = None
        ring_client = None
        logger.warning(f"Authentication failed for user {username}: {e!s}")
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e!s}")
    except Exception as e:
        # Clear stored credentials on any failure
        auth_credentials = None
        ring_client = None
        logger.exception("Failed to configure authentication:")
        raise HTTPException(status_code=500, detail=f"Failed to configure authentication: {e!s}")


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint for the Ring MCP server."""
    try:
        client = get_ring_client()
        # Try to get devices to test API connectivity
        devices = await client.get_devices(force_refresh=False)
        device_count = len(devices)

        return {
            "success": True,
            "message": f"Ring MCP server healthy - {device_count} devices accessible",
            "health_status": {
                "api_connected": True,
                "devices_accessible": device_count,
                "authentication_valid": True,
                "last_check": "2025-01-19T01:00:00Z",
            },
        }
    except AuthenticationError:
        return {
            "success": False,
            "message": "Ring authentication failed",
            "health_status": {
                "api_connected": False,
                "devices_accessible": 0,
                "authentication_valid": False,
                "last_check": "2025-01-19T01:00:00Z",
            },
        }
    except Exception as e:
        logger.exception("Health check failed", error=str(e))
        return {
            "success": False,
            "message": f"Health check failed: {e!s}",
            "health_status": {
                "api_connected": False,
                "devices_accessible": 0,
                "authentication_valid": False,
                "last_check": "2025-01-19T01:00:00Z",
            },
        }


@app.get("/api/v1/devices")
async def get_devices(force_refresh: bool = False):
    """Get all Ring devices."""
    try:
        client = get_ring_client()
        devices = await client.get_devices(force_refresh=force_refresh)

        return {"success": True, "devices": devices, "count": len(devices)}
    except Exception as e:
        logger.exception("Failed to get devices", error=str(e))
        raise


@app.get("/api/v1/devices/{device_id}")
async def get_device(device_id: str):
    """Get details for a specific device."""
    try:
        client = get_ring_client()
        device = await client.get_device(device_id)

        if not device:
            raise DeviceNotFoundError(f"Device {device_id} not found")

        return {"success": True, "device": device}
    except Exception as e:
        logger.exception("Failed to get device", device_id=device_id, error=str(e))
        raise


@app.get("/api/v1/devices/{device_id}/events")
async def get_device_events(device_id: str, limit: int = 10):
    """Get events for a specific device."""
    try:
        client = get_ring_client()
        events = await client.get_device_events(device_id, limit=limit)

        return {"success": True, "events": events, "count": len(events)}
    except Exception as e:
        logger.exception("Failed to get device events", device_id=device_id, error=str(e))
        raise


@app.get("/api/v1/devices/{device_id}/stream")
async def get_live_stream_url(device_id: str):
    """Get live stream URL for a camera device."""
    try:
        client = get_ring_client()
        stream_url = await client.get_live_stream_url(device_id)

        return {"success": True, "url": stream_url}
    except Exception as e:
        logger.exception("Failed to get stream URL", device_id=device_id, error=str(e))
        raise


@app.post("/api/v1/devices/{device_id}/arm")
async def set_arm_status(device_id: str, request: dict[str, Any]):
    """Arm or disarm a security device."""
    try:
        armed = request.get("status", False)
        if not isinstance(armed, bool):
            raise HTTPException(status_code=400, detail="Status must be a boolean")

        client = get_ring_client()
        result = await client.set_arm_status(device_id, armed)

        action = "armed" if armed else "disarmed"

        return {
            "success": result,
            "message": f"Device {device_id} {action} {'successfully' if result else 'failed'}",
            "operation": action,
            "timestamp": "2025-01-19T01:00:00Z",
            "device_id": device_id,
        }
    except Exception as e:
        logger.exception("Failed to set arm status", device_id=device_id, error=str(e))
        raise


@app.post("/api/v1/devices/{device_id}/chime")
async def trigger_doorbell_chime(device_id: str):
    """Trigger doorbell chime."""
    try:
        client = get_ring_client()
        result = await client.trigger_chime(device_id)

        return {
            "success": result,
            "message": f"Doorbell chime {'triggered successfully' if result else 'failed to trigger'}",
            "operation": "chime",
            "timestamp": "2025-01-19T01:00:00Z",
            "device_id": device_id,
        }
    except Exception as e:
        logger.exception("Failed to trigger chime", device_id=device_id, error=str(e))
        raise


@app.get("/api/v1/status")
async def get_system_status():
    """Get overall system status."""
    try:
        client = get_ring_client()
        devices = await client.get_devices(force_refresh=False)

        # Categorize devices
        doorbells = [d for d in devices if d.get("type") == "doorbell"]
        cameras = [d for d in devices if d.get("type") == "camera"]
        alarms = [d for d in devices if d.get("type") == "alarm"]

        return {
            "success": True,
            "status": {
                "total_devices": len(devices),
                "online_devices": len([d for d in devices if d.get("online")]),
                "doorbells": len(doorbells),
                "cameras": len(cameras),
                "alarms": len(alarms),
                "last_updated": "2025-01-19T01:00:00Z",
            },
        }
    except Exception as e:
        logger.exception("Failed to get system status", error=str(e))
        raise


def main():
    """Run the HTTP server."""
    # Configure logging
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Configure structlog for JSON logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Get server configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8123"))

    logger.info(f"Starting Ring MCP HTTP server on http://{host}:{port}")
    logger.info("API documentation available at: http://localhost:8123/docs")
    logger.info("Press Ctrl+C to stop")

    # Run the server
    uvicorn.run("ring_mcp.http_server:app", host=host, port=port, reload=False, log_level="info")


if __name__ == "__main__":
    main()
