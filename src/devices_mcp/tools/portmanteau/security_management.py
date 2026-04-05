"""
Security Management Portmanteau Tool

Consolidates all security-related operations into a single tool with action-based interface.
Now with REAL Nest Protect API integration (requires one-time OAuth setup).
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP

from devices_mcp.integrations.nest_client import (
    NestClient,
    get_nest_client,
)
from devices_mcp.tools.alarms.nest_protect_tool import NestProtectTool
from devices_mcp.tools.alarms.security_analysis_tool import SecurityAnalysisTool
from devices_mcp.utils.response_builders import (
    build_network_error_response,
)

logger = logging.getLogger(__name__)

# Global Nest client instance
_nest_client: NestClient | None = None


async def _handle_real_nest_action(
    client: NestClient,
    action: str,
    device_id: str | None = None,
) -> dict[str, Any]:
    """Handle Nest actions using real API."""
    import time

    if action == "nest_status":
        if device_id:
            device = await client.get_device(device_id)
            if device:
                return {
                    "success": True,
                    "operation": "status",
                    "devices": [device.to_dict()],
                    "total_devices": 1,
                    "online_devices": 1 if device.is_online else 0,
                    "timestamp": time.time(),
                }
            return {
                "success": False,
                "error": f"Device {device_id} not found",
                "timestamp": time.time(),
            }
        # Get all devices
        summary = await client.get_summary()
        return {
            "success": True,
            "operation": "status",
            **summary,
            "timestamp": time.time(),
        }

    if action == "nest_alerts":
        # Real API doesn't have historical alerts, return current status as "alerts"
        devices = await client.get_devices()
        alerts = []
        for d in devices:
            if d.smoke_status.value != "ok":
                alerts.append(
                    {
                        "device_id": d.device_id,
                        "device_name": d.name,
                        "type": "smoke",
                        "status": d.smoke_status.value,
                        "timestamp": time.time(),
                    }
                )
            if d.co_status.value != "ok":
                alerts.append(
                    {
                        "device_id": d.device_id,
                        "device_name": d.name,
                        "type": "co",
                        "status": d.co_status.value,
                        "timestamp": time.time(),
                    }
                )
            if not d.is_online:
                alerts.append(
                    {
                        "device_id": d.device_id,
                        "device_name": d.name,
                        "type": "offline",
                        "status": "offline",
                        "timestamp": time.time(),
                    }
                )
        return {
            "success": True,
            "operation": "alerts",
            "alerts": alerts,
            "total_alerts": len(alerts),
            "active_alerts": len(alerts),
            "timestamp": time.time(),
        }

    if action == "nest_battery":
        devices = await client.get_devices()
        battery_info = []
        for d in devices:
            battery_info.append(
                {
                    "device_id": d.device_id,
                    "name": d.name,
                    "battery_health": d.battery_health,
                    "needs_replacement": d.battery_health != "ok",
                }
            )
        needs_attention = [b for b in battery_info if b["needs_replacement"]]
        return {
            "success": True,
            "operation": "battery",
            "devices": battery_info,
            "total_devices": len(battery_info),
            "needs_attention": len(needs_attention),
            "timestamp": time.time(),
        }

    if action == "test_nest":
        # Can't trigger remote test via API (safety feature)
        return {
            "success": True,
            "operation": "test",
            "note": "Remote testing not supported by Nest API for safety reasons",
            "instruction": "Press the button on your Nest Protect to run a manual test",
            "timestamp": time.time(),
        }

    if action == "correlate_events":
        # Would need camera integration
        return {
            "success": True,
            "operation": "correlate",
            "note": "Event correlation requires Nest camera integration",
            "timestamp": time.time(),
        }

    return {"success": False, "error": f"Unknown action: {action}"}


SECURITY_ACTIONS = {
    # Nest OAuth setup
    "nest_oauth_start": "Start Nest OAuth flow - returns URL to visit",
    "nest_oauth_complete": "Complete OAuth with code from Google",
    "nest_oauth_status": "Check if Nest is authenticated",
    # Nest Protect operations (real API when authenticated, mock otherwise)
    "nest_status": "Get Nest Protect status",
    "nest_alerts": "Get Nest Protect alerts",
    "nest_battery": "Get Nest Protect battery status",
    "test_nest": "Test Nest Protect device",
    "correlate_events": "Correlate Nest camera events",
    # Security analysis
    "security_scan": "Perform security scan",
    "analyze_scene": "Analyze camera scene",
}


def register_security_management_tool(mcp: FastMCP) -> None:
    """Register the security management portmanteau tool."""

    @mcp.tool()
    async def security_management(
        action: Literal[
            "nest_status",
            "nest_alerts",
            "nest_battery",
            "test_nest",
            "correlate_events",
            "security_scan",
            "analyze_scene",
            "nest_oauth_start",
            "nest_oauth_complete",
            "nest_oauth_status",
        ],
        device_id: str | None = None,
        camera_name: str | None = None,
        hours: int = 24,
        alert_id: str | None = None,
        time_window_minutes: int = 5,
        threat_types: list[str] | None = None,
        save_images: bool = False,
        analysis_type: str | None = None,
        confidence_threshold: float = 0.5,
        # OAuth parameters
        oauth_code: str | None = None,
    ) -> dict[str, Any]:
        """
        Comprehensive security management portmanteau tool.

        PORTMANTEAU PATTERN RATIONALE:
        Instead of creating 7+ separate tools (one per operation), this tool consolidates related
        security operations into a single interface. Prevents tool explosion (7+ tools → 1 tool) while maintaining
        full functionality and improving discoverability. Follows FastMCP 3.1+ best practices.

        NEST PROTECT INTEGRATION:
        Uses real Google Nest API when authenticated. One-time OAuth setup required:
        1. Call nest_oauth_start → get URL
        2. Visit URL, login with Google, copy code
        3. Call nest_oauth_complete with oauth_code → done forever

        Args:
            action (Literal, required): The operation to perform. Must be one of: "nest_status", "nest_alerts",
                "nest_battery", "test_nest", "correlate_events", "security_scan", "analyze_scene",
                "nest_oauth_start", "nest_oauth_complete", "nest_oauth_status".
                - "nest_oauth_start": Start OAuth flow (returns Google URL to visit)
                - "nest_oauth_complete": Complete OAuth (requires: oauth_code)
                - "nest_oauth_status": Check if Nest is authenticated
                - "nest_status": Get Nest Protect status (optional: device_id)
                - "nest_alerts": Get Nest Protect alerts (optional: device_id, hours)
                - "nest_battery": Get Nest Protect battery status (optional: device_id)
                - "test_nest": Test Nest Protect device (optional: device_id)
                - "correlate_events": Correlate Nest camera events (optional: alert_id, time_window_minutes)
                - "security_scan": Perform security scan (requires: camera_name, threat_types)
                - "analyze_scene": Analyze camera scene (requires: camera_name, analysis_type)

            device_id (str | None): Device ID for Nest Protect operations. Used by: nest_status, nest_alerts,
                nest_battery, test_nest operations.

            camera_name (str | None): Camera name for security scan/analysis. Required for: security_scan,
                analyze_scene operations.

            hours (int): Hours to look back for alerts. Used by: nest_alerts operation. Default: 24

            alert_id (str | None): Alert ID for correlation. Used by: correlate_events operation.

            time_window_minutes (int): Time window for event correlation. Used by: correlate_events operation.
                Default: 5

            threat_types (list[str] | None): Threat types to detect. Required for: security_scan operation.
                Default: ["person", "package"]. Valid: "person", "package", "vehicle", "animal"

            save_images (bool): Save images from scan. Used by: security_scan, analyze_scene operations.
                Default: False

            analysis_type (str | None): Type of scene analysis. Required for: analyze_scene operation.
                Valid: "objects", "faces", "motion", "security"

            confidence_threshold (float): Confidence threshold for analysis. Used by: analyze_scene operation.
                Default: 0.5. Range: 0.0 to 1.0

            oauth_code (str | None): OAuth authorization code from Google. Required for: nest_oauth_complete.

        Returns:
            dict[str, Any]: Dictionary containing:
                - success (bool): Boolean indicating if operation succeeded
                - action (str): The action that was performed
                - data (dict): Operation-specific result data (status, alerts, threats, etc.)
                - error (str | None): Error message if success is False

        Examples:
            # Step 1: Start OAuth flow
            result = await security_management(action="nest_oauth_start")
            # Returns: {"oauth_url": "https://accounts.google.com/...", "instructions": [...]}

            # Step 2: After visiting URL and getting code
            result = await security_management(action="nest_oauth_complete", oauth_code="4/0ABC...")

            # Step 3: Now Nest operations use real API!
            result = await security_management(action="nest_status")

            # Check auth status
            result = await security_management(action="nest_oauth_status")

            # Security scan
            result = await security_management(action="security_scan", camera_name="Front Door", threat_types=["person", "package"])
        """
        global _nest_client

        try:
            if action not in SECURITY_ACTIONS:
                return {
                    "success": False,
                    "error": f"Invalid action '{action}'. Available: {list(SECURITY_ACTIONS.keys())}",
                }

            logger.info(f"Executing security management action: {action}")

            # ===== NEST OAUTH ACTIONS =====
            if action == "nest_oauth_start":
                oauth_url = NestClient.get_oauth_url()
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "oauth_url": oauth_url,
                        "instructions": [
                            "1. Visit the URL above in your browser",
                            "2. Sign in with the Google account linked to your Nest devices",
                            "3. Grant access when prompted",
                            "4. Copy the authorization code shown",
                            "5. Call: security_management('nest_oauth_complete', oauth_code='YOUR_CODE')",
                        ],
                        "note": "This is a one-time setup. Token will be cached for future use.",
                    },
                }

            if action == "nest_oauth_complete":
                if not oauth_code:
                    return {
                        "success": False,
                        "action": action,
                        "error": "oauth_code is required. Get it from the Google OAuth page.",
                    }

                # Create client and exchange code
                _nest_client = NestClient()
                success = await _nest_client.exchange_code(oauth_code)

                if success:
                    # Initialize with the new token
                    await _nest_client.initialize()
                    device_count = len(await _nest_client.get_devices())
                    return {
                        "success": True,
                        "action": action,
                        "data": {
                            "authenticated": True,
                            "devices_found": device_count,
                            "token_cached": True,
                            "message": f"Nest OAuth complete! Found {device_count} Nest Protect devices.",
                        },
                    }
                return {
                    "success": False,
                    "action": action,
                    "error": "Failed to exchange OAuth code. Make sure the code is correct and not expired.",
                }

            if action == "nest_oauth_status":
                # Try to get existing client or initialize from cache
                client = get_nest_client()
                if not client:
                    _nest_client = NestClient()
                    if await _nest_client.initialize():
                        client = _nest_client
                    else:
                        _nest_client = None

                if client and client.is_initialized:
                    devices = await client.get_devices()
                    return {
                        "success": True,
                        "action": action,
                        "data": {
                            "authenticated": True,
                            "devices_count": len(devices),
                            "devices": [d.name for d in devices],
                            "using_real_api": True,
                        },
                    }
                return {
                    "success": True,
                    "action": action,
                    "data": {
                        "authenticated": False,
                        "using_real_api": False,
                        "note": "Run nest_oauth_start to authenticate with Google Nest",
                    },
                }

            # ===== NEST PROTECT OPERATIONS =====
            if action in [
                "nest_status",
                "nest_alerts",
                "nest_battery",
                "test_nest",
                "correlate_events",
            ]:
                # Try real API first
                client = get_nest_client() or _nest_client
                if not client:
                    # Try to initialize from cached token
                    _nest_client = NestClient()
                    if await _nest_client.initialize():
                        client = _nest_client
                    else:
                        _nest_client = None

                if client and client.is_initialized:
                    # Use REAL Nest API
                    logger.info("Using real Nest API")
                    result = await _handle_real_nest_action(client, action, device_id)
                    result["using_real_api"] = True
                    return {"success": True, "action": action, "data": result}

                # Fall back to mock data
                logger.info("Nest not authenticated, using mock data")
                tool = NestProtectTool()
                operation_map = {
                    "nest_status": "status",
                    "nest_alerts": "alerts",
                    "nest_battery": "battery",
                    "test_nest": "test",
                    "correlate_events": "correlate",
                }
                # Mock tool only accepts operation, device_id, alert_type
                result = await tool.execute(
                    operation=operation_map[action],
                    device_id=device_id,
                )
                result["using_real_api"] = False
                result["note"] = "Using mock data. Run nest_oauth_start to use real Nest API."
                return {"success": True, "action": action, "data": result}

            # ===== SECURITY ANALYSIS =====
            if action in ["security_scan", "analyze_scene"]:
                tool = SecurityAnalysisTool()
                result = await tool.execute(
                    operation=action,
                    camera_name=camera_name,
                    threat_types=threat_types or ["person", "package"],
                    save_images=save_images,
                    analysis_type=analysis_type,
                    confidence_threshold=confidence_threshold,
                )
                return {"success": True, "action": action, "data": result}

            return {"success": False, "error": f"Action '{action}' not implemented"}

        except Exception as e:
            logger.exception(f"Error in security management action '{action}'")

            # Intelligent error analysis for security system issues
            error_str = str(e).lower()
            recovery_options = []

            if "oauth" in error_str or "authorization" in error_str or "token" in error_str:
                recovery_options = [
                    "Complete Nest OAuth setup with 'nest_oauth_helper.py'",
                    "Check OAuth credentials are properly configured",
                    "Refresh OAuth tokens if they have expired",
                    "Ensure Nest account has proper device permissions",
                ]
            elif "nest" in error_str and ("connection" in error_str or "network" in error_str):
                recovery_options = [
                    "Check Nest devices are online and connected to WiFi",
                    "Verify Nest account credentials and permissions",
                    "Ensure MCP server can reach Google Nest API endpoints",
                    "Check firewall allows HTTPS connections to Nest services",
                ]
            elif "device" in error_str and ("not found" in error_str or "offline" in error_str):
                recovery_options = [
                    f"Verify device_id '{device_id}' exists in your Nest account"
                    if device_id
                    else "Provide a valid device_id from your Nest account",
                    "Check device is powered on and connected to network",
                    "Ensure device is properly linked to your Nest account",
                    "Try refreshing device list from Nest app",
                ]
            elif "api" in error_str or "rate limit" in error_str:
                recovery_options = [
                    "Wait a few minutes before retrying (rate limit exceeded)",
                    "Check Google Nest API status and service health",
                    "Verify API credentials and permissions are correct",
                    "Reduce request frequency if hitting rate limits",
                ]
            else:
                recovery_options = [
                    "Check Nest device connectivity and account permissions",
                    "Verify OAuth setup is complete and tokens are valid",
                    "Try restarting the MCP server",
                    "Check Nest service status online",
                ]

            device_info = f" for device '{device_id}'" if device_id else ""
            return build_network_error_response(
                error=f"Nest security operation failed during {action}{device_info}",
                service="Google Nest API",
                recovery_options=recovery_options,
                suggestions=[
                    f"Try running security action '{action}' again after applying recovery steps",
                    "Complete OAuth setup if you haven't done so already",
                    "Check Nest app for device status and connectivity",
                ],
            )
