"""
Thermal camera sensor integration client.

Supports MLX90640 and AMG8833 thermal sensors via ESP32 REST API.
For hot spot detection (oven left on, server overheating, etc.)

Typical ESP32 endpoints:
- GET /thermal/frame - Raw thermal frame data
- GET /thermal/stats - Min/max/avg temperatures
- GET /thermal/hotspot - Highest temperature point
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import aiohttp

logger = logging.getLogger(__name__)


class ThermalSensorType(Enum):
    """Thermal sensor types."""

    MLX90640 = "mlx90640"  # 32x24 = 768 pixels
    MLX90641 = "mlx90641"  # 16x12 = 192 pixels
    AMG8833 = "amg8833"  # 8x8 = 64 pixels
    UNKNOWN = "unknown"


@dataclass
class ThermalHotSpot:
    """Hot spot detection result."""

    temperature_c: float
    temperature_f: float
    x: int  # pixel x coordinate
    y: int  # pixel y coordinate
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "temperature_c": round(self.temperature_c, 1),
            "temperature_f": round(self.temperature_f, 1),
            "x": self.x,
            "y": self.y,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ThermalFrame:
    """Complete thermal frame data."""

    width: int
    height: int
    min_temp_c: float
    max_temp_c: float
    avg_temp_c: float
    hotspot: ThermalHotSpot
    pixels: Optional[list[float]] = None  # Flattened temperature array
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self, include_pixels: bool = False) -> dict:
        result = {
            "width": self.width,
            "height": self.height,
            "min_temp_c": round(self.min_temp_c, 1),
            "max_temp_c": round(self.max_temp_c, 1),
            "avg_temp_c": round(self.avg_temp_c, 1),
            "hotspot": self.hotspot.to_dict(),
            "timestamp": self.timestamp.isoformat(),
        }
        if include_pixels and self.pixels:
            result["pixels"] = [round(p, 1) for p in self.pixels]
        return result


@dataclass
class ThermalSensor:
    """Thermal sensor device info."""

    id: str
    name: str
    ip: str
    sensor_type: ThermalSensorType
    is_online: bool = True
    firmware: str = ""
    last_frame: Optional[ThermalFrame] = None
    # Alert configuration
    high_threshold_c: Optional[float] = None
    alert_active: bool = False
    location: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "ip": self.ip,
            "sensor_type": self.sensor_type.value,
            "is_online": self.is_online,
            "firmware": self.firmware,
            "last_frame": self.last_frame.to_dict() if self.last_frame else None,
            "high_threshold_c": self.high_threshold_c,
            "alert_active": self.alert_active,
            "location": self.location,
        }


class ThermalClient:
    """Client for ESP32-based thermal sensors (MLX90640, AMG8833)."""

    def __init__(
        self,
        sensors: Optional[list[dict]] = None,
        cache_ttl: int = 5,
        timeout: int = 5,
    ):
        """Initialize thermal sensor client.

        Args:
            sensors: List of sensor configs [{"ip": "192.168.1.x", "name": "Kitchen", "threshold_c": 150}]
            cache_ttl: Cache time-to-live in seconds
            timeout: HTTP request timeout
        """
        self.sensors_config = sensors or []
        self.cache_ttl = cache_ttl
        self.timeout = timeout

        self._cache: dict[str, Any] = {}
        self._cache_time: dict[str, datetime] = {}
        self._sensors: dict[str, ThermalSensor] = {}
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize and discover thermal sensors."""
        try:
            for config in self.sensors_config:
                ip = config.get("ip")
                if not ip:
                    continue

                sensor = await self._discover_sensor(ip, config)
                if sensor:
                    self._sensors[ip] = sensor
                    logger.info(f"Thermal sensor discovered: {sensor.name} ({ip})")

            self._initialized = len(self._sensors) > 0
            if self._initialized:
                logger.info(f"Thermal client initialized with {len(self._sensors)} sensors")
            else:
                logger.warning("No thermal sensors found")

            return self._initialized

        except Exception:
            logger.exception("Failed to initialize thermal client")
            return False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    def _is_cache_valid(self, key: str) -> bool:
        if key not in self._cache_time:
            return False
        elapsed = (datetime.now() - self._cache_time[key]).total_seconds()
        return elapsed < self.cache_ttl

    async def _discover_sensor(self, ip: str, config: dict) -> Optional[ThermalSensor]:
        """Discover a thermal sensor and its capabilities."""
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                # Try to get sensor info
                async with session.get(f"http://{ip}/thermal/info") as resp:
                    if resp.status == 200:
                        info = await resp.json()
                        return self._create_sensor_from_info(ip, info, config)

                # Fallback: try to get a frame to detect sensor type
                async with session.get(f"http://{ip}/thermal/stats") as resp:
                    if resp.status == 200:
                        stats = await resp.json()
                        return self._create_sensor_from_stats(ip, stats, config)

        except asyncio.TimeoutError:
            logger.warning(f"Thermal sensor at {ip} timed out")
        except aiohttp.ClientError as e:
            logger.warning(f"Thermal sensor at {ip} connection error: {e}")
        except Exception:
            logger.exception("Failed to discover thermal sensor at")

        return None

    def _create_sensor_from_info(self, ip: str, info: dict, config: dict) -> ThermalSensor:
        """Create sensor from info endpoint."""
        name = config.get("name") or info.get("name") or f"Thermal {ip}"

        # Detect sensor type from dimensions
        width = info.get("width", 32)
        height = info.get("height", 24)
        pixel_count = width * height

        if pixel_count == 768:
            sensor_type = ThermalSensorType.MLX90640
        elif pixel_count == 192:
            sensor_type = ThermalSensorType.MLX90641
        elif pixel_count == 64:
            sensor_type = ThermalSensorType.AMG8833
        else:
            sensor_type = ThermalSensorType.UNKNOWN

        return ThermalSensor(
            id=f"thermal_{ip.replace('.', '_')}",
            name=name,
            ip=ip,
            sensor_type=sensor_type,
            is_online=True,
            firmware=info.get("firmware", ""),
            high_threshold_c=config.get("threshold_c"),
            location=config.get("location", ""),
        )

    def _create_sensor_from_stats(self, ip: str, stats: dict, config: dict) -> ThermalSensor:
        """Create sensor from stats endpoint (minimal info)."""
        name = config.get("name") or f"Thermal {ip}"

        return ThermalSensor(
            id=f"thermal_{ip.replace('.', '_')}",
            name=name,
            ip=ip,
            sensor_type=ThermalSensorType.UNKNOWN,
            is_online=True,
            high_threshold_c=config.get("threshold_c"),
            location=config.get("location", ""),
        )

    async def get_frame(self, ip: str, include_pixels: bool = False) -> Optional[ThermalFrame]:
        """Get thermal frame from a sensor."""
        if ip not in self._sensors:
            return None

        cache_key = f"frame_{ip}"
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as session:
                endpoint = "/thermal/frame" if include_pixels else "/thermal/stats"
                async with session.get(f"http://{ip}{endpoint}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        frame = self._parse_frame(data, include_pixels)

                        # Update sensor with latest frame
                        self._sensors[ip].last_frame = frame
                        self._sensors[ip].is_online = True

                        # Check alert threshold
                        sensor = self._sensors[ip]
                        if sensor.high_threshold_c and frame.max_temp_c > sensor.high_threshold_c:
                            sensor.alert_active = True
                        else:
                            sensor.alert_active = False

                        self._cache[cache_key] = frame
                        self._cache_time[cache_key] = datetime.now()
                        return frame

        except Exception as e:
            logger.warning(f"Failed to get thermal frame from {ip}: {e}")
            if ip in self._sensors:
                self._sensors[ip].is_online = False

        return None

    def _parse_frame(self, data: dict, include_pixels: bool) -> ThermalFrame:
        """Parse thermal frame data."""
        min_temp = data.get("min_c", data.get("min", 0))
        max_temp = data.get("max_c", data.get("max", 0))
        avg_temp = data.get("avg_c", data.get("avg", (min_temp + max_temp) / 2))

        # Hot spot info
        hotspot_data = data.get("hotspot", {})
        hotspot = ThermalHotSpot(
            temperature_c=hotspot_data.get("temp_c", max_temp),
            temperature_f=hotspot_data.get("temp_f", max_temp * 9 / 5 + 32),
            x=hotspot_data.get("x", 0),
            y=hotspot_data.get("y", 0),
        )

        pixels = data.get("pixels") if include_pixels else None

        return ThermalFrame(
            width=data.get("width", 32),
            height=data.get("height", 24),
            min_temp_c=min_temp,
            max_temp_c=max_temp,
            avg_temp_c=avg_temp,
            hotspot=hotspot,
            pixels=pixels,
        )

    async def get_all_sensors(self) -> list[ThermalSensor]:
        """Get status of all thermal sensors."""
        if not self._initialized:
            return []

        # Update frames for all sensors
        for ip in self._sensors:
            await self.get_frame(ip)

        return list(self._sensors.values())

    async def get_alerts(self) -> list[ThermalSensor]:
        """Get sensors with active alerts (temperature above threshold)."""
        sensors = await self.get_all_sensors()
        return [s for s in sensors if s.alert_active]

    async def get_summary(self) -> dict:
        """Get summary for dashboard."""
        sensors = await self.get_all_sensors()
        alerts = [s for s in sensors if s.alert_active]
        online = [s for s in sensors if s.is_online]

        return {
            "initialized": self._initialized,
            "sensor_count": len(sensors),
            "online_count": len(online),
            "alert_count": len(alerts),
            "sensors": [s.to_dict() for s in sensors],
            "alerts": [s.to_dict() for s in alerts],
        }


# Singleton instance
thermal_client: Optional[ThermalClient] = None


def get_thermal_client() -> Optional[ThermalClient]:
    """Get the thermal client singleton."""
    return thermal_client


async def init_thermal_client(
    sensors: Optional[list[dict]] = None,
    cache_ttl: int = 5,
) -> ThermalClient:
    """Initialize the thermal client singleton."""
    global thermal_client
    thermal_client = ThermalClient(
        sensors=sensors,
        cache_ttl=cache_ttl,
    )
    await thermal_client.initialize()
    return thermal_client
