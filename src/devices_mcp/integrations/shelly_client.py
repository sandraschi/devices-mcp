"""
Shelly device integration client.

Supports Shelly Plus devices with Add-On temperature sensors (DS18B20).
Perfect for freezer/fridge monitoring with external probes.

Shelly devices expose a simple REST API on the local network.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class ShellyDeviceType(Enum):
    """Shelly device types."""

    PLUS_1 = "plus_1"
    PLUS_2PM = "plus_2pm"
    PLUS_I4 = "plus_i4"
    PRO_1 = "pro_1"
    PRO_2 = "pro_2"
    PRO_4PM = "pro_4pm"
    HT = "ht"  # Humidity & Temperature
    FLOOD = "flood"
    UNKNOWN = "unknown"


@dataclass
class ShellyTemperatureSensor:
    """Shelly temperature sensor reading."""

    id: str
    name: str
    temperature_c: float
    temperature_f: float
    device_ip: str
    device_name: str
    sensor_index: int = 0
    last_updated: datetime = field(default_factory=datetime.now)
    is_online: bool = True
    # Alert thresholds
    high_threshold_c: float | None = None
    low_threshold_c: float | None = None
    alert_active: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "temperature_c": round(self.temperature_c, 1),
            "temperature_f": round(self.temperature_f, 1),
            "device_ip": self.device_ip,
            "device_name": self.device_name,
            "sensor_index": self.sensor_index,
            "last_updated": self.last_updated.isoformat(),
            "is_online": self.is_online,
            "high_threshold_c": self.high_threshold_c,
            "low_threshold_c": self.low_threshold_c,
            "alert_active": self.alert_active,
        }


@dataclass
class ShellyDevice:
    """Shelly device info."""

    ip: str
    name: str
    device_type: ShellyDeviceType
    mac: str = ""
    firmware: str = ""
    is_online: bool = True
    has_temperature: bool = False
    temperature_sensors: list[ShellyTemperatureSensor] = field(default_factory=list)
    extra_data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "name": self.name,
            "device_type": self.device_type.value,
            "mac": self.mac,
            "firmware": self.firmware,
            "is_online": self.is_online,
            "has_temperature": self.has_temperature,
            "temperature_sensors": [s.to_dict() for s in self.temperature_sensors],
            **self.extra_data,
        }


class ShellyClient:
    """Client for Shelly devices with temperature sensors."""

    def __init__(
        self,
        devices: list[dict] | None = None,
        cache_ttl: int = 30,
        timeout: int = 5,
    ):
        """Initialize Shelly client.

        Args:
            devices: List of device configs [{"ip": "192.168.1.x", "name": "Freezer", "thresholds": {...}}]
            cache_ttl: Cache time-to-live in seconds
            timeout: HTTP request timeout
        """
        self.devices_config = devices or []
        self.cache_ttl = cache_ttl
        self.timeout = timeout

        self._cache: dict[str, Any] = {}
        self._cache_time: dict[str, datetime] = {}
        self._devices: dict[str, ShellyDevice] = {}
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize and discover Shelly devices."""
        try:
            for config in self.devices_config:
                ip = config.get("ip")
                if not ip:
                    continue

                device = await self._discover_device(ip, config)
                if device:
                    self._devices[ip] = device
                    logger.info(f"Shelly device discovered: {device.name} ({ip})")

            self._initialized = len(self._devices) > 0
            if self._initialized:
                logger.info(f"Shelly client initialized with {len(self._devices)} devices")
            else:
                logger.warning("No Shelly devices found")

            return self._initialized

        except Exception:
            logger.exception("Failed to initialize Shelly client")
            return False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_time:
            return False
        elapsed = (datetime.now() - self._cache_time[key]).total_seconds()
        return elapsed < self.cache_ttl

    async def _discover_device(self, ip: str, config: dict) -> ShellyDevice | None:
        """Discover a Shelly device and its capabilities."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                # Get device info (Gen 2+ API)
                async with session.get(f"http://{ip}/rpc/Shelly.GetDeviceInfo") as resp:
                    if resp.status == 200:
                        info = await resp.json()
                        return await self._create_device_from_info(ip, info, config, session)

                # Try Gen 1 API fallback
                async with session.get(f"http://{ip}/shelly") as resp:
                    if resp.status == 200:
                        info = await resp.json()
                        return self._create_device_gen1(ip, info, config)

        except TimeoutError:
            logger.warning(f"Shelly device at {ip} timed out")
        except aiohttp.ClientError as e:
            logger.warning(f"Shelly device at {ip} connection error: {e}")
        except Exception:
            logger.exception("Failed to discover Shelly device at")

        return None

    async def _create_device_from_info(
        self, ip: str, info: dict, config: dict, session: aiohttp.ClientSession
    ) -> ShellyDevice:
        """Create device from Gen 2+ API info."""
        name = config.get("name") or info.get("name") or f"Shelly {ip}"
        mac = info.get("mac", "")
        firmware = info.get("fw_id", "")
        model = info.get("model", "").lower()

        # Determine device type
        device_type = ShellyDeviceType.UNKNOWN
        if "plus1" in model or "shelly1" in model:
            device_type = ShellyDeviceType.PLUS_1
        elif "plus2pm" in model:
            device_type = ShellyDeviceType.PLUS_2PM
        elif "plusi4" in model:
            device_type = ShellyDeviceType.PLUS_I4
        elif "pro1" in model:
            device_type = ShellyDeviceType.PRO_1
        elif "pro2" in model:
            device_type = ShellyDeviceType.PRO_2
        elif "pro4pm" in model:
            device_type = ShellyDeviceType.PRO_4PM
        elif "ht" in model:
            device_type = ShellyDeviceType.HT

        # Check for temperature sensors (Add-On with DS18B20)
        temperature_sensors = []
        try:
            async with session.get(f"http://{ip}/rpc/Temperature.GetStatus?id=0") as resp:
                if resp.status == 200:
                    temp_data = await resp.json()
                    sensor = self._parse_temperature_sensor(ip, name, 0, temp_data, config.get("thresholds", {}))
                    if sensor:
                        temperature_sensors.append(sensor)

            # Check for additional sensors (up to 5 DS18B20 on Add-On)
            for i in range(1, 5):
                try:
                    async with session.get(f"http://{ip}/rpc/Temperature.GetStatus?id={i}") as resp:
                        if resp.status == 200:
                            temp_data = await resp.json()
                            sensor = self._parse_temperature_sensor(
                                ip, name, i, temp_data, config.get("thresholds", {})
                            )
                            if sensor:
                                temperature_sensors.append(sensor)
                except Exception:
                    break

        except Exception as e:
            logger.debug(f"No temperature sensors on {ip}: {e}")

        return ShellyDevice(
            ip=ip,
            name=name,
            device_type=device_type,
            mac=mac,
            firmware=firmware,
            is_online=True,
            has_temperature=len(temperature_sensors) > 0,
            temperature_sensors=temperature_sensors,
            extra_data={"model": info.get("model")},
        )

    def _create_device_gen1(self, ip: str, info: dict, config: dict) -> ShellyDevice:
        """Create device from Gen 1 API info."""
        name = config.get("name") or info.get("name") or f"Shelly {ip}"
        mac = info.get("mac", "")

        return ShellyDevice(
            ip=ip,
            name=name,
            device_type=ShellyDeviceType.UNKNOWN,
            mac=mac,
            is_online=True,
            has_temperature=False,
            extra_data={"type": info.get("type")},
        )

    def _parse_temperature_sensor(
        self,
        ip: str,
        device_name: str,
        index: int,
        data: dict,
        thresholds: dict,
    ) -> ShellyTemperatureSensor | None:
        """Parse temperature sensor data."""
        temp_c = data.get("tC")
        if temp_c is None:
            return None

        temp_f = data.get("tF") or (temp_c * 9 / 5 + 32)

        # Get thresholds for this sensor
        sensor_thresholds = thresholds.get(str(index), thresholds)
        high_threshold = sensor_thresholds.get("high_c")
        low_threshold = sensor_thresholds.get("low_c")

        # Check alert status
        alert_active = False
        if high_threshold is not None and temp_c > high_threshold:
            alert_active = True
        if low_threshold is not None and temp_c < low_threshold:
            alert_active = True

        sensor_name = f"{device_name} Sensor {index}" if index > 0 else device_name

        return ShellyTemperatureSensor(
            id=f"{ip}_{index}",
            name=sensor_name,
            temperature_c=temp_c,
            temperature_f=temp_f,
            device_ip=ip,
            device_name=device_name,
            sensor_index=index,
            high_threshold_c=high_threshold,
            low_threshold_c=low_threshold,
            alert_active=alert_active,
        )

    async def get_all_temperatures(self) -> list[ShellyTemperatureSensor]:
        """Get temperature readings from all sensors."""
        if not self._initialized:
            return []

        cache_key = "all_temperatures"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        sensors = []
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                for ip, device in self._devices.items():
                    if not device.has_temperature:
                        continue

                    # Get thresholds from config
                    config = next((c for c in self.devices_config if c.get("ip") == ip), {})
                    thresholds = config.get("thresholds", {})

                    # Query each sensor
                    for i in range(5):
                        try:
                            async with session.get(f"http://{ip}/rpc/Temperature.GetStatus?id={i}") as resp:
                                if resp.status == 200:
                                    temp_data = await resp.json()
                                    sensor = self._parse_temperature_sensor(ip, device.name, i, temp_data, thresholds)
                                    if sensor:
                                        sensors.append(sensor)
                                else:
                                    break
                        except Exception:
                            break

            self._cache[cache_key] = sensors
            self._cache_time[cache_key] = datetime.now()

        except Exception:
            logger.exception("Failed to get Shelly temperatures")

        return sensors

    async def get_device_status(self, ip: str) -> dict | None:
        """Get full status of a Shelly device."""
        try:
            async with (
                aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session,
                session.get(f"http://{ip}/rpc/Shelly.GetStatus") as resp,
            ):
                if resp.status == 200:
                    return await resp.json()
        except Exception:
            logger.exception("Failed to get Shelly status for")

        return None

    async def get_summary(self) -> dict:
        """Get summary for dashboard."""
        temps = await self.get_all_temperatures()

        alerts = [s for s in temps if s.alert_active]
        online_count = len([s for s in temps if s.is_online])

        return {
            "initialized": self._initialized,
            "device_count": len(self._devices),
            "sensor_count": len(temps),
            "sensors": [s.to_dict() for s in temps],
            "alerts": [s.to_dict() for s in alerts],
            "alert_count": len(alerts),
            "online_count": online_count,
        }


# Singleton instance
shelly_client: ShellyClient | None = None


def get_shelly_client() -> ShellyClient | None:
    """Get the Shelly client singleton."""
    return shelly_client


async def init_shelly_client(
    devices: list[dict] | None = None,
    cache_ttl: int = 30,
) -> ShellyClient:
    """Initialize the Shelly client singleton."""
    global shelly_client
    shelly_client = ShellyClient(
        devices=devices,
        cache_ttl=cache_ttl,
    )
    await shelly_client.initialize()
    return shelly_client
