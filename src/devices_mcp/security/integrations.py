"""
Security System Integrations for Tapo Camera Dashboard

This module provides integration clients for various security MCP servers
to create a unified home security monitoring platform.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class SecurityDevice:
    """Unified security device representation"""

    id: str
    name: str
    type: str  # 'smoke_detector', 'co_detector', 'camera', 'doorbell'
    status: str  # 'online', 'offline', 'alert'
    battery_level: Optional[int] = None
    last_seen: Optional[datetime] = None
    location: Optional[str] = None
    alerts: List[Dict] = None

    def __post_init__(self):
        if self.alerts is None:
            self.alerts = []


@dataclass
class SecurityAlert:
    """Unified security alert representation"""

    id: str
    device_id: str
    device_name: str
    alert_type: str  # 'smoke', 'co', 'motion', 'doorbell'
    severity: str  # 'critical', 'warning', 'info'
    message: str
    timestamp: datetime
    resolved: bool = False


class NestProtectClient:
    """
    REST API client for Nest Protect MCP server integration

    Connects to the Nest Protect MCP server's REST API to fetch
    device status, alerts, and sensor data.
    """

    def __init__(self, base_url: str = "http://localhost:8123", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        """Initialize HTTP session"""
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self.timeout)

    async def disconnect(self):
        """Close HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None

    async def _get(self, endpoint: str) -> Dict:
        """Make GET request to Nest Protect API"""
        if not self._session:
            await self.connect()

        url = f"{self.base_url}{endpoint}"
        try:
            async with self._session.get(url) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError:
            logger.exception("Nest Protect API error")
            return {}
        except json.JSONDecodeError:
            logger.exception("Invalid JSON response from Nest Protect")
            return {}

    async def get_devices(self) -> List[SecurityDevice]:
        """Fetch all Nest Protect devices"""
        data = await self._get("/api/devices")
        devices = []

        for device_data in data.get("devices", []):
            # Convert Nest Protect device format to unified format
            device = SecurityDevice(
                id=device_data.get("device_id", ""),
                name=device_data.get("name", "Unknown Device"),
                type=self._map_device_type(device_data.get("type", "")),
                status=self._map_device_status(device_data.get("status", "")),
                battery_level=device_data.get("battery_level"),
                last_seen=self._parse_timestamp(device_data.get("last_seen")),
                location=device_data.get("location", "Unknown"),
                alerts=device_data.get("active_alerts", []),
            )
            devices.append(device)

        return devices

    async def get_alerts(self, active_only: bool = True) -> List[SecurityAlert]:
        """Fetch security alerts"""
        endpoint = "/api/alerts/active" if active_only else "/api/alerts"
        data = await self._get(endpoint)
        alerts = []

        for alert_data in data.get("alerts", []):
            alert = SecurityAlert(
                id=alert_data.get("alert_id", ""),
                device_id=alert_data.get("device_id", ""),
                device_name=alert_data.get("device_name", ""),
                alert_type=self._map_alert_type(alert_data.get("alert_type", "")),
                severity=alert_data.get("severity", "warning"),
                message=alert_data.get("message", ""),
                timestamp=self._parse_timestamp(alert_data.get("timestamp")),
                resolved=alert_data.get("resolved", False),
            )
            alerts.append(alert)

        return alerts

    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system health status"""
        data = await self._get("/api/system/status")
        return {
            "online_devices": data.get("online_devices", 0),
            "total_devices": data.get("total_devices", 0),
            "active_alerts": data.get("active_alerts", 0),
            "last_update": self._parse_timestamp(data.get("last_update")),
            "system_health": data.get("health", "unknown"),
        }

    def _map_device_type(self, nest_type: str) -> str:
        """Map Nest Protect device types to unified types"""
        type_mapping = {
            "smoke_detector": "smoke_detector",
            "co_detector": "co_detector",
            "protect": "smoke_detector",  # Generic Nest Protect
        }
        return type_mapping.get(nest_type.lower(), "smoke_detector")

    def _map_device_status(self, nest_status: str) -> str:
        """Map Nest Protect status to unified status"""
        status_mapping = {
            "online": "online",
            "offline": "offline",
            "alert": "alert",
            "warning": "online",  # Warnings are still online
            "ok": "online",
        }
        return status_mapping.get(nest_status.lower(), "offline")

    def _map_alert_type(self, nest_alert_type: str) -> str:
        """Map Nest Protect alert types to unified types"""
        alert_mapping = {
            "smoke": "smoke",
            "co": "co",
            "heat": "smoke",  # Heat alerts treated as smoke
            "test": "info",
            "maintenance": "warning",
        }
        return alert_mapping.get(nest_alert_type.lower(), "warning")

    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime object"""
        if not timestamp_str:
            return None

        try:
            # Try ISO format first
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            try:
                # Try common formats
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                logger.warning(f"Could not parse timestamp: {timestamp_str}")
                return None


class RingMCPClient:
    """
    MCP proxy client for Ring MCP server integration

    Since Ring MCP only exposes MCP interface, this client will proxy
    through an MCP bridge or direct process communication.
    """

    def __init__(self, mcp_server_path: str = "D:\\Dev\\repos\\ring-mcp"):
        self.mcp_server_path = mcp_server_path
        # TODO: Implement MCP proxy when Ring server is working

    async def get_devices(self) -> List[SecurityDevice]:
        """Fetch Ring devices from camera manager."""
        devices = []
        try:
            from ...core.server import TapoCameraServer

            server = await TapoCameraServer.get_instance()
            if hasattr(server, "camera_manager") and server.camera_manager:
                cameras = await server.camera_manager.list_cameras()
                for cam in cameras:
                    if cam.get("type") == "ring":
                        status_dict = cam.get("status", {})
                        if isinstance(status_dict, dict):
                            device = SecurityDevice(
                                id=cam.get("name", ""),
                                name=cam.get("name", ""),
                                type="doorbell",
                                status="online" if status_dict.get("connected") else "offline",
                                battery_level=None,
                                last_seen=None,
                                location="Unknown",
                                alerts=[],
                            )
                            devices.append(device)
        except Exception:
            logger.exception("Failed to get Ring devices from camera manager")
        return devices

    async def get_alerts(self) -> List[SecurityAlert]:
        """Fetch Ring alerts - not yet implemented."""
        # Ring doorbell alerts would come from Ring API
        # For now, return empty list
        return []


class SecurityIntegrationManager:
    """
    Unified manager for all security system integrations

    Coordinates data collection from multiple security MCP servers
    and provides unified interface for dashboard consumption.
    """

    def __init__(self):
        self.nest_client: Optional[NestProtectClient] = None
        self.ring_client: Optional[RingMCPClient] = None
        self._cache: Dict[str, Any] = {}
        self._cache_timeout = timedelta(seconds=30)  # Cache for 30 seconds

    async def initialize(self, config: Dict[str, Any]):
        """Initialize security integrations based on config"""
        # Nest Protect integration
        if config.get("nest_protect", {}).get("enabled", False):
            nest_url = config["nest_protect"].get("server_url", "http://localhost:8123")
            self.nest_client = NestProtectClient(base_url=nest_url)
            await self.nest_client.connect()
            logger.info(f"Initialized Nest Protect integration: {nest_url}")

        # Ring MCP integration (when ready)
        if config.get("ring_mcp", {}).get("enabled", False):
            ring_path = config["ring_mcp"].get("server_path", "D:\\Dev\\repos\\ring-mcp")
            self.ring_client = RingMCPClient(mcp_server_path=ring_path)
            logger.info(f"Initialized Ring MCP integration: {ring_path}")

    async def get_all_devices(self) -> List[SecurityDevice]:
        """Get all security devices from all integrated systems"""
        devices = []

        # Nest Protect devices
        if self.nest_client:
            try:
                nest_devices = await self.nest_client.get_devices()
                devices.extend(nest_devices)
            except Exception:
                logger.exception("Failed to fetch Nest Protect devices")

        # Ring devices (when implemented)
        if self.ring_client:
            try:
                ring_devices = await self.ring_client.get_devices()
                devices.extend(ring_devices)
            except Exception:
                logger.exception("Failed to fetch Ring devices")

        return devices

    async def get_all_alerts(self) -> List[SecurityAlert]:
        """Get all security alerts from all integrated systems"""
        alerts = []

        # Nest Protect alerts
        if self.nest_client:
            try:
                nest_alerts = await self.nest_client.get_alerts()
                alerts.extend(nest_alerts)
            except Exception:
                logger.exception("Failed to fetch Nest Protect alerts")

        # Ring alerts (when implemented)
        if self.ring_client:
            try:
                ring_alerts = await self.ring_client.get_alerts()
                alerts.extend(ring_alerts)
            except Exception:
                logger.exception("Failed to fetch Ring alerts")

        return alerts

    async def get_system_overview(self) -> Dict[str, Any]:
        """Get unified system overview"""
        overview = {
            "total_devices": 0,
            "online_devices": 0,
            "active_alerts": 0,
            "systems": {},
            "last_update": datetime.now(),
        }

        # Nest Protect overview
        if self.nest_client:
            try:
                nest_status = await self.nest_client.get_system_status()
                overview["systems"]["nest_protect"] = nest_status
                overview["total_devices"] += nest_status.get("total_devices", 0)
                overview["online_devices"] += nest_status.get("online_devices", 0)
                overview["active_alerts"] += nest_status.get("active_alerts", 0)
            except Exception as e:
                logger.exception("Failed to get Nest Protect system status")
                overview["systems"]["nest_protect"] = {"error": str(e)}

        # Ring overview (placeholder)
        if self.ring_client:
            overview["systems"]["ring_mcp"] = {"status": "not_implemented"}

        return overview

    async def cleanup(self):
        """Clean up resources"""
        if self.nest_client:
            await self.nest_client.disconnect()


# Global instance for dashboard use
security_manager = SecurityIntegrationManager()
