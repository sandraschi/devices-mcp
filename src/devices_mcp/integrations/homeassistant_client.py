"""
Home Assistant API Client

Fetches device data from Home Assistant REST API.
Used primarily for Nest Protect integration (since HA has verified Google OAuth).
"""

import logging
import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class NestProtectState:
    """Nest Protect device state from Home Assistant."""

    entity_id: str
    friendly_name: str
    location: str
    smoke_status: str  # "idle", "warning", "emergency"
    co_status: str  # "idle", "warning", "emergency"
    battery_level: Optional[int]
    is_online: bool
    last_updated: Optional[datetime]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.friendly_name,
            "location": self.location,
            "smoke_status": self.smoke_status,
            "co_status": self.co_status,
            "battery_level": self.battery_level,
            "is_online": self.is_online,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class HomeAssistantClient:
    """
    Client for Home Assistant REST API.

    Docs: https://developers.home-assistant.io/docs/api/rest/
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8123",
        access_token: Optional[str] = None,
        cache_ttl: int = 30,
    ):
        # Auto-detect Docker environment and adjust URL
        import os

        if os.getenv("CONTAINER") == "yes":
            # In Docker, replace localhost with host.docker.internal for Windows/Mac
            # Or use service name if Home Assistant is in same Docker network
            if "localhost" in base_url or "127.0.0.1" in base_url:
                # Try to detect if HA is in same network (service name) or on host
                ha_service_name = os.getenv("HOMEASSISTANT_SERVICE_NAME", "homeassistant")
                # First try service name (if in same Docker network)
                # Fallback to host.docker.internal (if HA is on host)
                if ha_service_name:
                    # Replace localhost with service name
                    base_url = base_url.replace("localhost", ha_service_name)
                    base_url = base_url.replace("127.0.0.1", ha_service_name)
                else:
                    # Use host.docker.internal for Windows/Mac Docker Desktop
                    base_url = base_url.replace("localhost", "host.docker.internal")
                    base_url = base_url.replace("127.0.0.1", "host.docker.internal")

        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.cache_ttl = cache_ttl

        self._session: Optional[aiohttp.ClientSession] = None
        self._cache: dict[str, Any] = {}
        self._cache_time: dict[str, datetime] = {}
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize the client and verify connection."""
        if not self.access_token:
            logger.warning("No Home Assistant access token configured")
            return False

        try:
            # Ensure we never leak a previous session on re-init attempts.
            if self._session and not self._session.closed:
                await self._session.close()
            self._initialized = False

            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10),
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
            )

            # Test connection
            async with self._session.get(f"{self.base_url}/api/") as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Connected to Home Assistant: {data.get('message')}")
                    self._initialized = True
                    return True
                if response.status == 401:
                    logger.error("Home Assistant: Invalid access token")
                    await self.close()
                    return False
                logger.error(f"Home Assistant connection failed: {response.status}")
                await self.close()
                return False

        except asyncio.CancelledError:
            # Request cancellation during startup must not leak aiohttp sessions.
            await self.close()
            raise
        except aiohttp.ClientConnectorError:
            logger.warning(f"Cannot connect to Home Assistant at {self.base_url}")
            import os

            if os.getenv("CONTAINER") == "yes":
                logger.warning(
                    "  [DOCKER] If Home Assistant is on host, try: http://host.docker.internal:8123"
                )
                logger.warning(
                    "  [DOCKER] If Home Assistant is in Docker, ensure it's on same network"
                )
            await self.close()
            return False
        except Exception:
            logger.exception("Failed to initialize Home Assistant client")
            await self.close()
            return False

    async def close(self) -> None:
        """Close the client session."""
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def _get(self, endpoint: str) -> Optional[dict | list]:
        """Make GET request to HA API."""
        if not self._session:
            return None

        try:
            async with self._session.get(f"{self.base_url}{endpoint}") as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"HA API error: {response.status}")
                return None
        except Exception:
            logger.exception("Error calling HA API:")
            return None

    async def get_states(self) -> list[dict]:
        """Get all entity states."""
        result = await self._get("/api/states")
        return result if isinstance(result, list) else []

    async def get_state(self, entity_id: str) -> Optional[dict]:
        """Get state of a specific entity."""
        return await self._get(f"/api/states/{entity_id}")

    async def get_nest_protect_devices(self) -> list[NestProtectState]:
        """
        Get all Nest Protect devices from Home Assistant.

        HA exposes Nest Protect as multiple entities:
        - binary_sensor.{name}_smoke_status
        - binary_sensor.{name}_co_status
        - sensor.{name}_battery_level
        """
        # Check cache
        cache_key = "nest_protect_devices"
        if cache_key in self._cache:
            age = (datetime.now() - self._cache_time[cache_key]).total_seconds()
            if age < self.cache_ttl:
                return self._cache[cache_key]

        states = await self.get_states()
        if not states:
            return []

        # Group by device
        devices: dict[str, dict] = {}

        for state in states:
            entity_id = state.get("entity_id", "")
            attrs = state.get("attributes", {})

            # Nest Protect smoke sensors
            if "nest" in entity_id.lower() and "smoke" in entity_id.lower():
                device_name = attrs.get("friendly_name", "").replace(" Smoke", "")
                if device_name not in devices:
                    devices[device_name] = {
                        "friendly_name": device_name,
                        "location": attrs.get("area", "Unknown"),
                    }
                devices[device_name]["smoke_entity"] = entity_id
                devices[device_name]["smoke_status"] = (
                    "emergency" if state.get("state") == "on" else "idle"
                )

            # Nest Protect CO sensors
            elif "nest" in entity_id.lower() and "co" in entity_id.lower():
                device_name = attrs.get("friendly_name", "").replace(" CO", "")
                if device_name not in devices:
                    devices[device_name] = {
                        "friendly_name": device_name,
                        "location": attrs.get("area", "Unknown"),
                    }
                devices[device_name]["co_entity"] = entity_id
                devices[device_name]["co_status"] = (
                    "emergency" if state.get("state") == "on" else "idle"
                )

            # Battery level
            elif "nest" in entity_id.lower() and "battery" in entity_id.lower():
                device_name = attrs.get("friendly_name", "").replace(" Battery", "")
                if device_name not in devices:
                    devices[device_name] = {
                        "friendly_name": device_name,
                        "location": attrs.get("area", "Unknown"),
                    }
                try:
                    devices[device_name]["battery_level"] = int(state.get("state", 0))
                except (ValueError, TypeError):
                    devices[device_name]["battery_level"] = None

        # Convert to NestProtectState objects
        result = []
        for name, data in devices.items():
            state = NestProtectState(
                entity_id=data.get("smoke_entity", f"nest.{name}"),
                friendly_name=data.get("friendly_name", name),
                location=data.get("location", "Unknown"),
                smoke_status=data.get("smoke_status", "unknown"),
                co_status=data.get("co_status", "unknown"),
                battery_level=data.get("battery_level"),
                is_online=True,  # If we got data, it's online
                last_updated=datetime.now(),
            )
            result.append(state)

        # Cache results
        self._cache[cache_key] = result
        self._cache_time[cache_key] = datetime.now()

        logger.info(f"Found {len(result)} Nest Protect devices via Home Assistant")
        return result

    async def get_nest_summary(self) -> dict[str, Any]:
        """Get summary of Nest Protect devices."""
        devices = await self.get_nest_protect_devices()

        if not devices:
            return {
                "initialized": False,
                "error": "No Nest Protect devices found in Home Assistant",
                "total_devices": 0,
            }

        smoke_ok = all(d.smoke_status == "idle" for d in devices)
        co_ok = all(d.co_status == "idle" for d in devices)
        all_online = all(d.is_online for d in devices)

        return {
            "initialized": True,
            "total_devices": len(devices),
            "online_count": sum(1 for d in devices if d.is_online),
            "smoke_status": "ok" if smoke_ok else "alert",
            "co_status": "ok" if co_ok else "alert",
            "battery_warnings": [
                d.friendly_name for d in devices if d.battery_level and d.battery_level < 20
            ],
            "all_ok": smoke_ok and co_ok and all_online,
            "devices": [d.to_dict() for d in devices],
        }


# Global client instance
_ha_client: Optional[HomeAssistantClient] = None


async def init_homeassistant_client(
    base_url: str = "http://localhost:8123",
    access_token: Optional[str] = None,
    cache_ttl: int = 30,
) -> Optional[HomeAssistantClient]:
    """Initialize the global Home Assistant client."""
    global _ha_client

    if _ha_client:
        await _ha_client.close()

    _ha_client = HomeAssistantClient(
        base_url=base_url,
        access_token=access_token,
        cache_ttl=cache_ttl,
    )

    if await _ha_client.initialize():
        return _ha_client

    await _ha_client.close()
    _ha_client = None
    return None


def get_homeassistant_client() -> Optional[HomeAssistantClient]:
    """Get the global Home Assistant client instance."""
    return _ha_client
