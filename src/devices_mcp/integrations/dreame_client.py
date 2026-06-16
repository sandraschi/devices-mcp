"""Dreame robot vacuum integration.
Supports two modes:
- Home Assistant REST API (vacuum.dreame_* entities)
- Proxy to a running `dreame-mcp` backend (DreameHome cloud) via /api/v1/*
"""

import os
from dataclasses import dataclass
from typing import Any, Optional

from ..utils import get_logger

logger = get_logger(__name__)
# Dreame integration status
_dreame_client: Optional["DreameClient"] = None


@dataclass
class DreameStatus:
    """Dreame vacuum status information."""

    state: str
    battery_level: int
    cleaning_time: int
    cleaned_area: float
    error_code: int | None
    is_charging: bool
    is_cleaning: bool
    fan_speed: str


class DreameClient:
    """Client for Dreame robot vacuums.
    If a Home Assistant access token is provided, we use HA's REST API.
    If no token is provided, we can optionally proxy to a running `dreame-mcp`
    backend (which uses the DreameHome cloud API).
    """

    def __init__(
        self,
        host: str,
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        dreame_mcp_url: str | None = None,
    ):
        """
        Initialize Dreame client.
        Args:
            host: Home Assistant host IP
            token: Long-lived access token
            username: Dreame account username (optional)
            password: Dreame account password (optional)
        """
        # `host` can be either a raw host (e.g. 192.168.1.10) or a full HA base URL.
        self.host = host
        self.base_url = host if host.startswith("http://") or host.startswith("https://") else f"http://{host}:8123"
        self.token = token
        self.username = username
        self.password = password
        self.session = None
        self.entities: list[dict[str, Any]] = []
        self.mock_mode = token == "MOCK"
        self._mode: str = "ha" if (token and token != "MOCK") else "dreame_mcp"
        self.dreame_mcp_url = (
            (dreame_mcp_url or "").strip().rstrip("/")
            or (os.getenv("DREAME_MCP_URL", "").strip().rstrip("/"))
            or "http://localhost:10894"
        )

    async def connect(self) -> dict[str, Any]:
        """Connect and verify Dreame integration."""
        if self.mock_mode:
            logger.info(f"[MOCK] Connected to Dreame via Home Assistant at {self.host}")
            return {
                "success": True,
                "message": "[MOCK] Connected to Home Assistant (Mock Mode)",
                "entities": [{"entity_id": "vacuum.dreame_d20_mock", "state": "docked"}],
            }
        # Prefer HA when token is provided; otherwise try dreame-mcp proxy.
        if self.token:
            try:
                # Use Home Assistant REST API to communicate with Dreame vacuum
                import aiohttp

                self._mode = "ha"
                self.session = aiohttp.ClientSession(
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json",
                    }
                )
                # Test connection
                async with self.session.get(f"{self.base_url}/api/states") as response:
                    if response.status == 200:
                        states = await response.json()
                        # Look for Dreame vacuum entities
                        dreame_entities = [
                            entity for entity in states if entity.get("entity_id", "").startswith("vacuum.dreame_")
                        ]
                        self.entities = dreame_entities
                        return {
                            "success": True,
                            "message": f"Connected to Home Assistant, found {len(dreame_entities)} Dreame vacuum(s)",
                            "entities": dreame_entities,
                        }
                    return {
                        "success": False,
                        "message": f"Failed to connect: HTTP {response.status}",
                        "error": f"Failed to connect: HTTP {response.status}",
                    }
            except Exception as e:
                logger.exception("Error connecting to Dreame via Home Assistant:")
                return {"success": False, "message": str(e), "error": str(e)}
        # dreame-mcp proxy mode
        try:
            import aiohttp

            self._mode = "dreame_mcp"
            self.session = aiohttp.ClientSession(headers={"Content-Type": "application/json"})
            async with self.session.get(f"{self.dreame_mcp_url}/api/v1/health") as response:
                if response.status != 200:
                    txt = await response.text()
                    return {
                        "success": False,
                        "message": f"dreame-mcp health failed: HTTP {response.status} - {txt[:200]}",
                        "error": f"dreame-mcp health failed: HTTP {response.status} - {txt[:200]}",
                    }
                data = await response.json()
                if not data.get("connected", False):
                    return {
                        "success": False,
                        "message": "dreame-mcp is reachable but not connected",
                        "error": "dreame-mcp is reachable but not connected",
                    }
                return {
                    "success": True,
                    "message": "Connected via dreame-mcp (DreameHome cloud)",
                    "dreame_mcp_url": self.dreame_mcp_url,
                }
        except Exception as e:
            logger.exception("Error connecting to dreame-mcp proxy:")
            return {"success": False, "message": str(e), "error": str(e)}

    async def get_status(self, entity_id: str | None = None) -> DreameStatus | None:
        """Get current status of Dreame vacuum."""
        if self.mock_mode:
            return DreameStatus(
                state="docked",
                battery_level=100,
                cleaning_time=0,
                cleaned_area=0.0,
                error_code=None,
                is_charging=True,
                is_cleaning=False,
                fan_speed="normal",
            )
        try:
            if not self.session:
                return None
            if self._mode == "dreame_mcp":
                async with self.session.get(f"{self.dreame_mcp_url}/api/v1/status") as response:
                    if response.status != 200:
                        return None
                    data = await response.json()
                    if not data.get("success", False):
                        return None
                    return DreameStatus(
                        state=str(data.get("state", "unknown")),
                        battery_level=int(data.get("battery", 0) or 0),
                        cleaning_time=int(data.get("cleaning_time", 0) or 0),
                        cleaned_area=float(data.get("cleaned_area", 0.0) or 0.0),
                        error_code=None,
                        is_charging=str(data.get("state", "")).lower() in ("charging", "docked"),
                        is_cleaning=str(data.get("state", "")).lower() in ("cleaning", "returning"),
                        fan_speed=str(data.get("fan_speed", "normal") or "normal"),
                    )
            eid = entity_id or await self._pick_entity_id()
            if not eid:
                return None
            async with self.session.get(f"{self.base_url}/api/states/{eid}") as response:
                if response.status == 200:
                    data = await response.json()
                    # Parse Dreame vacuum attributes
                    attributes = data.get("attributes", {})
                    state = data.get("state", "unknown")
                    return DreameStatus(
                        state=state,
                        battery_level=attributes.get("battery_level", 0),
                        cleaning_time=attributes.get("cleaning_time", 0),
                        cleaned_area=attributes.get("cleaned_area", 0.0),
                        error_code=attributes.get("error_code"),
                        is_charging=attributes.get("charging", False),
                        is_cleaning=state in ["cleaning", "returning"],
                        fan_speed=attributes.get("fan_speed", "normal"),
                    )
        except Exception:
            logger.exception("Error getting Dreame status:")
            return None

    async def start_cleaning(self, entity_id: str) -> dict[str, Any]:
        """Start cleaning cycle."""
        return await self._call_service(entity_id, "vacuum", "start")

    async def stop_cleaning(self, entity_id: str) -> dict[str, Any]:
        """Stop cleaning cycle."""
        return await self._call_service(entity_id, "vacuum", "stop")

    async def return_to_dock(self, entity_id: str) -> dict[str, Any]:
        """Send vacuum back to dock."""
        return await self._call_service(entity_id, "vacuum", "return_to_base")

    async def pause_cleaning(self, entity_id: str) -> dict[str, Any]:
        """Pause cleaning cycle."""
        return await self._call_service(entity_id, "vacuum", "pause")

    async def set_fan_speed(self, entity_id: str, speed: str) -> dict[str, Any]:
        """Set fan speed (quiet, normal, turbo, max)."""
        return await self._call_service(entity_id, "vacuum", "set_fan_speed", {"fan_speed": speed})

    async def locate_vacuum(self, entity_id: str) -> dict[str, Any]:
        """Locate vacuum by playing sound."""
        return await self._call_service(entity_id, "vacuum", "locate")

    async def _call_service(
        self, entity_id: str, domain: str, service: str, service_data: dict | None = None
    ) -> dict[str, Any]:
        """Call Home Assistant service for Dreame vacuum."""
        try:
            if not self.session:
                return {"success": False, "message": "Not connected", "error": "Not connected"}
            if self._mode == "dreame_mcp":
                # Map HA service calls to dreame-mcp control commands where possible.
                cmd_map = {
                    "start": "start_clean",
                    "stop": "stop",
                    "pause": "pause",
                    "return_to_base": "go_home",
                    "locate": "find_robot",
                }
                cmd = cmd_map.get(service)
                if not cmd:
                    return {
                        "success": False,
                        "message": f"Unsupported dreame-mcp command for service: {service}",
                        "error": f"Unsupported dreame-mcp command for service: {service}",
                    }
                async with self.session.post(f"{self.dreame_mcp_url}/api/v1/control/{cmd}") as response:
                    if response.status == 200:
                        return {"success": True, "message": f"dreame-mcp command {cmd} called successfully"}
                    error_text = await response.text()
                    return {
                        "success": False,
                        "message": f"dreame-mcp control failed: HTTP {response.status} - {error_text}",
                        "error": f"dreame-mcp control failed: HTTP {response.status} - {error_text}",
                    }
            url = f"{self.base_url}/api/services/{domain}/{service}"
            data = {"entity_id": entity_id}
            if service_data:
                data.update(service_data)
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    return {"success": True, "message": f"Service {service} called successfully"}
                error_text = await response.text()
                return {
                    "success": False,
                    "message": f"Service call failed: HTTP {response.status} - {error_text}",
                    "error": f"Service call failed: HTTP {response.status} - {error_text}",
                }
        except Exception as e:
            logger.exception("Error calling service {service}:")
            return {"success": False, "message": str(e), "error": str(e)}

    async def close(self):
        """Close client session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def _pick_entity_id(self) -> str | None:
        """Pick a Dreame vacuum entity_id from cached discovery.
        This keeps robots UI usable even when no explicit entity_id is configured.
        """
        if self.entities:
            eid = self.entities[0].get("entity_id")
            return str(eid) if eid else None
        return None


def get_dreame_client(host: str, token: str, username: str | None = None, password: str | None = None) -> DreameClient:
    """Get or create Dreame client instance."""
    global _dreame_client
    if _dreame_client is None:
        _dreame_client = DreameClient(host, token, username, password)
    return _dreame_client


async def init_dreame_client(
    host: str, token: str, username: str | None = None, password: str | None = None
) -> dict[str, Any]:
    """Initialize Dreame client and test connection."""
    try:
        client = get_dreame_client(host, token, username, password)
        result = await client.connect()
        if result["success"]:
            logger.info("Dreame client initialized successfully")
        else:
            logger.error(f"Failed to initialize Dreame client: {result.get('error')}")
        return result
    except Exception as e:
        logger.exception("Error initializing Dreame client:")
        return {"success": False, "message": str(e), "error": str(e)}
