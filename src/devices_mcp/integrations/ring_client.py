"""
Ring Doorbell and Alarm integration client.

Uses the ring_doorbell library for unofficial API access.
Supports Ring Alarm Base Station EU with sensors.

Ring Alarm Device Kinds (from raw API):
- hub.redsky: Base Station (Gen 2)
- security-panel: Security Panel / Alarm Hub
- sensor.contact: Contact Sensor (door/window)
- sensor.motion: Motion Sensor
- security-keypad: Keypad
- range-extender.zwave: Range Extender
- adapter.sidewalk: Sidewalk Bridge
- alarm.*: Various alarm components
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RingAlarmMode(Enum):
    """Ring alarm modes."""

    DISARMED = "none"
    HOME = "some"
    AWAY = "all"


class RingDeviceType(Enum):
    """Ring device types."""

    DOORBELL = "doorbell"
    CAMERA = "camera"
    ALARM_BASE = "alarm_base"
    SECURITY_PANEL = "security_panel"
    CONTACT_SENSOR = "contact_sensor"
    MOTION_SENSOR = "motion_sensor"
    KEYPAD = "keypad"
    RANGE_EXTENDER = "range_extender"
    SIREN = "siren"
    SMOKE_CO_LISTENER = "smoke_co_listener"
    FLOOD_FREEZE_SENSOR = "flood_freeze_sensor"
    GLASS_BREAK_SENSOR = "glass_break_sensor"
    OTHER = "other"


# Ring device kind mappings to our types
RING_KIND_MAP = {
    # Base station / hub
    "hub.redsky": RingDeviceType.ALARM_BASE,
    "security-panel": RingDeviceType.SECURITY_PANEL,
    "base_station_v1": RingDeviceType.ALARM_BASE,
    # Sensors
    "sensor.contact": RingDeviceType.CONTACT_SENSOR,
    "security.sensor.contact": RingDeviceType.CONTACT_SENSOR,
    "sensor.motion": RingDeviceType.MOTION_SENSOR,
    "security.sensor.motion": RingDeviceType.MOTION_SENSOR,
    "sensor.flood-freeze": RingDeviceType.FLOOD_FREEZE_SENSOR,
    "sensor.glassbreak": RingDeviceType.GLASS_BREAK_SENSOR,
    # Keypad
    "security-keypad": RingDeviceType.KEYPAD,
    "keypad": RingDeviceType.KEYPAD,
    # Range extender
    "range-extender.zwave": RingDeviceType.RANGE_EXTENDER,
    "range-extender": RingDeviceType.RANGE_EXTENDER,
    # Siren
    "siren": RingDeviceType.SIREN,
    "siren.outdoor-strobe": RingDeviceType.SIREN,
    # Smoke/CO
    "listener.smoke-co": RingDeviceType.SMOKE_CO_LISTENER,
    "alarm.smoke": RingDeviceType.SMOKE_CO_LISTENER,
    "alarm.co": RingDeviceType.SMOKE_CO_LISTENER,
}


@dataclass
class RingDevice:
    """Ring device data."""

    id: str
    name: str
    device_type: RingDeviceType
    battery_level: int | None = None
    is_online: bool = True
    last_activity: datetime | None = None
    location_id: str | None = None
    extra_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "device_type": self.device_type.value,
            "battery_level": self.battery_level,
            "is_online": self.is_online,
            "location_id": self.location_id,
            "last_activity": (self.last_activity.isoformat() if self.last_activity else None),
            **self.extra_data,
        }


@dataclass
class RingSensor:
    """Ring sensor state."""

    id: str
    name: str
    sensor_type: str  # contact, motion, flood_freeze, glassbreak, smoke_co
    is_open: bool | None = None  # For contact sensors
    motion_detected: bool = False  # For motion sensors
    battery_level: int | None = None
    is_online: bool = True
    tamper_status: str | None = None  # ok, tamper
    fault_status: bool = False
    location_id: str | None = None
    zone_id: str | None = None
    extra_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "sensor_type": self.sensor_type,
            "is_open": self.is_open,
            "motion_detected": self.motion_detected,
            "battery_level": self.battery_level,
            "is_online": self.is_online,
            "tamper_status": self.tamper_status,
            "fault_status": self.fault_status,
            "location_id": self.location_id,
            "zone_id": self.zone_id,
            **self.extra_data,
        }


@dataclass
class RingBaseStation:
    """Ring Alarm Base Station data."""

    id: str
    name: str
    location_id: str
    mode: RingAlarmMode
    is_online: bool = True
    siren_enabled: bool = True
    firmware: str | None = None
    volume: int | None = None  # 0-100
    brightness: int | None = None  # LED brightness
    extra_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "location_id": self.location_id,
            "mode": self.mode.value,
            "mode_name": self.mode.name.lower(),
            "is_online": self.is_online,
            "siren_enabled": self.siren_enabled,
            "firmware": self.firmware,
            "volume": self.volume,
            "brightness": self.brightness,
            **self.extra_data,
        }


@dataclass
class RingAlarmStatus:
    """Ring alarm status."""

    mode: RingAlarmMode
    is_armed: bool
    base_station: RingBaseStation | None = None
    sensors: list[RingSensor] = field(default_factory=list)
    keypads: list[RingDevice] = field(default_factory=list)
    all_devices: list[RingDevice] = field(default_factory=list)
    entry_delay_active: bool = False
    exit_delay_active: bool = False
    siren_active: bool = False
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "mode": self.mode.value,
            "mode_name": self.mode.name.lower(),
            "is_armed": self.is_armed,
            "base_station": self.base_station.to_dict() if self.base_station else None,
            "sensors": [s.to_dict() for s in self.sensors],
            "keypads": [k.to_dict() for k in self.keypads],
            "sensor_count": len(self.sensors),
            "all_device_count": len(self.all_devices),
            "entry_delay_active": self.entry_delay_active,
            "exit_delay_active": self.exit_delay_active,
            "siren_active": self.siren_active,
            "last_updated": self.last_updated.isoformat(),
        }


class RingClient:
    """Ring doorbell and alarm client with full alarm system support."""

    # Ring Alarm API endpoints
    LOCATIONS_ENDPOINT = "/clients_api/locations"
    ALARM_DEVICES_ENDPOINT = "/clients_api/ring_devices"
    ALARM_MODE_ENDPOINT = "/clients_api/locations/{location_id}/devices/{device_id}/mode"
    SIREN_ENDPOINT = "/clients_api/locations/{location_id}/devices/{device_id}/siren"

    def __init__(
        self,
        email: str,
        password: str | None = None,
        token_file: str = "ring_token.cache",
        cache_ttl: int = 60,
    ):
        self.email = email
        self.password = password
        # Adjust token file path for Docker (use mounted volume)
        self.token_file = self._adjust_token_path(token_file)
        self.cache_ttl = cache_ttl

        self._ring = None
        self._auth = None
        self._cache: dict[str, Any] = {}
        self._cache_time: dict[str, datetime] = {}
        self._2fa_pending = False
        self._initialized = False
        self._last_error: str | None = None

        # Raw API data for alarm devices
        self._raw_devices_data: dict[str, Any] = {}
        self._locations: list[dict] = []

    @staticmethod
    def _adjust_token_path(token_file: str) -> Path:
        """Adjust token file path for Docker environment."""
        import os

        token_path = Path(token_file)

        # In Docker, use mounted volume for token persistence
        if os.getenv("CONTAINER") == "yes":
            # If token file is in current directory, move to /app/tokens
            if not token_path.is_absolute():
                tokens_dir = Path("/app/tokens")
                tokens_dir.mkdir(parents=True, exist_ok=True)
                return tokens_dir / token_path.name
            # If absolute path, ensure parent directory exists
            token_path.parent.mkdir(parents=True, exist_ok=True)

        return token_path

    async def initialize(self) -> bool:
        """Initialize Ring connection."""
        self._last_error = None
        try:
            from ring_doorbell import Auth, Ring

            # Check for cached token
            if self.token_file.exists():
                logger.info("Loading Ring token from cache")
                token_data = json.loads(self.token_file.read_text())
                self._auth = Auth("TapoCameraMCP/1.0", token_data, self._token_updated)
                self._ring = Ring(self._auth)
                await asyncio.to_thread(self._ring.update_data)
                self._initialized = True
                logger.info("Ring initialized from cached token")

                # Fetch additional alarm data
                await self._fetch_alarm_data()
                return True

            # Need fresh authentication
            if not self.password:
                self._last_error = "Ring password required for initial authentication"
                logger.error("Ring password required for initial authentication")
                return False

            logger.info("Authenticating with Ring...")
            self._auth = Auth("TapoCameraMCP/1.0", None, self._token_updated)

            try:
                await asyncio.to_thread(self._auth.fetch_token, self.email, self.password)
            except Exception as e:
                error_str = str(type(e).__name__).lower() + " " + str(e).lower()
                if "2fa" in error_str or "verification" in error_str or "requires2fa" in error_str:
                    self._2fa_pending = True
                    logger.warning("Ring 2FA required - check your email/SMS for code")
                    return True  # Return True so client stays active for 2FA
                raise

            self._ring = Ring(self._auth)
            await asyncio.to_thread(self._ring.update_data)
            self._initialized = True
            logger.info("Ring initialized successfully")

            # Fetch additional alarm data
            await self._fetch_alarm_data()

        except ImportError:
            self._last_error = "ring_doorbell package not installed (pip install ring-doorbell)"
            logger.warning("ring_doorbell library not installed")
            return False
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}"
            logger.exception("Failed to initialize Ring")
            return False
        else:
            return True

    def _token_updated(self, token: dict):
        """Callback when token is updated."""
        self.token_file.write_text(json.dumps(token))
        logger.debug("Ring token updated and cached")

    async def submit_2fa_code(self, code: str) -> bool:
        """Submit 2FA verification code."""
        if not self._2fa_pending:
            logger.warning("No 2FA pending")
            return False

        try:
            await asyncio.to_thread(self._auth.fetch_token, self.email, self.password, code)
            self._2fa_pending = False

            from ring_doorbell import Ring

            self._ring = Ring(self._auth)
            await asyncio.to_thread(self._ring.update_data)
            self._initialized = True
            logger.info("Ring 2FA completed successfully")

            # Fetch additional alarm data
            await self._fetch_alarm_data()
        except Exception as e:
            self._last_error = f"{type(e).__name__}: {e}"
            logger.exception("Ring 2FA failed")
            return False
        else:
            return True

    @property
    def is_2fa_pending(self) -> bool:
        return self._2fa_pending

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def last_error(self) -> str | None:
        return self._last_error

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_time:
            return False
        elapsed = (datetime.now() - self._cache_time[key]).total_seconds()
        return elapsed < self.cache_ttl

    async def _update_data(self, force: bool = False):
        """Update Ring data from API.

        Args:
            force: If True, bypass cache and force refresh from Ring API.
                   Use sparingly due to rate limiting and async issues.
        """
        if not self._initialized or not self._ring:
            return

        # Check if we need to update (use longer interval to avoid async issues)
        update_cache_key = "_last_update"
        if not force and self._is_cache_valid(update_cache_key):
            return  # Data is fresh enough

        try:
            # Skip data refresh for now due to async event loop conflicts
            # The ring_doorbell library has internal async code that conflicts
            # with FastAPI's async event loop. Data is refreshed during init.
            logger.debug("Skipping Ring data refresh to avoid async conflicts")
            await self._fetch_alarm_data()

            # Mark as updated with longer TTL
            self._cache_time[update_cache_key] = datetime.now()
        except Exception:
            # Log error - don't use stale cached data
            logger.exception("Ring data refresh failed:")
            raise  # Re-raise to fail properly instead of using stale data

    async def _fetch_alarm_data(self):
        """Fetch raw alarm device data from Ring API.

        Ring Alarm uses a separate API structure from doorbells:
        - Doorbells: /clients_api/ring_devices (video devices)
        - Alarm: /clients_api/locations/{location_id} (security panel + Z-Wave devices)
        """
        if not self._ring:
            return

        try:
            # Get raw devices_data which includes doorbells and some alarm devices
            self._raw_devices_data = self._ring.devices_data.copy()
            logger.info(f"Ring raw device types available: {list(self._raw_devices_data.keys())}")

            # Log what we found for debugging
            total_devices = 0
            alarm_device_count = 0
            for dev_type, devices in self._raw_devices_data.items():
                if devices:
                    total_devices += len(devices)
                    logger.info(f"Ring: Found {len(devices)} '{dev_type}' devices")
                    for dev_id, dev_data in devices.items():
                        kind = dev_data.get("kind", "unknown")
                        name = dev_data.get("description", "Unknown")
                        logger.debug(f"  - {name} (kind={kind}, id={dev_id})")

                        # Count alarm-related devices
                        if any(k in kind.lower() for k in ["hub", "base", "panel", "sensor", "keypad", "siren"]):
                            alarm_device_count += 1

            logger.info(f"Ring: Total {total_devices} devices, {alarm_device_count} alarm-related")

            # CRITICAL: Alarm devices are location-specific and accessed via locations API
            # The ring_doorbell library's devices_data may not include all alarm devices
            # We need to query locations endpoint directly
            await self._fetch_locations_alarm_data()

        except Exception as e:
            logger.warning(f"Failed to fetch alarm data: {e}")

    async def _fetch_locations_alarm_data(self):
        """Fetch alarm devices from locations/security panel API.

        Ring Alarm base station and sensors are under locations, not ring_devices.
        This is why doorbell works but alarm doesn't - different API endpoints!
        """
        if not self._ring or not self._auth:
            return

        try:
            # Access locations endpoint directly
            # Ring Alarm devices are under locations, not ring_devices
            # Use Ring's internal async_query method (handles auth)
            endpoint = self.LOCATIONS_ENDPOINT  # "/clients_api/locations"
            response = await self._ring._async_query(endpoint, method="GET")

            if response.status_code == 200:
                locations_data = response.json()
                self._locations = locations_data if isinstance(locations_data, list) else []

                logger.info(f"Ring: Found {len(self._locations)} locations")

                # Each location can have a security_panel with alarm devices
                for location in self._locations:
                    location_id = location.get("id")
                    location_name = location.get("name", "Unknown Location")

                    # Check for security panel (base station)
                    security_panel = location.get("security_panel")
                    if security_panel:
                        logger.info(f"Ring: Location '{location_name}' has security panel (alarm system)")

                        # Security panel has devices list (sensors, keypads, etc.)
                        panel_devices = security_panel.get("devices", [])
                        logger.info(f"Ring: Security panel has {len(panel_devices)} devices")

                        # Add security panel as base station to raw devices
                        if "other" not in self._raw_devices_data:
                            self._raw_devices_data["other"] = {}

                        # Add base station
                        base_station_id = security_panel.get("id")
                        if base_station_id:
                            self._raw_devices_data["other"][str(base_station_id)] = {
                                "kind": "security-panel",
                                "description": f"{location_name} Base Station",
                                "location_id": str(location_id),
                                "mode": security_panel.get("mode", "none"),
                                "firmware_version": security_panel.get("firmware_version"),
                                "status": "online" if security_panel.get("online") else "offline",
                            }

                        # Add all alarm devices from security panel
                        for device in panel_devices:
                            device_id = device.get("device_id") or device.get("id")
                            if device_id:
                                device_kind = device.get("kind", "unknown")
                                device_name = device.get("description") or device.get("name", f"Device {device_id}")

                                self._raw_devices_data["other"][str(device_id)] = {
                                    "kind": device_kind,
                                    "description": device_name,
                                    "location_id": str(location_id),
                                    "battery_life": device.get("battery_percentage"),
                                    "status": device.get("status", "online"),
                                    "firmware_version": device.get("firmware_version"),
                                    "zwave_node_id": device.get("zwave_node_id"),
                                    "zone_id": device.get("zone_id"),
                                    "tamper_status": device.get("tamper_status"),
                                    "fault_status": device.get("fault_status"),
                                    # Sensor-specific fields
                                    "faulted": device.get("faulted", False),
                                    "motion_detected": device.get("motion_detected", False),
                                }

                                logger.debug(
                                    f"Ring: Added alarm device '{device_name}' ({device_kind}) from location '{location_name}'"
                                )
                    else:
                        logger.debug(f"Ring: Location '{location_name}' has no security panel (no alarm system)")
            else:
                logger.warning(f"Ring: Failed to fetch locations (status {response.status_code})")

        except Exception as e:
            logger.warning(f"Failed to fetch locations alarm data: {e}")
            logger.debug(f"Exception details: {type(e).__name__}: {e}", exc_info=True)

    def _get_device_type(self, kind: str) -> RingDeviceType:
        """Map Ring device kind to our device type."""
        kind_lower = kind.lower() if kind else ""
        if kind_lower in RING_KIND_MAP:
            return RING_KIND_MAP[kind_lower]

        # Fuzzy matching for unknown kinds
        if "contact" in kind_lower or "door" in kind_lower or "window" in kind_lower:
            return RingDeviceType.CONTACT_SENSOR
        if "motion" in kind_lower:
            return RingDeviceType.MOTION_SENSOR
        if "keypad" in kind_lower:
            return RingDeviceType.KEYPAD
        if "hub" in kind_lower or "base" in kind_lower or "panel" in kind_lower:
            return RingDeviceType.ALARM_BASE
        if "range" in kind_lower or "extender" in kind_lower:
            return RingDeviceType.RANGE_EXTENDER
        if "siren" in kind_lower:
            return RingDeviceType.SIREN
        if "smoke" in kind_lower or "co" in kind_lower:
            return RingDeviceType.SMOKE_CO_LISTENER

        return RingDeviceType.OTHER

    async def get_doorbells(self) -> list[RingDevice]:
        """Get all Ring doorbells."""
        if not self._initialized:
            return []

        cache_key = "doorbells"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        try:
            # Skip _update_data() to avoid async conflicts
            # Use cached data from initialization instead
            devices = []

            # Access video devices directly from raw data to avoid async calls
            doorbots_data = self._raw_devices_data.get("doorbots", {})
            for dev_id, dev_data in doorbots_data.items():
                device = RingDevice(
                    id=str(dev_id),
                    name=dev_data.get("description", f"Doorbell {dev_id}"),
                    device_type=RingDeviceType.DOORBELL,
                    battery_level=dev_data.get("battery_life"),
                    is_online=dev_data.get("status") != "offline",
                    extra_data={
                        "kind": dev_data.get("kind", "doorbell"),
                        "has_subscription": dev_data.get("has_subscription", False),
                        "firmware": dev_data.get("firmware_version"),
                    },
                )
                devices.append(device)

            self._cache[cache_key] = devices
            self._cache_time[cache_key] = datetime.now()
            logger.info(f"Ring: Found {len(devices)} doorbells from cached data")
        except Exception:
            logger.exception("Failed to get Ring doorbells")
            return []
        else:
            return devices

    async def get_alarm_devices(self) -> list[RingDevice]:
        """Get all Ring Alarm devices from raw API data."""
        if not self._initialized:
            logger.debug("Ring not initialized, returning empty alarm devices")
            return []

        cache_key = "alarm_devices"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        try:
            # Don't force refresh - use cached data from initialization
            # This avoids the nested async event loop issue
            if not self._raw_devices_data:
                logger.warning("No raw Ring device data available")
                return []

            devices = []

            # Check all device categories for alarm-related devices
            alarm_kinds = {"hub", "base", "panel", "sensor", "keypad", "siren", "range_extender"}

            for category, category_devices in self._raw_devices_data.items():
                for dev_id, dev_data in category_devices.items():
                    kind = dev_data.get("kind", "").lower()

                    # Check if this is an alarm-related device
                    is_alarm_device = any(ak in kind for ak in alarm_kinds)

                    if is_alarm_device:
                        device_type = self._get_device_type(kind)
                        name = dev_data.get("description", f"Device {dev_id}")
                        battery = dev_data.get("battery_life")
                        location_id = dev_data.get("location_id")

                        # Determine online status
                        is_online = True
                        if "status" in dev_data:
                            is_online = dev_data["status"] not in ["offline", "disconnected"]

                        device = RingDevice(
                            id=str(dev_id),
                            name=name,
                            device_type=device_type,
                            battery_level=battery,
                            is_online=is_online,
                            location_id=location_id,
                            extra_data={
                                "kind": kind,
                                "category": category,
                                "firmware": dev_data.get("firmware_version"),
                                "zwave_node_id": dev_data.get("zwave_node_id"),
                                "serial": dev_data.get("serial_number"),
                            },
                        )
                        devices.append(device)
                        logger.debug(f"Found alarm device: {name} ({kind})")

            logger.info(f"Ring: Found {len(devices)} alarm devices in raw data")

            self._cache[cache_key] = devices
            self._cache_time[cache_key] = datetime.now()
            return devices

        except Exception:
            logger.exception("Failed to get Ring alarm devices")
            return []

    async def get_alarm_status(self) -> RingAlarmStatus | None:
        """Get Ring alarm status including sensors and base station."""
        if not self._initialized:
            return None

        cache_key = "alarm_status"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        try:
            await self._update_data()

            mode = RingAlarmMode.DISARMED
            base_station: RingBaseStation | None = None
            sensors: list[RingSensor] = []
            keypads: list[RingDevice] = []
            all_devices: list[RingDevice] = []
            siren_active = False
            entry_delay = False
            exit_delay = False

            # Process raw 'other' devices (alarm devices are here)
            other_devices = self._raw_devices_data.get("other", {})

            for dev_id, dev_data in other_devices.items():
                kind = dev_data.get("kind", "")
                device_type = self._get_device_type(kind)
                name = dev_data.get("description", f"Device {dev_id}")
                location_id = dev_data.get("location_id")

                # Extract common fields
                battery = dev_data.get("battery_life")
                is_online = (
                    dev_data.get("status") not in ["offline", "disconnected", None] if "status" in dev_data else True
                )

                # Create base device
                device = RingDevice(
                    id=str(dev_id),
                    name=name,
                    device_type=device_type,
                    battery_level=battery,
                    is_online=is_online,
                    location_id=location_id,
                    extra_data={"kind": kind},
                )
                all_devices.append(device)

                # Handle specific device types
                if device_type in (RingDeviceType.ALARM_BASE, RingDeviceType.SECURITY_PANEL):
                    # Extract mode from base station
                    mode_str = dev_data.get("mode", "none")
                    if mode_str == "all":
                        mode = RingAlarmMode.AWAY
                    elif mode_str == "some":
                        mode = RingAlarmMode.HOME
                    else:
                        mode = RingAlarmMode.DISARMED

                    siren_active = dev_data.get("siren_status", {}).get("state") == "active"

                    base_station = RingBaseStation(
                        id=str(dev_id),
                        name=name,
                        location_id=location_id or "",
                        mode=mode,
                        is_online=is_online,
                        firmware=dev_data.get("firmware_version"),
                        volume=dev_data.get("volume"),
                        brightness=dev_data.get("brightness"),
                        extra_data={
                            "kind": kind,
                            "alarm_state": dev_data.get("alarm_state"),
                        },
                    )

                elif device_type == RingDeviceType.CONTACT_SENSOR:
                    # Contact sensor (door/window)
                    faulted = dev_data.get("faulted", False)
                    tamper = dev_data.get("tamper_status")

                    sensor = RingSensor(
                        id=str(dev_id),
                        name=name,
                        sensor_type="contact",
                        is_open=faulted,  # faulted = open
                        battery_level=battery,
                        is_online=is_online,
                        tamper_status=tamper,
                        fault_status=faulted,
                        location_id=location_id,
                        zone_id=dev_data.get("zone_id"),
                        extra_data={"kind": kind},
                    )
                    sensors.append(sensor)

                elif device_type == RingDeviceType.MOTION_SENSOR:
                    # Motion sensor
                    motion = dev_data.get("motion_detected", False)
                    tamper = dev_data.get("tamper_status")

                    sensor = RingSensor(
                        id=str(dev_id),
                        name=name,
                        sensor_type="motion",
                        motion_detected=motion,
                        battery_level=battery,
                        is_online=is_online,
                        tamper_status=tamper,
                        location_id=location_id,
                        zone_id=dev_data.get("zone_id"),
                        extra_data={"kind": kind},
                    )
                    sensors.append(sensor)

                elif device_type == RingDeviceType.KEYPAD:
                    keypads.append(device)

                elif device_type == RingDeviceType.FLOOD_FREEZE_SENSOR:
                    # Flood/freeze sensor
                    flood = dev_data.get("flood", {}).get("faulted", False)
                    freeze = dev_data.get("freeze", {}).get("faulted", False)

                    sensor = RingSensor(
                        id=str(dev_id),
                        name=name,
                        sensor_type="flood_freeze",
                        fault_status=flood or freeze,
                        battery_level=battery,
                        is_online=is_online,
                        location_id=location_id,
                        extra_data={
                            "kind": kind,
                            "flood_detected": flood,
                            "freeze_detected": freeze,
                        },
                    )
                    sensors.append(sensor)

                elif device_type == RingDeviceType.SMOKE_CO_LISTENER:
                    # Smoke/CO listener
                    smoke = dev_data.get("smoke", {}).get("alarm_status") == "active"
                    co = dev_data.get("co", {}).get("alarm_status") == "active"

                    sensor = RingSensor(
                        id=str(dev_id),
                        name=name,
                        sensor_type="smoke_co",
                        fault_status=smoke or co,
                        battery_level=battery,
                        is_online=is_online,
                        location_id=location_id,
                        extra_data={
                            "kind": kind,
                            "smoke_detected": smoke,
                            "co_detected": co,
                        },
                    )
                    sensors.append(sensor)

            # Check for entry/exit delay from alarm state
            if base_station and base_station.extra_data.get("alarm_state"):
                alarm_state = base_station.extra_data["alarm_state"]
                entry_delay = "entry" in str(alarm_state).lower()
                exit_delay = "exit" in str(alarm_state).lower()

            status = RingAlarmStatus(
                mode=mode,
                is_armed=mode != RingAlarmMode.DISARMED,
                base_station=base_station,
                sensors=sensors,
                keypads=keypads,
                all_devices=all_devices,
                entry_delay_active=entry_delay,
                exit_delay_active=exit_delay,
                siren_active=siren_active,
            )

            self._cache[cache_key] = status
            self._cache_time[cache_key] = datetime.now()
            return status

        except Exception:
            logger.exception("Failed to get Ring alarm status")
            return None

    async def set_alarm_mode(self, mode: RingAlarmMode) -> bool:
        """Set Ring alarm mode (arm/disarm)."""
        if not self._initialized:
            return False

        try:
            # Clear cache
            self._cache.pop("alarm_status", None)
            self._cache.pop("alarm_devices", None)

            # Find base station or security panel from raw data
            other_devices = self._raw_devices_data.get("other", {})
            base_station_id = None
            location_id = None

            for dev_id, dev_data in other_devices.items():
                kind = dev_data.get("kind", "")
                device_type = self._get_device_type(kind)

                if device_type in (RingDeviceType.ALARM_BASE, RingDeviceType.SECURITY_PANEL):
                    base_station_id = dev_id
                    location_id = dev_data.get("location_id")
                    break

            if not base_station_id or not location_id:
                logger.warning("No Ring alarm base station found")
                return False

            # Set mode via Ring API
            # The ring_doorbell library's Ring.groups() doesn't expose alarm mode setting
            # We need to use the raw API directly
            endpoint = f"/clients_api/locations/{location_id}/devices/{base_station_id}/mode"
            try:
                await self._ring.async_query(
                    endpoint,
                    method="PUT",
                    json={"mode": mode.value},
                )
                logger.info(f"Ring alarm mode set to {mode.name} via API")
                return True
            except AttributeError:
                # Fallback: Try using groups() method
                alarm_groups = self._ring.groups() if hasattr(self._ring, "groups") else {}
                for _group_name, group_devices in alarm_groups.items():
                    for device in group_devices:
                        if hasattr(device, "set_mode"):
                            await asyncio.to_thread(device.set_mode, mode.value)
                            logger.info(f"Ring alarm mode set to {mode.name} via groups")
                            return True

            logger.warning("Could not set Ring alarm mode")
            return False

        except Exception:
            logger.exception("Failed to set Ring alarm mode")
            return False

    async def trigger_siren(self, activate: bool = True, duration: int = 30) -> bool:
        """Trigger or stop the Ring alarm siren.

        Args:
            activate: True to activate siren, False to deactivate
            duration: Siren duration in seconds (only for activation)

        Returns:
            True if successful
        """
        if not self._initialized:
            return False

        try:
            # Clear cache
            self._cache.pop("alarm_status", None)

            # Find base station
            other_devices = self._raw_devices_data.get("other", {})
            base_station_id = None
            location_id = None

            for dev_id, dev_data in other_devices.items():
                kind = dev_data.get("kind", "")
                device_type = self._get_device_type(kind)

                if device_type in (RingDeviceType.ALARM_BASE, RingDeviceType.SECURITY_PANEL):
                    base_station_id = dev_id
                    location_id = dev_data.get("location_id")
                    break

            if not base_station_id or not location_id:
                logger.warning("No Ring alarm base station found for siren control")
                return False

            # Siren control via API
            endpoint = f"/clients_api/locations/{location_id}/devices/{base_station_id}/siren"
            state = "on" if activate else "off"

            try:
                await self._ring.async_query(
                    endpoint,
                    method="PUT",
                    json={"state": state, "duration": duration},
                )
                action = "activated" if activate else "deactivated"
                logger.info(f"Ring alarm siren {action}")
                return True
            except Exception:
                logger.exception("Failed to control siren:")
                return False

        except Exception:
            logger.exception("Failed to control Ring siren")
            return False

    async def get_alarm_events(self, limit: int = 50) -> list[dict]:
        """Get recent Ring Alarm events (entry, exit, arm, disarm, etc.)."""
        if not self._initialized:
            return []

        cache_key = f"alarm_events_{limit}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        try:
            events = []

            # Get location IDs from alarm devices
            location_ids = set()
            other_devices = self._raw_devices_data.get("other", {})
            for dev_data in other_devices.values():
                if loc := dev_data.get("location_id"):
                    location_ids.add(loc)

            # Query alarm history for each location
            for location_id in location_ids:
                try:
                    endpoint = f"/clients_api/locations/{location_id}/history"
                    response = await self._ring.async_query(
                        endpoint,
                        method="GET",
                        extra_params={"limit": limit},
                    )
                    if hasattr(response, "json"):
                        history = response.json()
                        for event in history:
                            events.append(
                                {
                                    "id": event.get("id"),
                                    "event_type": event.get("kind", "unknown"),
                                    "device_id": event.get("device_id"),
                                    "device_name": event.get("device_description", "Unknown"),
                                    "timestamp": event.get("created_at"),
                                    "location_id": location_id,
                                    "extra": {
                                        "mode": event.get("mode"),
                                        "actor": event.get("actor"),
                                    },
                                }
                            )
                except Exception as e:
                    logger.debug(f"Could not fetch alarm history for {location_id}: {e}")

            # Sort by timestamp
            events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            events = events[:limit]

            self._cache[cache_key] = events
            self._cache_time[cache_key] = datetime.now()
            return events

        except Exception:
            logger.exception("Failed to get Ring alarm events")
            return []

    async def get_doorbell_snapshot(self, device_id: str) -> bytes | None:
        """Get a snapshot from a Ring doorbell."""
        if not self._initialized:
            return None

        try:
            for doorbell in self._ring.video_devices():
                if str(doorbell.id) == device_id:
                    # Get last recording snapshot if available
                    if hasattr(doorbell, "recording_download"):
                        # This would get the last event snapshot
                        pass
                    return None
        except Exception:
            logger.exception("Failed to get Ring snapshot")
            return None
        else:
            return None

    async def get_recent_events(self, limit: int = 10) -> list[dict]:
        """Get recent Ring events (motion, ding, etc.)."""
        if not self._initialized:
            return []

        cache_key = f"events_{limit}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        try:
            events = []

            for doorbell in self._ring.video_devices():
                try:
                    # Use async history method
                    history = await doorbell.async_history(limit=limit)
                    for event in history:
                        event_data = {
                            "device_id": str(doorbell.id),
                            "device_name": doorbell.name,
                            "event_type": event.get("kind", "unknown"),
                            "timestamp": event.get("created_at"),
                            "answered": event.get("answered", False),
                            "recording_id": event.get("id"),
                            "duration": event.get("duration"),
                        }
                        # Try to get video URL for this event
                        try:
                            if event.get("id"):
                                url = await doorbell.async_recording_url(event["id"])
                                event_data["video_url"] = url
                        except Exception as url_err:
                            logger.debug("Could not get video URL: %s", url_err)
                        events.append(event_data)
                except Exception as e:
                    logger.warning(f"Failed to get history for {doorbell.name}: {e}")

            # Sort by timestamp
            events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            events = events[:limit]

            self._cache[cache_key] = events
            self._cache_time[cache_key] = datetime.now()
        except Exception:
            logger.exception("Failed to get Ring events")
            return []
        else:
            return events

    async def get_summary(self) -> dict:
        """Get a summary of Ring status for dashboard."""
        doorbells = await self.get_doorbells()
        alarm_status = await self.get_alarm_status()
        doorbell_events = await self.get_recent_events(limit=5)
        alarm_events = await self.get_alarm_events(limit=5)

        # Combine and sort all events
        all_events = doorbell_events + alarm_events
        all_events.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Alarm device summary
        alarm_devices = await self.get_alarm_devices()
        contact_sensors = [d for d in alarm_devices if d.device_type == RingDeviceType.CONTACT_SENSOR]
        motion_sensors = [d for d in alarm_devices if d.device_type == RingDeviceType.MOTION_SENSOR]

        return {
            "initialized": self._initialized,
            "2fa_pending": self._2fa_pending,
            "doorbells": [d.to_dict() for d in doorbells],
            "doorbell_count": len(doorbells),
            "alarm": alarm_status.to_dict() if alarm_status else None,
            "alarm_devices": {
                "total": len(alarm_devices),
                "contact_sensors": len(contact_sensors),
                "motion_sensors": len(motion_sensors),
                "base_station": alarm_status.base_station.to_dict()
                if alarm_status and alarm_status.base_station
                else None,
            },
            "recent_events": all_events[:10],
            "doorbell_events": doorbell_events,
            "alarm_events": alarm_events,
            "last_event": all_events[0] if all_events else None,
        }


# Singleton instance - DEPRECATED: Use server-level storage instead
ring_client: RingClient | None = None

# Server-level storage for Ring clients (to avoid singleton issues in web apps)
_server_ring_clients: dict[str, RingClient] = {}


def get_ring_client(server_id: str = "default") -> RingClient | None:
    """Get the Ring client for a specific server instance.

    Returns the stored client even when not yet initialized (e.g. 2FA pending or failed
    attempt) so /status can read is_2fa_pending and _last_error. Callers that need a live
    session must check client.is_initialized.
    """
    if server_id in _server_ring_clients:
        client = _server_ring_clients[server_id]
        if client:
            return client

    if ring_client:
        return ring_client

    for client in _server_ring_clients.values():
        if client:
            return client

    return None


def set_ring_client(client: RingClient, server_id: str = "default") -> None:
    """Store a Ring client for a specific server instance."""
    _server_ring_clients[server_id] = client


def _resolve_token_file(token_file: str) -> str:
    """Resolve relative token paths to repo root so cwd (e.g. web-sota) does not break cache."""
    p = Path(token_file)
    if p.is_absolute():
        return str(p)
    root = Path(__file__).resolve().parents[3]
    return str(root / p)


async def init_ring_client(
    email: str,
    password: str | None = None,
    token_file: str = "ring_token.cache",
    cache_ttl: int = 60,
    server_id: str = "default",
) -> RingClient:
    """Initialize the Ring client for a specific server instance."""
    global ring_client
    token_path = _resolve_token_file(token_file)

    existing = _server_ring_clients.get(server_id)
    if existing and existing.is_initialized:
        return existing

    if existing and not existing.is_initialized:
        await existing.initialize()
        set_ring_client(existing, server_id)
        ring_client = existing
        return existing

    client = RingClient(
        email=email,
        password=password,
        token_file=token_path,
        cache_ttl=cache_ttl,
    )
    await client.initialize()

    set_ring_client(client, server_id)

    ring_client = client

    return client
