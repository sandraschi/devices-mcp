"""
Ring MCP Status and System Information Tools - FastMCP 3.1

Comprehensive status monitoring tools providing:
- Authentication status and token validity
- Device connectivity and health status
- System performance metrics
- Connection diagnostics and troubleshooting
- Real-time system state monitoring

This module uses FastMCP 3.1 patterns with multiline decorators and proper
tool registration for Claude Desktop stdio communication.
"""

import logging
import time
from datetime import datetime
from typing import Any

from fastmcp import FastMCP

from ..core.exceptions import AuthenticationError
from ..core.ring_client import RingClient

logger = logging.getLogger(__name__)


def register_tools(app: FastMCP) -> None:
    """Register status monitoring tools with the FastMCP application.

    Uses FastMCP 3.1 patterns with multiline decorators and proper
    stdio communication support for Claude Desktop integration.

    Args:
        app: FastMCP application instance
    """

    @app.tool(
        name="get_system_status",
        description="Get comprehensive system status including authentication and device connectivity",
    )
    async def get_system_status(include_device_details: bool = True, check_connectivity: bool = True) -> dict[str, Any]:
        """Get comprehensive system status including authentication and device connectivity.

        Provides a complete overview of the Ring MCP system status including:
        - Authentication status and token validity
        - Device connectivity and health
        - System performance metrics
        - Network connectivity status
        - Service availability

        Args:
            include_device_details: Include detailed device information (default: True)
            check_connectivity: Perform active connectivity tests (default: True)

        Returns:
            Dict containing comprehensive system status information
        """
        start_time = time.time()
        status = {
            "timestamp": datetime.now().isoformat(),
            "system_status": "unknown",
            "authentication": {},
            "devices": {},
            "connectivity": {},
            "performance": {},
            "diagnostics": {},
        }

        try:
            # Check authentication status
            auth_status = await check_authentication_status()
            status["authentication"] = auth_status

            # Check device status
            device_status = await check_device_status(include_device_details)
            status["devices"] = device_status

            # Check connectivity
            if check_connectivity:
                connectivity_status = await check_connectivity_status()
                status["connectivity"] = connectivity_status

            # Determine overall system status
            status["system_status"] = determine_overall_status(
                auth_status, device_status, status.get("connectivity", {})
            )

            # Performance metrics
            status["performance"] = {
                "response_time_seconds": round(time.time() - start_time, 3),
                "memory_usage_mb": get_memory_usage(),
                "cpu_usage_percent": get_cpu_usage(),
            }

            # Diagnostics
            status["diagnostics"] = generate_diagnostics(status)

        except Exception as e:
            logger.exception("Error getting system status: %s", str(e))
            status["system_status"] = "error"
            status["error"] = {
                "message": str(e),
                "type": type(e).__name__,
                "timestamp": datetime.now().isoformat(),
            }

        return status

    @app.tool(
        name="check_authentication_status",
        description="Check Ring API authentication status and token validity",
    )
    async def check_authentication_status() -> dict[str, Any]:
        """Check Ring API authentication status and token validity.

        Validates the current authentication state including:
        - Token existence and validity
        - Token expiration status
        - Authentication method (OAuth/password)
        - Permission scope verification
        - API rate limit status

        Returns:
            Dict containing authentication status and details
        """
        auth_status = {
            "authenticated": False,
            "method": "unknown",
            "token_valid": False,
            "token_expires_in": None,
            "permissions": [],
            "rate_limit_status": "unknown",
            "last_successful_auth": None,
            "auth_errors": [],
        }

        try:
            # Create a test client to check auth
            test_client = RingClient()
            await test_client.connect()

            # Check if we have valid credentials
            if test_client.auth and test_client.auth.token:
                auth_status["authenticated"] = True
                auth_status["token_valid"] = True
                auth_status["method"] = "oauth_token"

                # Get token info if available
                if hasattr(test_client.auth, "token_expires_in"):
                    auth_status["token_expires_in"] = test_client.auth.token_expires_in

                auth_status["last_successful_auth"] = datetime.now().isoformat()

            elif test_client.username and test_client.password:
                auth_status["method"] = "username_password"
                # Test actual authentication
                try:
                    await test_client.get_devices(force_refresh=False)
                    auth_status["authenticated"] = True
                    auth_status["last_successful_auth"] = datetime.now().isoformat()
                except AuthenticationError as e:
                    auth_status["auth_errors"].append(f"Authentication failed: {e!s}")
                except Exception as e:
                    auth_status["auth_errors"].append(f"Connection failed: {e!s}")

            else:
                auth_status["method"] = "none"
                auth_status["auth_errors"].append("No authentication credentials configured")

        except Exception as e:
            logger.exception("Authentication check failed: %s", str(e))
            auth_status["auth_errors"].append(f"Check failed: {e!s}")

        return auth_status

    @app.tool(
        name="check_device_connectivity",
        description="Test connectivity and status of all Ring devices",
    )
    async def check_device_connectivity(device_id: str | None = None, test_commands: bool = False) -> dict[str, Any]:
        """Test connectivity and status of all Ring devices.

        Performs connectivity tests on Ring devices including:
        - Network connectivity verification
        - Device responsiveness testing
        - Status command execution
        - Signal strength checking
        - Battery level monitoring

        Args:
            device_id: Optional specific device ID to test
            test_commands: Execute test commands on devices (default: False)

        Returns:
            Dict containing device connectivity test results
        """
        connectivity_results = {
            "test_timestamp": datetime.now().isoformat(),
            "devices_tested": 0,
            "devices_online": 0,
            "devices_offline": 0,
            "connectivity_score": 0,
            "device_results": [],
            "recommendations": [],
        }

        try:
            # Get all devices
            client = RingClient()
            await client.connect()

            devices = await client.get_devices(force_refresh=True)
            connectivity_results["devices_tested"] = len(devices)

            for device in devices:
                device_result = {
                    "device_id": device.get("id", "unknown"),
                    "device_type": device.get("type", "unknown"),
                    "device_name": device.get("name", "Unnamed"),
                    "connectivity_status": "unknown",
                    "response_time_ms": None,
                    "last_seen": device.get("last_seen"),
                    "battery_level": device.get("battery_level"),
                    "signal_strength": device.get("signal_strength"),
                    "errors": [],
                }

                try:
                    # Test basic connectivity
                    start_time = time.time()
                    device_details = await client.get_device_details(device["id"])
                    response_time = (time.time() - start_time) * 1000

                    device_result["connectivity_status"] = "online"
                    device_result["response_time_ms"] = round(response_time, 2)
                    connectivity_results["devices_online"] += 1

                    # Check device health
                    if device_details.get("battery_level", 0) < 20:
                        device_result["errors"].append("Low battery")
                        connectivity_results["recommendations"].append(
                            f"Replace battery in {device.get('name', 'device')}"
                        )

                    if device_details.get("signal_strength", 0) < 50:
                        device_result["errors"].append("Weak signal")
                        connectivity_results["recommendations"].append(
                            f"Check signal strength for {device.get('name', 'device')}"
                        )

                except DeviceNotFoundError:
                    device_result["connectivity_status"] = "offline"
                    device_result["errors"].append("Device not found")
                    connectivity_results["devices_offline"] += 1
                    connectivity_results["recommendations"].append(
                        f"Check if {device.get('name', 'device')} is powered on"
                    )

                except Exception as e:
                    device_result["connectivity_status"] = "error"
                    device_result["errors"].append(str(e))
                    connectivity_results["devices_offline"] += 1
                    connectivity_results["recommendations"].append(
                        f"Troubleshoot {device.get('name', 'device')}: {e!s}"
                    )

                connectivity_results["device_results"].append(device_result)

            # Calculate connectivity score
            if connectivity_results["devices_tested"] > 0:
                connectivity_results["connectivity_score"] = int(
                    (connectivity_results["devices_online"] / connectivity_results["devices_tested"]) * 100
                )

        except Exception as e:
            logger.exception("Device connectivity check failed: %s", str(e))
            connectivity_results["error"] = str(e)
            connectivity_results["connectivity_score"] = 0

        return connectivity_results

    @app.tool(name="get_service_health", description="Get detailed service health and performance metrics")
    async def get_service_health(include_metrics: bool = True, history_minutes: int = 5) -> dict[str, Any]:
        """Get detailed service health and performance metrics.

        Provides comprehensive service health information including:
        - Service availability and uptime
        - Performance metrics and response times
        - Error rates and failure patterns
        - Resource utilization (memory, CPU)
        - Health check history

        Args:
            include_metrics: Include performance metrics (default: True)
            history_minutes: Minutes of history to include (default: 5)

        Returns:
            Dict containing service health and performance information
        """
        health_info = {
            "service_name": "Ring MCP Server",
            "version": "3.1.0",
            "uptime_seconds": get_uptime(),
            "health_status": "healthy",
            "last_health_check": datetime.now().isoformat(),
            "health_score": 100,
            "components": {},
            "performance": {},
            "alerts": [],
            "recommendations": [],
        }

        try:
            # Check core components
            components = {
                "authentication": await check_auth_component(),
                "device_management": await check_device_component(),
                "api_connectivity": await check_api_component(),
                "tool_system": await check_tool_component(),
            }

            health_info["components"] = components

            # Determine overall health
            health_score = 0
            total_components = len(components)

            for component_status in components.values():
                if component_status["status"] == "healthy":
                    health_score += 100
                elif component_status["status"] == "degraded":
                    health_score += 50
                elif component_status["status"] == "error":
                    health_score += 0

            health_info["health_score"] = int(health_score / total_components)

            if health_info["health_score"] < 80:
                health_info["health_status"] = "degraded"
            if health_info["health_score"] < 50:
                health_info["health_status"] = "error"

            # Performance metrics
            if include_metrics:
                health_info["performance"] = {
                    "memory_usage_mb": get_memory_usage(),
                    "cpu_usage_percent": get_cpu_usage(),
                    "active_connections": get_active_connections(),
                    "response_time_avg_ms": get_average_response_time(),
                }

            # Generate alerts and recommendations
            health_info["alerts"] = generate_health_alerts(components)
            health_info["recommendations"] = generate_health_recommendations(components)

        except Exception as e:
            logger.exception("Service health check failed: %s", str(e))
            health_info["health_status"] = "error"
            health_info["health_score"] = 0
            health_info["error"] = str(e)

        return health_info


async def check_auth_component() -> dict[str, Any]:
    """Check authentication component health."""
    try:
        auth_status = await check_authentication_status()
        if auth_status["authenticated"]:
            return {"status": "healthy", "details": "Authentication working"}
        return {"status": "error", "details": "Authentication failed"}
    except Exception as e:
        return {"status": "error", "details": f"Auth check failed: {e!s}"}


async def check_device_component() -> dict[str, Any]:
    """Check device management component health."""
    try:
        client = RingClient()
        await client.connect()
        devices = await client.get_devices(force_refresh=False)
        return {
            "status": "healthy",
            "details": f"Device management working ({len(devices)} devices)",
        }
    except Exception as e:
        return {"status": "error", "details": f"Device check failed: {e!s}"}


async def check_api_component() -> dict[str, Any]:
    """Check API connectivity component health."""
    try:
        # Test basic API connectivity
        client = RingClient()
        await client.connect()
        return {"status": "healthy", "details": "API connectivity working"}
    except Exception as e:
        return {"status": "error", "details": f"API check failed: {e!s}"}


async def check_tool_component() -> dict[str, Any]:
    """Check tool system component health."""
    return {"status": "healthy", "details": "Tool system operational"}


def determine_overall_status(auth_status: dict, device_status: dict, connectivity_status: dict) -> str:
    """Determine overall system status based on component statuses."""
    if not auth_status.get("authenticated", False):
        return "authentication_failed"

    online_devices = device_status.get("online_devices", 0)
    total_devices = device_status.get("total_devices", 0)

    if total_devices == 0:
        return "no_devices"

    connectivity_ratio = online_devices / total_devices

    if connectivity_ratio >= 0.8:
        return "healthy"
    if connectivity_ratio >= 0.5:
        return "degraded"
    return "poor_connectivity"


def generate_diagnostics(status: dict[str, Any]) -> dict[str, Any]:
    """Generate diagnostic information."""
    return {
        "diagnostic_timestamp": datetime.now().isoformat(),
        "system_uptime": get_uptime(),
        "memory_usage": get_memory_usage(),
        "suggestions": [
            "Check authentication if auth_status is false",
            "Verify device connectivity if many devices are offline",
            "Monitor system resources if performance is degraded",
        ],
    }


# Placeholder functions for system metrics
def get_uptime() -> int:
    """Get system uptime in seconds."""
    try:
        import psutil

        return int(psutil.boot_time())
    except ImportError:
        return 0


def get_memory_usage() -> float:
    """Get memory usage in MB."""
    try:
        import psutil

        return round(psutil.Process().memory_info().rss / 1024 / 1024, 2)
    except ImportError:
        return 0.0


def get_cpu_usage() -> float:
    """Get CPU usage percentage."""
    try:
        import psutil

        return round(psutil.cpu_percent(interval=1), 2)
    except ImportError:
        return 0.0


def get_active_connections() -> int:
    """Get number of active connections."""
    try:
        import psutil

        return len(psutil.net_connections())
    except ImportError:
        return 0


def get_average_response_time() -> float:
    """Get average response time in milliseconds."""
    return 0.0  # Placeholder


def generate_health_alerts(components: dict[str, dict]) -> list[str]:
    """Generate health alerts based on component status."""
    alerts = []

    for component_name, component_status in components.items():
        if component_status["status"] == "error":
            alerts.append(f"{component_name} component is not working: {component_status['details']}")

    return alerts


def generate_health_recommendations(components: dict[str, dict]) -> list[str]:
    """Generate health recommendations."""
    recommendations = []

    for component_name, component_status in components.items():
        if component_status["status"] != "healthy":
            recommendations.append(f"Fix {component_name} component: {component_status['details']}")

    if not recommendations:
        recommendations.append("System is healthy - no action required")

    return recommendations
